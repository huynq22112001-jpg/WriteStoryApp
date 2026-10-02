# P249 – BE: sao lưu + khôi phục

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F13 | [P104](./P104-writer-queue-uow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P249] BE: sao lưu + khôi phục

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P104. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F13-xuat-va-sao-luu/be.md
- docs/implementation-plan.vi.md §5 (backup), §24 D1
- docs/tests/flows/T16-xuat-va-sao-luu.md

Việc cần làm:
1. POST /v1/backups (VACUUM INTO tạm + rename, manifest checksum asset, tùy chọn vault, giữ N bản, không lồng backup), GET /v1/backups, verify, restore (backup hiện trạng trước, đóng writer, thay, rebuild FTS).
2. Test: backup trong lúc 3 truyện đang ghi.

Phạm vi file: be/src/writestory_be/modules/operations/backup*, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P249 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P249); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
