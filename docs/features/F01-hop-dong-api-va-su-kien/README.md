# F01 — Hợp đồng API và luồng sự kiện

Giai đoạn: R0 (khung: quy ước, lỗi, event bus trong RAM), R1 (lưu `job_events`, replay, OpenAPI → TS trong CI). Trạng thái: planned.

## Mục tiêu

FE và BE nói chung một "ngôn ngữ" cố định: mọi API có cùng quy ước (`/v1`, token, idempotency, phân trang, `expected_revision`), mọi lỗi có cùng hình dạng `{code, message, detail, retryable, action}`, và mọi cập nhật thời gian thực đi qua **một** luồng SSE toàn cục có thể nối lại từ `seq` mà không mất hay lặp sự kiện. Kiểu TypeScript ở FE được sinh từ OpenAPI của BE, không viết tay.

## Phạm vi

- Trong phạm vi:
  - Quy ước API: prefix `/v1`, header `Authorization`, `Idempotency-Key`, phân trang cursor, `expected_revision` + 409, 202 cho tác vụ dài, định dạng ID/thời gian, snake_case JSON.
  - Hợp đồng lỗi Plan §23.1.D: mã tối thiểu + mã hạ tầng bổ sung, ánh xạ HTTP status, `action` gợi ý cho FE.
  - SSE toàn cục `GET /v1/events?since=&works=` (Plan §23.1.C): envelope có version, `Last-Event-ID`, replay từ `job_events`, gộp `token.delta` 50–100 ms, chỉ gửi đầy đủ cho truyện đăng ký; bản preview đuôi cho Phòng viết; giữ `job_events` 90 ngày.
  - `GET /v1/jobs/{id}/events` (Plan §7) là bộ lọc của cùng event bus.
  - Xuất OpenAPI → `contracts/openapi.json` → `openapi-typescript` → `fe/src/shared/api/generated/schema.d.ts`, kiểm diff trong CI.
  - FE: `shared/api/client.ts`, `shared/api/stream.ts` (fetch streaming), event bus duy nhất trong `features/jobs`, ánh xạ `code → thông báo + nút`.
  - AI: contract port tiến độ `ProgressSink`/`CheckpointSink` và kiểu sự kiện AI (`TokenDelta`, `StepProgress`, `CheckpointPayload`).
- Ngoài phạm vi:
  - Bảng `jobs`/`job_steps`, writer queue, retention runner → F02 (F01 dùng lại).
  - Ngữ nghĩa từng event nghiệp vụ (`candidate.ready`, `work.continuity`…) do tính năng phát ra định nghĩa payload chi tiết (F10, F11, F12…); F01 chốt envelope và cơ chế.
  - Trung tâm thông báo, log AI → F14.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F00 | Token, base URL, middleware bảo mật, `BootGate` cung cấp session cho client |
| F02 (cho phần R1) | Bảng `job_events`, writer queue, retention; ở R0 event bus chạy trong RAM |

## Nguồn thiết kế

- Plan §2 (SSE native FastAPI ≥ 0.135, fetch streaming), §3 bước 6, §4.4 (độ trễ event < 200 ms mục tiêu, batch 50–100 ms), §7 (danh sách API, "FE reconnect từ sequence; event không bị render lặp"), §8 (OpenAPI → types), §17 (ActionRequest có idempotency key, expected revisions), §23.1.C, §23.1.D, §23.2 #10 (giữ `job_events` 90 ngày), §23.5 #2.
- Arch §4 (`shared/api/client.ts`, `stream.ts`, `generated/schema.d.ts`, `features/jobs`), §5 (`api/errors.py`, `api/streams.py`, `jobs/events.py`, `infrastructure/ai/progress_adapter.py`), §6 (`contracts/events.py`, `ports/progress.py`), §7 (chuỗi sinh hợp đồng, app factory không side effect, envelope là Pydantic có version).
- UI §6 (một event bus, buffer token, rAF), §5.3 (Phòng viết 1–2 dòng cuối, ~4 lần/giây).
- Review §7.2 (FastAPI SSE: ping 15 s, `Last-Event-ID`; EventSource không gửi được `Authorization`).
- Mã feature Plan: WRK08 (episode/event history), CHT07 (stream tiến độ), OPS08 (log có cấu trúc) — phần hạ tầng.

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | `api/errors.py`, `api/conventions.py`, `api/streams.py`, `jobs/events.py` (EventBus), bảng `job_events`, `idempotency_records`, xuất OpenAPI |
| FE | [fe.md](./fe.md) | `client.ts`, `stream.ts`, `errors.ts`, event bus `features/jobs`, bản đồ invalidation, buffer token |
| AI | [ai.md](./ai.md) | `ports/progress.py`, `contracts/events.py`; không gọi model |

## Tiêu chí hoàn thành

- [ ] Mọi route trả lỗi theo envelope; test contract duyệt toàn bộ OpenAPI xác nhận response lỗi tham chiếu `ErrorResponse`.
- [ ] `contracts/openapi.json` sinh lặp lại được (cùng input → cùng byte); CI fail khi file hoặc `schema.d.ts` lệch.
- [ ] Ngắt mạng giả giữa stream (đóng kết nối phía server) → FE nối lại với `Last-Event-ID`, không mất event đã lưu, không render lặp (dedup theo `seq`).
- [ ] `since` cũ hơn event cũ nhất còn giữ → FE nhận `backend.notice` `replay_gap` và làm mới toàn bộ query.
- [ ] `token.delta` chỉ gửi đầy đủ cho truyện trong `works=`; truyện khác nhận bản preview ≤ ~4 lần/giây; `token.delta` không có trong `job_events`.
- [ ] Client chậm không làm chậm backend: hàng đợi subscriber đầy → server đóng kết nối, client tự replay từ DB.
- [ ] POST lặp với cùng `Idempotency-Key` trả cùng kết quả; khác nội dung → 409 `IDEMPOTENCY_CONFLICT`.
- [ ] Các test luồng liên quan pass: [T17](../../tests/flows/T17-phong-viet-va-su-kien.md); phần hiển thị lỗi theo mã trong [T15](../../tests/flows/T15-loi-provider.md); reconnect sau crash trong [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md).

## Rủi ro và câu hỏi mở

- Plan §23.1.D liệt kê `WORK_BUSY_QUEUED` và `VAULT_LOCKED` như mã lỗi, nhưng §4.2 và §23.2 #7 nói job **không fail** mà chuyển `waiting_slot`. Thiết kế ở đây: các mã này dùng cả làm `wait_reason` của job (không phải HTTP error); chỉ trả HTTP 423/409 khi một lời gọi đồng bộ thật sự không thực hiện được (ví dụ kiểm tra provider khi vault khóa). Cần ghi rõ lại trong Plan.
- Plan §23.1.D nói "`message` lấy từ gói ngôn ngữ" trong khi cũng nói "FE ánh xạ `code` → thông báo". Đề xuất: BE trả `message` tiếng Việt làm bản dự phòng (log, công cụ), FE ưu tiên khóa i18n theo `code`.
- Envelope Plan §23.1.C có `seq` bắt buộc nhưng `token.delta` không được lưu → không có `seq` riêng. Đề xuất: `token.delta` mang `seq` = seq đã lưu gần nhất (watermark) và không gửi dòng `id:` SSE; FE dedup `token.delta` theo `(candidate_id, offset)`.
- API chính xác của `fastapi.sse` (tên lớp `ServerSentEvent`, cách đọc `Last-Event-ID`) phải đối chiếu docs FastAPI khi dựng (Review §7.2 chỉ xác nhận có tính năng).
- Thay đổi `works=` cần mở lại kết nối (tham số nằm ở query). Chấp nhận vì replay từ `Last-Event-ID` không mất dữ liệu; nếu mở/đóng workspace quá thường xuyên gây nhiễu thì cân nhắc endpoint đăng ký riêng.
- Ngưỡng hàng đợi subscriber, số event replay tối đa, chu kỳ flush token là giả định, chỉnh sau đo R0/R2.
