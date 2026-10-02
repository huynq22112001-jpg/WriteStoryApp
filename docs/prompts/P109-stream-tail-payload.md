# P109 – stream.tail, jobs/{id}/events, payload có kiểu

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F01 | [P108](./P108-eventbus-db.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P109] stream.tail, jobs/{id}/events, payload có kiểu

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P108. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F01-hop-dong-api-va-su-kien/be.md
- docs/implementation-plan.vi.md §23.1.C, §24 D10

Việc cần làm:
1. Event `stream.tail` (1–2 dòng cuối, ~4 lần/giây) cho client không đăng ký truyện đó.
2. `GET /v1/jobs/{id}/events` = bộ lọc của luồng chung.
3. Payload Pydantic theo type cho job.queued, job.state, job.step, token.delta, backend.notice.
4. Chạy lại export OpenAPI (P006).

Phạm vi file: be/src/writestory_be/jobs/, be/src/writestory_be/api/, contracts/, be/tests/
Xong khi: Test pass, OpenAPI cập nhật.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P109 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P109); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
