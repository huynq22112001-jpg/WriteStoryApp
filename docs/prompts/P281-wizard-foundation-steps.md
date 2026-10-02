# P281 – FE: wizard – nền truyện, xưng hô, dàn ý

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F06 / F05 | [P160](./P160-wizard-skeleton.md), [P279](./P279-story-bible-characters.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P281] FE: wizard – nền truyện, xưng hô, dàn ý

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P160, P279. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F06-nen-truyen-va-story-bible/fe.md
- docs/features/F05-thu-vien-va-tao-truyen/fe.md
- docs/ui-design.vi.md §5.7

Việc cần làm:
1. Hoàn thiện bước foundation (chạy job, xem/duyệt/sửa từng phần, khôi phục nháp), address_rules, event_outline của wizard P160.
2. Test + e2e tạo truyện đầy đủ với backend giả.

Phạm vi file: fe/src/features/wizard/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P281 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P281); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
