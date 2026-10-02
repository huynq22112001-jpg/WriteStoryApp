# P015 – Paste NFC + đếm âm tiết TS

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 / F08 | [P014](./P014-spike-tiptap.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P015] Paste NFC + đếm âm tiết TS

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P014. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- ai/src/writestory_ai/languages/vi/normalizer.py
- ai/src/writestory_ai/languages/vi/length.py
- docs/features/F07-editor-va-phien-ban/fe.md

Việc cần làm:
1. `fe/src/shared/lib/vi/normalize.ts` và `length.ts`: port đúng thuật toán Python.
2. Áp chuẩn hóa khi paste vào ChapterEditor; hiện số âm tiết + ký tự dưới editor.
3. Test đối chiếu cùng các ca của ai/tests/unit/test_vi_language.py.

Phạm vi file: fe/src/shared/lib/vi/, fe/src/features/editor/
Xong khi: test pass, kết quả trùng bản Python.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P015 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P015); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
