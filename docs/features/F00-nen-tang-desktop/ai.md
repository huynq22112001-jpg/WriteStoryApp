# F00 — AI

Không có workflow, prompt hay model thật trong F00. Phần AI duy nhất là **mock provider phục vụ spike R0**: chứng minh bundle frozen chứa được package `writestory_ai` (kể cả package resources), stream token qua `/v1/events` và chạy 3 luồng song song mà editor vẫn mượt (Plan §9 Giai đoạn 0, Arch §11 R0 "AI mock provider").

## Module và file

```text
ai/src/writestory_ai/
  providers/mock.py           MockTextProvider: stream văn bản giả theo kịch bản, không gọi mạng
  prompts/manifest.json       Bản tối thiểu (1 template "spike.echo") chỉ để kiểm resource trong bundle frozen
ai/tests/fixtures/
  mock_provider.py            Re-export MockTextProvider + helper kịch bản cho test (docs/tests/README.md)
```

Lý do đặt bản chạy được trong `src/` thay vì chỉ ở `tests/fixtures/`: spike cần mock trong **binary đã đóng gói** (máy sạch), mà thư mục test không được PyInstaller gom. Mock chỉ được đăng ký khi bootstrap có `dev_features=true` (F00 be.md); registry provider thật (F04) không liệt kê nó cho người dùng.

## Contract (Pydantic)

Chỉ là tập con tối thiểu cho spike; contract provider chính thức do F04 (`ports/provider.py`) và F10 chốt, khi đó mock được chuyển sang port thật.

```text
MockScenario:   latency_ms: int = 300        # trễ trước token đầu
                tokens_per_sec: float = 30
                total_tokens: int = 1500
                fail_sequence: list[str] = []  # "429:2" | "500" | "ok" (giống docs/tests/README.md)
                disconnect_after_tokens: int | None
                seed: int = 0                  # văn bản giả xác định
MockChunk:      text: str, index: int          # index tăng dần, dùng làm offset kiểm tra trùng
MockResult:     text: str, usage: {input_tokens, output_tokens}, stop_reason: "end_turn" | "max_tokens"
```

## Workflow

1. `POST /v1/dev/mock-runs` (F00 be.md) tạo N run (1–5), mỗi run một `work_id` giả.
2. Mỗi run là một task asyncio gọi `MockTextProvider.stream(scenario)`; token đi qua `ProgressSink` (contract của F01 ai.md) → BE gộp 50–100 ms → `token.delta` trên `/v1/events`.
3. Mỗi 500 token phát `job.step` giả (`plan → write → check → commit`) để FE spike thử hiển thị bước.
4. Khi `commit_to_spike_db=true`: kết thúc run ghi một dòng vào `data/tmp/spike.sqlite3` (WAL, `synchronous=FULL`) để đo thời gian commit khi nhiều luồng commit gần nhau (Plan §4.2 "đo ở R0"). File này bị xóa khi tắt spike.
5. Văn bản giả: câu tiếng Việt có dấu sinh từ danh sách cố định theo `seed` (có cả `đ`, chữ hai dấu như "ộ", "ễ") để kiểm encoding UTF-8 xuyên suốt stream → FE.

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| `spike.echo` | Chỉ kiểm `importlib.resources` đọc được template trong bundle frozen; không gửi đi đâu | — | Chuỗi đã render |

## Model, effort, giới hạn

- Không có vai trò (Plan §7.1) hay effort; mock không đọc `provider_models`.
- Không có structured output.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Không mô phỏng trong F00 (để F10/T15) |
| Bị cắt `max_tokens` | Không mô phỏng trong F00 |
| JSON không hợp lệ | Không áp dụng |
| `fail_sequence` có `429:2` | Mock raise lỗi giả kèm `retry_after=2`; spike chỉ ghi log, không cần limiter thật |
| `disconnect_after_tokens` | Dừng stream giữa chừng; FE spike phải hiện trạng thái run lỗi, không treo |
| Hủy run (đóng app) | Task nhận `CancelledError`, kết thúc sạch trong deadline shutdown |

## Đánh giá

- Không có rubric chất lượng văn. Chỉ số spike (ghi ADR, không đặt ngưỡng trước khi đo): độ trễ event backend → UI, FPS/độ trễ gõ phím khi 3–5 luồng stream (UI §10), thời gian commit vào `spike.sqlite3` khi các run kết thúc gần nhau.
- Bộ dữ liệu mẫu: không cần; văn bản giả sinh theo `seed`.

## Việc cần làm

- [ ] `providers/mock.py` với `MockScenario`, stream xác định theo `seed`.
- [ ] `ai/tests/fixtures/mock_provider.py` re-export + helper.
- [ ] `prompts/manifest.json` tối thiểu + khai báo trong `pyproject.toml` package data; kiểm đọc được trong bản PyInstaller.
- [ ] Ghi kết quả spike vào ADR.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Cùng `seed` → cùng văn bản; `tokens_per_sec` tạo độ trễ đúng thứ tự độ lớn (dùng clock giả) | `ai/tests/unit/providers/test_mock_provider.py` |
| unit | `disconnect_after_tokens` dừng đúng chỗ; `fail_sequence` raise đúng thứ tự | `ai/tests/unit/providers/test_mock_provider.py` |
| contract (mock provider) | Đọc `spike.echo` qua `importlib.resources` (chạy cả trong bản frozen ở smoke desktop) | `ai/tests/contract/test_package_resources.py` |

## Tên mới đề xuất

- `ai/src/writestory_ai/providers/mock.py` (`MockTextProvider`, `MockScenario`, `MockChunk`, `MockResult`); docs/tests/README.md hiện chỉ nêu `ai/tests/fixtures/mock_provider.py` — đề xuất file fixture đó re-export từ `providers/mock.py`.
- Template `spike.echo` trong `ai/src/writestory_ai/prompts/manifest.json`.
- File tạm `data/tmp/spike.sqlite3` (chỉ trong spike).
