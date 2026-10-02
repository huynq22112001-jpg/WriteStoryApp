# P275 – FE: findings, xung đột, resync

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F11 | [P274](./P274-review-diff-ui.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P275] FE: findings, xung đột, resync

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P274. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/fe.md

Việc cần làm:
1. Danh sách findings có trích dẫn, bấm nhảy tới đoạn; resolve/dismiss (ghi chú chỉ cho finding LLM).
2. UI xung đột 409 (3 bên), hộp thoại resync K..N.
3. Test.

Phạm vi file: fe/src/features/review/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P275 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P275); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
