# P245 – BE: ước tính chi phí + API hàng đợi

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F12 | [P244](./P244-autowrite-api.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P245] BE: ước tính chi phí + API hàng đợi

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P244. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/be.md
- docs/implementation-plan.vi.md §23.2 #6

Việc cần làm:
1. POST /v1/works/{id}/autowrite/estimate (token theo usage trung bình, giá provider_models, khoảng min–max, thời gian).
2. GET /v1/queues, PUT /v1/queues/priority, GET/PUT /v1/settings/concurrency; reconcile hàng đợi sau restart.
3. Test.

Phạm vi file: be/src/writestory_be/modules/autowrite/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P245 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P245); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
