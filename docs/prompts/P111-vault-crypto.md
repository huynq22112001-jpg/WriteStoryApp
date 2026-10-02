# P111 – Vault: mã hóa file secrets.enc

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F03 | [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P111] Vault: mã hóa file secrets.enc

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F03-khoi-dau-va-vault/be.md
- docs/implementation-plan.vi.md §2 (Secret)
- docs/tests/flows/T02-lan-chay-dau-va-vault.md

Việc cần làm:
1. Thêm `cryptography>=44` vào be/pyproject.toml.
2. VaultService: AES-GCM (nonce 12 byte không dùng lại), Argon2id theo OWASP (m≥19 MiB, t=2, p=1), Scrypt dự phòng; định dạng file theo F03 be.md; ghi tạm + rename.
3. Tạo / mở / khóa / đổi mật khẩu; sai mật khẩu → VAULT_PASSWORD_INVALID.
4. Test: round-trip, sai mật khẩu, file hỏng → VAULT_CORRUPT, không có plaintext trên đĩa.

Phạm vi file: be/src/writestory_be/infrastructure/secrets/, be/pyproject.toml, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P111 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P111); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
