# P907 – TEST: ánh xạ kịch bản → file test (xfail)

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P906](./P906-harness-tich-hop.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P907] TEST: ánh xạ kịch bản → file test (xfail)

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P906. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/flows/T01…T17

Việc cần làm:
1. Tạo file test theo cột 'Tự động hóa' của từng luồng; kịch bản chưa có tính năng → xfail kèm lý do (không bỏ trống).
2. Cập nhật cột 'Tự động hóa' nếu đường dẫn thay đổi.

Phạm vi file: tests/, be/tests/, ai/tests/, docs/tests/flows/
Xong khi: Mọi kịch bản có test pass hoặc xfail có lý do.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P907 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P907); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
