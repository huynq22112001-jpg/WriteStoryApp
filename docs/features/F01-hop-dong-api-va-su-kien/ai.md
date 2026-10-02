# F01 — AI

F01 không gọi model. Phần AI là **hợp đồng port tiến độ/checkpoint và kiểu sự kiện** mà mọi workflow (F04, F09, F10, F11) dùng để báo tiến độ cho BE, không import BE (Arch §6: "Progress/checkpoint đi qua port callback được BE cung cấp. Payload có version, source revisions và pinned settings; không truyền ORM object hoặc DB session").

## Module và file

```text
ai/src/writestory_ai/
  contracts/events.py      TokenDelta, StepProgress, CheckpointPayload, PinnedSettings
  contracts/errors.py      AIError và các lớp con mang `code` trùng tên mã lỗi Plan §23.1.D
  ports/progress.py        ProgressSink, CheckpointSink (typing.Protocol)
  testing/sinks.py         RecordingProgressSink, InMemoryCheckpointSink (dùng trong test, không cần BE)
```

BE triển khai: `be/src/writestory_be/infrastructure/ai/progress_adapter.py` (F01 be.md).

## Contract (Pydantic)

```text
PinnedSettings:    provider_id: str, model_id: str, effort: str | None,
                   prompt_id: str, prompt_version: str, method_versions: dict[str, str]
StepProgress:      v: int = 1
                   step: str                  # plan | write | check | settle | validate | seam | review | repair | summarize | ...
                   status: "started" | "finished" | "failed" | "skipped"
                   attempt: int               # lần thử của bước (retry transport không tăng attempt)
                   round: int | None          # vòng sửa k (Plan §6.2 bước 10)
                   max_rounds: int | None
                   progress: float | None     # 0..1 nếu ước lượng được
                   usage: Usage | None        # chỉ khi finished; Usage định nghĩa ở contracts/usage.py (F04/F10)
                   error_code: str | None     # khi failed, một trong AIError.code
TokenDelta:        candidate_ref: str         # ID candidate do BE cấp trước khi gọi workflow
                   step: str
                   offset: int                # vị trí code point của text trong văn bản candidate
                   text: str
CheckpointPayload: v: int = 1
                   step: str
                   attempt: int
                   input_hash: str            # hash input của bước (khớp chapter_plans.input_hash khi là bước plan)
                   source_revisions: dict[str, str]   # ví dụ {"state": "...", "handoff": "...", "outline": "..."}
                   pinned: PinnedSettings
                   state: dict                # dữ liệu riêng của bước, JSON-serializable
                   partial_text_len: int | None       # độ dài văn bản candidate đã có khi checkpoint
```

```text
ProgressSink (Protocol):
  async step(p: StepProgress) -> None           # BE ghi job_steps + phát job.step; có thể chậm vì đi qua writer queue
  token(d: TokenDelta) -> None                  # đồng bộ, không chặn, không raise; BE chỉ đưa vào buffer
CheckpointSink (Protocol):
  async save(cp: CheckpointPayload) -> None     # trả về sau khi đã ghi bền; raise nếu ghi lỗi
```

`AIError(code)` và lớp con: `ProviderAuthError("PROVIDER_AUTH")`, `ProviderUnreachableError("PROVIDER_UNREACHABLE")`, `ProviderRateLimitError("PROVIDER_RATE_LIMIT", retry_after_s)`, `ProviderRefusalError("PROVIDER_REFUSAL")`, `OutputTruncatedError("OUTPUT_TRUNCATED")`, `StructuredOutputInvalidError("STRUCTURED_OUTPUT_INVALID")`, `BudgetExceededError("BUDGET_EXCEEDED")`. BE ánh xạ `code` 1:1 sang `ErrorCode` (F01 be.md mục B); AI không import enum của BE.

## Workflow

Quy tắc dùng port cho mọi workflow:

1. Trước khi chạy bước: `await sink.step(StepProgress(step, "started", attempt))`.
2. Khi stream văn bản: gọi `sink.token(...)` cho từng đoạn nhận được, `offset` tăng liên tục. `token()` chỉ phục vụ hiển thị: BE được phép bỏ bớt khi quá tải; văn bản chuẩn của candidate do workflow giữ và được lưu qua checkpoint/kết quả trả về.
3. Sau mỗi ranh giới hợp lệ của bước (Plan §4.3 "phục hồi ở ranh giới từng bước"): `await checkpoints.save(...)`. Bước stream dài có thể lưu checkpoint trung gian để giữ bản nháp partial (tần suất do F10 chốt).
4. Kết thúc bước: `step(..., "finished", usage=...)` hoặc `step(..., "failed", error_code=...)` rồi raise `AIError` tương ứng.
5. Hủy: BE hủy task asyncio; workflow để `asyncio.CancelledError` lan ra (không bắt rồi nuốt), không gọi thêm sink sau khi bị hủy.
6. Payload phải JSON-serializable, không chứa API key, không chứa đối tượng ORM/session; `CheckpointPayload.state` tối đa 1 MB (giả định, BE từ chối nếu lớn hơn).

## Prompt

Không áp dụng (F01 không có prompt).

## Model, effort, giới hạn

- Không gọi model. `PinnedSettings` chỉ ghi lại model/effort/prompt đã ghim cho job (Plan §7.1 "job ghim model + effort lúc bắt đầu").
- Structured output: không áp dụng.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Workflow raise `ProviderRefusalError`; sink nhận `step failed` với `error_code="PROVIDER_REFUSAL"` |
| Bị cắt `max_tokens` | Theo F10; nếu vẫn cắt sau khi viết tiếp → `OutputTruncatedError` |
| JSON không hợp lệ | Theo F10; cuối cùng → `StructuredOutputInvalidError` |
| `CheckpointSink.save` raise | Workflow dừng bước, để lỗi lan ra; BE quyết định job `failed`/`interrupted` |
| `ProgressSink.step` chậm (writer queue đầy) | Workflow chờ; không gọi lại song song |
| `token()` bị gọi sau khi bước kết thúc | BE bỏ qua; test contract bắt lỗi này |

## Đánh giá

- Không có chỉ số chất lượng văn. Kiểm tra contract: mọi workflow trong test mock phát `started` trước `finished`, `offset` liên tục, không gọi sink sau hủy.
- Bộ dữ liệu mẫu: không cần.

## Việc cần làm

- [x] `contracts/events.py`, `contracts/errors.py`, `ports/progress.py`.
- [ ] `testing/sinks.py` (recording sink cho test workflow).
- [ ] Helper `assert_progress_protocol(events)` dùng lại trong test F10.
- [ ] Đồng bộ danh sách `AIError.code` với `ErrorCode` của BE (test contract phía BE).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Model validate: `offset` âm bị từ chối, `CheckpointPayload` serialize/deserialize giữ nguyên | `ai/tests/unit/contracts/test_events.py` |
| contract (mock provider) | Workflow giả dùng `MockTextProvider` (F00) + `RecordingProgressSink`: thứ tự started → token… → finished, offset liên tục; hủy giữa stream không còn lời gọi sink | `ai/tests/contract/test_progress_protocol.py` |
| contract | Mọi `AIError.code` có trong `ErrorCode` của BE | `be/tests/contract/test_ai_error_codes.py` |

## Tên mới đề xuất

- `ai/src/writestory_ai/contracts/errors.py` (`AIError`, `ProviderAuthError`, `ProviderUnreachableError`, `ProviderRateLimitError`, `ProviderRefusalError`, `OutputTruncatedError`, `StructuredOutputInvalidError`, `BudgetExceededError`).
- `ai/src/writestory_ai/testing/sinks.py` (`RecordingProgressSink`, `InMemoryCheckpointSink`), helper `assert_progress_protocol`.
- `PinnedSettings`; các trường của `StepProgress`, `TokenDelta` (`candidate_ref`, `offset`), `CheckpointPayload` (`input_hash`, `source_revisions`, `partial_text_len`) — Arch §6 chỉ nêu tên lớp.
