# F12 — AI

F12 không thêm workflow sinh văn bản mới. Phần AI chỉ gồm: (1) cách một job gọi pipeline với cấu hình đã ghim, (2) ranh giới sở hữu giữa limiter (BE) và retry transport (AI policy), (3) cách AI báo checkpoint/hủy để scheduler dừng và resume đúng ranh giới bước.

## Module và file

```text
ai/src/writestory_ai/
  contracts/generation.py      GenerationInput (thêm pinned: PinnedConfig)
  contracts/events.py          StepProgress, CheckpointPayload (stage, repair_round, wait)
  ports/limiter.py             ProviderLimiterPort – BE triển khai bằng infrastructure/ai/limits.py
  ports/progress.py            ProgressSink, CheckpointSink, CancelToken
  policies/retry.py            Phân loại lỗi + hàm backoff (thuần, không giữ state toàn cục)
  workflows/longform/pipeline.py   Entry run_chapter(input, ports) – thuộc F10
```

Ranh giới sở hữu:

| Việc | Chủ sở hữu | Ghi chú |
|---|---|---|
| Semaphore theo provider/model, token bucket RPM/TPM, `cooldown_until` dùng chung mọi job | BE `infrastructure/ai/limits.py` | Plan §4.2, Arch §5; một instance/provider cho cả app |
| Worker pool, chọn truyện, khóa truyện, ngân sách | BE `jobs/` | AI không biết có bao nhiêu truyện |
| Phân loại lỗi (retryable/không), số lần retry transport, công thức backoff + jitter | AI `policies/retry.py` | Arch §6 "retry transport do adapter/policy AI sở hữu" |
| Gọi `acquire`/`release`/`report` quanh mỗi HTTP request | AI provider adapter, qua `ProviderLimiterPort` | AI không import BE; port do BE inject |
| Retry/resume cả job, `waiting_slot`, checkpoint | BE `jobs/` | AI chỉ ném lỗi có kiểu và phát checkpoint |

## Contract (Pydantic)

```text
PinnedConfig:  roles: dict[role, {provider_id, model_id, effort | None, max_tokens}],
               prompt_versions: dict[template_id, version], method_versions, language: "vi",
               max_repair_rounds, length_target
GenerationInput (F10) + pinned: PinnedConfig + resume_from?: CheckpointPayload
ProviderLimiterPort:
  async acquire(provider_id, model_id, est_input_tokens, max_tokens) -> Permit
  release(permit, usage: Usage | None)
  report(provider_id, outcome: ok | rate_limited | server_error | network_error | auth_error,
         retry_after_s: float | None)
StepProgress:  stage, repair_round?, repair_max?, wait?: {reason, until}
CheckpointPayload: v, stage_completed, artifacts_ref (plan_id, candidate_id, delta hash…),
                   input_hash, pinned_hash
Lỗi có kiểu: ProviderAuthError, ProviderUnreachableError, ProviderRateLimitExhausted,
             ProviderRefusal, OutputTruncated, StructuredOutputInvalid, Cancelled
```

## Workflow

1. BE (runner) phân giải `pinned_config` bằng `model_resolver.py` lúc job chuyển `running` lần đầu và lưu vào `jobs.pinned_config`; lần resume dùng lại đúng bản đã ghim (Plan §7.1 "job ghim model + effort", FL26 bước 4). Thay đổi cài đặt chỉ áp cho job chương kế.
2. BE gọi `pipeline.run_chapter(GenerationInput, ports)` với `ContextPort`, `ProgressSink`, `CheckpointSink`, `ProviderLimiterPort`, `CancelToken`.
3. Trước mỗi request, adapter gọi `acquire`; chờ trong port được báo bằng `StepProgress.wait` để Phòng viết hiện "đạt giới hạn tốc độ" trong khi job vẫn `running`.
4. Lỗi transport: `policies/retry.py` quyết định retry (tối đa 3, `Retry-After` ưu tiên, `min(60, 2·2^n)` + full jitter); mỗi lần thất bại gọi `report`. Hết lượt → ném lỗi có kiểu; BE chuyển job sang `waiting_slot`/`failed`.
5. Sau mỗi bước hoàn tất, pipeline gọi `CheckpointSink.save(CheckpointPayload)`; BE persist trước khi pipeline sang bước kế. Kiểm `CancelToken` ở đầu mỗi bước và giữa stream (đóng HTTP request khi hủy, Plan §6.6 cuối).
6. Resume: pipeline nhận `resume_from`; bỏ qua bước đã xong nếu `input_hash` và `pinned_hash` khớp (plan dùng lại theo `chapter_plans.input_hash`, Plan §5); bước Write dở luôn chạy lại.

## Prompt

Không có prompt mới. Ghim `prompt_versions` để resume và chương kế dùng đúng template; không đổi lớp 1–2 trong batch để giữ prompt cache (Plan §6.4).

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| (của F10/F11) | — | Ghim theo job | — |

## Model, effort, giới hạn

- Vai trò (Plan §7.1) và effort lấy theo thứ tự: vai trò trong truyện → vai trò toàn app → effort mặc định → mặc định provider; chỉ gửi mức model hỗ trợ.
- `est_input_tokens` cho TPM: Anthropic dùng count tokens khi cần chính xác; provider khác ước lượng theo tỷ lệ token/âm tiết + biên 15% (Plan §23.3 #4).
- Structured output: không áp dụng riêng cho F12.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Không retry; ném `ProviderRefusal` → BE đặt job `waiting_user` (Plan §23.3 #3) |
| Bị cắt `max_tokens` | Pipeline F10 viết tiếp tối đa 2 lần; không phải lỗi limiter |
| JSON không hợp lệ | Pipeline F10 xử lý; không tiêu lượt retry transport |
| 429 có `Retry-After` | `report(rate_limited, retry_after)` → limiter đặt cooldown chung provider; retry sau thời gian đó |
| 401/403/404 model | Không retry; `ProviderAuthError` |
| Mất mạng giữa stream | Retry transport; hết lượt → `ProviderUnreachableError`, phần draft đã stream được lưu partial qua checkpoint |
| Hủy khi đang chờ `acquire` | `acquire` nhận `CancelToken`, thoát ngay, không giữ permit |

## Đánh giá

- Chỉ số: tổng số request thực tế / số request tối thiểu (đo chi phí retry); không có retry lồng (transport × job) vượt giới hạn; thời gian chờ đúng `Retry-After` ± 1 s với mock.
- Bộ dữ liệu mẫu: kịch bản mock provider `fail_sequence`, `disconnect_after_tokens` (docs/tests/README.md).

## Việc cần làm

- [ ] `ports/limiter.py` + adapter gọi `acquire/release/report`.
- [ ] `policies/retry.py` phân loại lỗi theo giao thức (Anthropic/OpenAI-compatible/Ollama).
- [ ] `PinnedConfig` + `pinned_hash`; pipeline nhận `resume_from`.
- [ ] `CancelToken` truyền tới httpx stream.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Phân loại lỗi + backoff có jitter trong biên | `ai/tests/unit/policies/test_retry.py` |
| contract (mock provider) | `fail_sequence: [429(retry_after=2), 500, ok]` → 2 retry, gọi `report` đúng | `ai/tests/contract/test_limiter_port.py` |
| contract (mock provider) | Resume từ checkpoint bỏ qua bước đã xong khi hash khớp | `ai/tests/contract/test_pipeline_resume.py` |
| contract (mock provider) | Cancel giữa stream đóng request, không ghi candidate ready | `ai/tests/contract/test_cancel.py` |

## Tên mới đề xuất

- `ports/limiter.py` với `ProviderLimiterPort`, `Permit`.
- `PinnedConfig`, `pinned_hash`, `resume_from`, `CancelToken`, `StepProgress.wait`.
- Lớp lỗi: `ProviderAuthError`, `ProviderUnreachableError`, `ProviderRateLimitExhausted`, `ProviderRefusal`, `OutputTruncated`, `StructuredOutputInvalid`, `Cancelled`.
