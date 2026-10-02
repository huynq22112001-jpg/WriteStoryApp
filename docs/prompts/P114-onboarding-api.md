# P114 – API trạng thái onboarding

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F03 | [P102](./P102-migration-baseline.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P114] API trạng thái onboarding

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P102. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F03-khoi-dau-va-vault/be.md
- docs/tests/flows/T02-lan-chay-dau-va-vault.md

Việc cần làm:
1. `modules/onboarding/`: GET/PUT /v1/onboarding, POST /v1/onboarding/complete; lưu trong settings key `onboarding.state`.
2. Test các bước và trạng thái sau restart.

Phạm vi file: be/src/writestory_be/modules/onboarding/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P114 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P114); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
