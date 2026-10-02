# P278 – FE: hộp thoại auto-write + ước tính

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F12 | [P276](./P276-writing-room-table.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P278] FE: hộp thoại auto-write + ước tính

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P276. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/fe.md
- docs/ui-design.vi.md §5.8

Việc cần làm:
1. Số chương / tới chương, chế độ auto|review_each|review_every_k, ưu tiên, ước tính chi phí + thời gian, cảnh báo vượt ngân sách (confirm_over_budget).
2. Test.

Phạm vi file: fe/src/features/autowrite/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P278 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P278); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
