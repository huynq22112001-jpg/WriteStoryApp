# P117 – Badge thư viện + tìm theo tiêu đề

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F05 | [P116](./P116-style-profile-languages.md), [P107](./P107-fts-tim-kiem.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P117] Badge thư viện + tìm theo tiêu đề

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P116, P107. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F05-thu-vien-va-tao-truyen/be.md (bảng ưu tiên badge)

Việc cần làm:
1. compute_library_badge theo bảng ưu tiên trong spec (continuity + job).
2. Index tiêu đề vào search (P107); tìm không dấu.
3. Test.

Phạm vi file: be/src/writestory_be/modules/works/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P117 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P117); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
