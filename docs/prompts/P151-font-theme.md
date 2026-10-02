# P151 – FE: font tiếng Việt offline + theme

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | UI | [P150](./P150-shadcn-base-ui.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P151] FE: font tiếng Việt offline + theme

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P150. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/ui-design.vi.md §3 (Font), §8

Việc cần làm:
1. Cài @fontsource/be-vietnam-pro và @fontsource-variable/noto-serif (subset vietnamese), import trong global.css.
2. Token màu/typography sáng – tối; cỡ chữ đọc chỉnh được (Zustand + lưu qua settings API sau).
3. Kiểm tra build không gọi Google Fonts.

Phạm vi file: fe/src/styles/, fe/src/app/, fe/package.json
Xong khi: build pass; không có request font ra ngoài.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P151 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P151); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
