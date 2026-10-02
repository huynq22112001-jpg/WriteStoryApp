# P162 – FE: danh sách model kéo thả + effort

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F04 | [P161](./P161-settings-models-connection.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P162] FE: danh sách model kéo thả + effort

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P161. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/fe.md
- docs/ui-design.vi.md §5.6.1

Việc cần làm:
1. Danh sách kéo thả (dnd-kit), đầu = mặc định, hàng mở rộng (tên, context, output, effort hỗ trợ, giá, vai trò, đồng thời riêng, nguồn), ✕ xóa, + Thêm, mục 'Model khả dụng khác', ⚠ model biến mất.
2. Ô effort mặc định chỉ hiện mức model hỗ trợ; trống = mặc định provider.
3. Test: kéo đổi mặc định; effort theo capability.

Phạm vi file: fe/src/features/settings/models/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P162 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P162); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
