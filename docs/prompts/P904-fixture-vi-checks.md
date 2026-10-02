# P904 – TEST: ca kiểm tra tiếng Việt

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P001](./P001-cai-moi-truong-uv-python.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P904] TEST: ca kiểm tra tiếng Việt

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P001. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/flows/T13-kiem-tra-tieng-viet.md

Việc cần làm:
1. `tests/fixtures/vi_checks/`: xưng hô đúng/sai, từ lạc thời, cụm sáo, lỗi Telex, trộn kiểu bỏ dấu, thoại sai ký tự, ca hỏi/ngã không bắt được (ghi rõ giới hạn), ca paste từ Word (NFD, NBSP, zero-width).

Phạm vi file: tests/fixtures/vi_checks/, tests/fixtures/paste/
Xong khi: Mỗi ca có kết quả mong đợi.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P904 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P904); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
