# F14 — AI

F14 chỉ định nghĩa hợp đồng báo usage và trace request. AI không tính tiền, không ghi file, không biết data-root; BE nhận dữ liệu qua contract/port rồi lưu `usage_records`, cộng `usage_counters` và (nếu bật) ghi log debug.

## Module và file

```text
ai/src/writestory_ai/
  contracts/usage.py        Usage, StepUsage
  contracts/trace.py        RequestTrace (cho log debug, Plan §23.2 #11)
  ports/progress.py         ProgressSink.on_usage(Usage), on_request_trace(RequestTrace)
  providers/anthropic.py, openai_compatible.py, ollama.py   chuẩn hóa usage theo giao thức
```

## Contract (Pydantic)

```text
Usage:
  provider_id, model_id, role, job_step_ref (do BE truyền vào), attempt
  reported: bool                       # False khi provider không trả usage
  input_tokens: int | None             # phần input KHÔNG đến từ cache, tính giá input thường
  output_tokens: int | None            # gồm token suy nghĩ nếu provider tính chung
  reasoning_tokens: int | None         # tách riêng nếu provider báo
  cache_read_tokens: int | None
  cache_write_tokens: int | None
  cache_write_ttl: "5m" | "1h" | None
  stop_reason: end | max_tokens | refusal | tool_use | cancelled | error
  provider_request_id: str | None
  latency_ms, first_token_ms
  partial: bool                        # stream bị hủy/đứt, số liệu có thể thiếu
RequestTrace:
  ts, provider_id, model_id, effort, template_id, template_version,
  params: {max_tokens, effort, temperature?, structured: bool},
  messages: list[{role, content}]      # prompt đã render, KHÔNG có header/khóa
  response_text | response_json, stop_reason, usage: Usage, error_code?
```

Trace chỉ được tạo khi BE truyền cờ `debug_trace=True` trong `GenerationInput`; mặc định không dựng để tránh giữ chuỗi lớn trong RAM.

## Workflow

1. Adapter gọi provider; khi stream kết thúc (hoặc bị hủy/đứt) tạo `Usage` từ dữ liệu provider trả.
2. Gọi `ProgressSink.on_usage(usage)` ngay sau mỗi request, kể cả request thất bại có usage (ví dụ cắt `max_tokens`) và lần retry – BE cần tổng thực tế để đối soát chi phí (Plan §4.3: không hứa exactly-once billing).
3. Nếu `debug_trace`: gọi `on_request_trace(trace)`; BE che secret và ghi file.

Chuẩn hóa theo giao thức (giả định, kiểm lại tài liệu chính thức khi code):

| Giao thức | Nguồn trường | Chuẩn hóa |
|---|---|---|
| Anthropic Messages | `usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` (chi tiết TTL 5m/1h nếu có); stream: `message_start` + `message_delta` | `input_tokens` giữ nguyên (đã không gồm cache); `cache_write_ttl` theo breakpoint đã đặt |
| OpenAI-compatible | `usage.prompt_tokens`, `completion_tokens`, `prompt_tokens_details.cached_tokens`, `completion_tokens_details.reasoning_tokens`; stream cần `stream_options.include_usage` | `input_tokens = prompt_tokens − cached_tokens`; `cache_read_tokens = cached_tokens`; `cache_write_tokens = None` |
| Ollama / LM Studio (OpenAI-compatible local) | Có thể thiếu usage | `reported=False`, mọi số `None`; không ước lượng |

## Prompt

Không có prompt. `template_id`/`template_version` trong trace lấy từ manifest prompt (Plan §23.3 #8).

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| — | — | — | — |

## Model, effort, giới hạn

- Không chọn model. Ghi `effort` thực gửi (trống nếu không gửi tham số, Plan §7.1).
- Structured output: không áp dụng.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | `stop_reason=refusal`, vẫn báo usage nếu có |
| Bị cắt `max_tokens` | `stop_reason=max_tokens`; mỗi lần viết tiếp là một `Usage` riêng |
| JSON không hợp lệ | Usage vẫn báo; lần sửa JSON là request riêng |
| Hủy giữa stream | `partial=True`; dùng số liệu cuối cùng nhận được, không bù |
| Provider không trả usage | `reported=False`, không suy diễn (Plan §6.6) |

## Đánh giá

- Đối soát: tổng `Usage` của mock provider khớp `usage_records` của BE 100%.
- Bộ dữ liệu mẫu: fixture response ghi lại theo giao thức trong `ai/tests/fixtures/usage/`.

## Việc cần làm

- [ ] `contracts/usage.py`, `contracts/trace.py`.
- [ ] Chuẩn hóa usage trong 3 adapter, gồm stream và cancel.
- [ ] `ProgressSink.on_usage`, `on_request_trace`.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Chuẩn hóa usage Anthropic/OpenAI/Ollama từ fixture | `ai/tests/unit/providers/test_usage_normalize.py` |
| contract (mock provider) | Retry 429 → 2 `Usage` (lần lỗi không có token) + 1 thành công | `ai/tests/contract/test_usage_reporting.py` |
| contract (mock provider) | `disconnect_after_tokens` → `partial=True` | `ai/tests/contract/test_usage_partial.py` |

## Tên mới đề xuất

- `contracts/trace.py`, `RequestTrace`; trường `Usage.{reported, reasoning_tokens, cache_write_ttl, partial, first_token_ms, provider_request_id}`.
- Port `ProgressSink.on_usage`, `ProgressSink.on_request_trace`; cờ `GenerationInput.debug_trace`.
