# P284 – FE: trang Nhật ký/chi phí + Lưu trữ

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F14 | [P153](./P153-error-empty-states.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P284] FE: trang Nhật ký/chi phí + Lưu trữ

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F14-thong-bao-nhat-ky-chi-phi/fe.md

Việc cần làm:
1. /logs?tab=usage|events|ai (chi phí theo ngày/truyện/provider, sự kiện, log AI nếu bật).
2. /settings/storage: dung lượng theo loại, dọn dẹp.
3. Test.

Phạm vi file: fe/src/features/logs/, fe/src/features/storage/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P284 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P284); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
