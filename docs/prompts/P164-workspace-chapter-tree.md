# P164 – FE: workspace 3 cột + cây chương

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 | [P152](./P152-app-shell.md), [P014](./P014-spike-tiptap.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P164] FE: workspace 3 cột + cây chương

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P152, P014. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/fe.md
- docs/ui-design.vi.md §5.2, §24 D30

Việc cần làm:
1. `features/workspace/`: react-resizable-panels 3 cột thu gọn được, thanh mode (Lập dàn ý | Viết | Review | Bible), route /works/$workId?mode=&chapter=&tab=.
2. Cây chương react-arborist (ảo hóa, kéo thả gọi reorder, trạng thái chương).
3. Test.

Phạm vi file: fe/src/features/workspace/, fe/src/app/router.tsx
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P164 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P164); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
