# P014 – Spike editor Tiptap + paragraph_id

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 / S08 | [P004](./P004-kiem-chung-fe-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P014] Spike editor Tiptap + paragraph_id

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P004. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S08-spike-editor-ime.md
- docs/features/F07-editor-va-phien-ban/fe.md
- docs/implementation-plan.vi.md §24 D19

Việc cần làm:
1. Cài Tiptap v3 (@tiptap/react, starter-kit, @tiptap/extensions, extension-unique-id); pnpm overrides `prosemirror-view >= 1.41.9`.
2. `fe/src/features/editor/ChapterEditor.tsx` tối thiểu; mỗi đoạn có paragraph_id 8 ký tự [a-z0-9], duy nhất sau tách/gộp đoạn.
3. Route tạm `/editor-spike`.
4. Test: id duy nhất sau tách/gộp.

Phạm vi file: fe/src/features/editor/, fe/src/app/router.tsx, fe/package.json
Xong khi: test + build pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P014 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P014); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
