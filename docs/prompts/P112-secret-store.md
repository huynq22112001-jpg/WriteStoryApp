# P112 – SecretStore + key theo phiên + che log

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F03 | [P111](./P111-vault-crypto.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P112] SecretStore + key theo phiên + che log

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P111. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F03-khoi-dau-va-vault/be.md

Việc cần làm:
1. SessionSecretStore (chỉ RAM), SecretStore hợp nhất vault + phiên, quy ước secret_ref `provider:<id>:api_key`.
2. Redaction: thêm secret đã nạp vào bộ lọc log (bootstrap/logging_setup.py).
3. Test: key phiên mất sau restart; log không chứa key.

Phạm vi file: be/src/writestory_be/infrastructure/secrets/, bootstrap/logging_setup.py, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P112 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P112); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
