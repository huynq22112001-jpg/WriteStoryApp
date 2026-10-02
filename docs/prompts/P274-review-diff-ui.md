# P274 – FE: màn Review/Diff

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F11 | [P167](./P167-history-diff.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P274] FE: màn Review/Diff

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P167. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/fe.md
- docs/ui-design.vi.md §5.5

Việc cần làm:
1. So sánh song song/inline, mức từ/câu, nhận từng đoạn, Ctrl+Enter / Esc, J/K điều hướng.
2. Test + e2e nhận từng đoạn.

Phạm vi file: fe/src/features/review/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P274 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P274); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
