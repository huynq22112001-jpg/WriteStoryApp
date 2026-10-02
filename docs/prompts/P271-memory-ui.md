# P271 – FE: tab Nhớ + tìm kiếm + trace

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F09 | [P164](./P164-workspace-chapter-tree.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P271] FE: tab Nhớ + tìm kiếm + trace

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P164. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/fe.md
- docs/ui-design.vi.md §5.2

Việc cần làm:
1. Tab 'Nhớ' (facts/hooks liên quan, kết quả tìm có nguồn chương), trang /works/$workId/search, trình xem trace 'Đã dùng ngữ cảnh'.
2. Hook useStoryState(workId, chapter) cho Story Bible.
3. Test.

Phạm vi file: fe/src/features/memory/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P271 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P271); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
