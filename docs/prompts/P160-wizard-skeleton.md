# P160 – FE: khung wizard tạo truyện

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F05 | [P159](./P159-library-ui.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P160] FE: khung wizard tạo truyện

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P159. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F05-thu-vien-va-tao-truyen/fe.md
- docs/ui-design.vi.md §5.7

Việc cần làm:
1. Route /new, 7 bước basics|brief|foundation|address_rules|event_outline|writing_config|review, lưu nháp từng bước (wizard_step).
2. Bước 1, 2, 6, 7 đầy đủ; bước 3–5 chỉ khung (nội dung ở P281).
3. react-hook-form + zod; test.

Phạm vi file: fe/src/features/wizard/, fe/src/app/router.tsx
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P160 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P160); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
