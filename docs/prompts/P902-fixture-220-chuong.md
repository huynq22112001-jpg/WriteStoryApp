# P902 – TEST: truyện tổng hợp 220 chương

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P901](./P901-fixture-truyen-mau.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P902] TEST: truyện tổng hợp 220 chương

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P901. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/flows/T14-truyen-dai-va-ngu-canh.md

Việc cần làm:
1. Script `tests/fixtures/stories/gen_synthetic_long.py` sinh synthetic_long_220 (chương ngắn có facts/hooks/sự kiện, xác định theo seed).
2. Kiểm tra kích thước hợp lý, sinh lại ra cùng kết quả.

Phạm vi file: tests/fixtures/stories/
Xong khi: Sinh lại cho kết quả giống hệt.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P902 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P902); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
