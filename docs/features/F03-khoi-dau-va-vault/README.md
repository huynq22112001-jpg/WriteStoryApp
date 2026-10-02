# F03 — Khởi đầu (onboarding) và vault API key

Giai đoạn: R1. Trạng thái: planned.

## Mục tiêu

Lần đầu mở app, người dùng được dẫn qua vài bước ngắn: (macOS) chọn thư mục dữ liệu → đặt mật khẩu vault hoặc chọn chỉ dùng key trong phiên → thêm nhà cung cấp AI và kiểm tra lấy danh sách model → tạo truyện đầu tiên hoặc mở truyện mẫu. API key chỉ nằm trong `data/secrets.enc` đã mã hóa hoặc trong RAM của phiên; khi vault khóa, tác vụ cần key tự chờ và chạy tiếp ngay sau khi người dùng mở khóa.

## Phạm vi

- Trong phạm vi:
  - Vault `data/secrets.enc`: AES-256-GCM, khóa dẫn xuất bằng Argon2id (`cryptography` ≥ 44, tham số OWASP tối thiểu), Scrypt dự phòng; nonce 12 byte mới mỗi lần ghi; tạo, mở, khóa, đổi mật khẩu, đặt lại (xóa) vault.
  - Kho secret theo phiên (session-only): không bao giờ ghi đĩa/log/DB.
  - `SecretStore` dùng chung cho BE (F04 lấy key qua đây), API `/v1/vault/*`, `/v1/secrets/*`.
  - Hành vi `VAULT_LOCKED`: lời gọi đồng bộ trả 423; job chuyển `waiting_slot` lý do `VAULT_LOCKED` và được đánh thức khi mở vault (cơ chế đánh thức thuộc F12, F03 cung cấp tín hiệu).
  - Onboarding: trạng thái lần chạy đầu, wizard 4 bước, hoàn tất/bỏ qua.
  - FE: wizard onboarding, hộp thoại mở khóa vault, badge vault trên header, mục Bảo mật trong Cài đặt.
- Ngoài phạm vi:
  - Chọn data-root macOS (màn trước khi backend chạy) → F00; wizard chỉ hiển thị bước này là "đã xong".
  - Form provider, kiểm tra kết nối, discovery model → F04 (wizard nhúng component của F04).
  - Wizard tạo truyện và truyện mẫu → F05.
  - Đưa vault vào backup → F13. Lưu key vào OS keychain/bỏ vault: chỉ khi người dùng đổi yêu cầu (Plan §3.1).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F00 | Data-root, chọn data-root macOS, token/bootstrap |
| F02 | Bảng `settings` (trạng thái onboarding, chế độ vault), `UnitOfWork`, ghi file nguyên tử |
| F01 | Hợp đồng lỗi (`VAULT_LOCKED`), event `vault.status`, event bus FE |
| F04, F05 (để hoàn tất wizard) | Bước 3 dùng form provider + discovery của F04; bước 4 dùng wizard/truyện mẫu của F05. Có thể làm F03 trước với bước 3–4 tạm là liên kết |

## Nguồn thiết kế

- Plan §2 (Secret: vault, cryptography ≥ 44, AES-GCM + Argon2id, Scrypt dự phòng, nonce 12 byte, khóa chỉ trong RAM), §3.1 (vault không dùng khóa hard-code; key theo phiên; chuyển data Win/Mac mở bằng mật khẩu), §5 (settings chỉ lưu reference tới secret), §7 (`POST /v1/vault/unlock | lock`, `GET /v1/vault/status`), FL01 bước 4 ("mở vault khi cần dùng key"), FL26 bước 1, §21 (secret không vào log), §23.1.C (`vault.status`), §23.1.D (`VAULT_LOCKED`), §23.2 #7, §23.4 #1 và #4, §23.5 #5.
- Arch §5 (`infrastructure/secrets/vault.py`), §4 (`features/onboarding`, `features/settings`).
- UI §5.6.1 (API key "lưu trong vault"), §5.8 (onboarding, hộp thoại mở khóa vault).
- Review §7.4 (Argon2id OWASP m=19 MiB, t=2, p=1; Scrypt N=2^17, r=8, p=1; nonce không dùng lại).
- Mã feature Plan: MOD01 (lưu secret riêng), NEW01 (vault portable), OPS10 (cấu hình persist trong data).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Định dạng `secrets.enc`, `VaultService`, `SessionSecretStore`, `SecretStore`, API vault/secrets/onboarding, tín hiệu cho scheduler |
| FE | [fe.md](./fe.md) | Wizard `/onboarding`, `VaultUnlockDialog`, `VaultBadge`, mục Cài đặt → Bảo mật |
| AI | [ai.md](./ai.md) | Không áp dụng |

## Tiêu chí hoàn thành

- [ ] Lần chạy đầu (DB trống) tự vào `/onboarding`; hoàn tất hoặc bỏ qua → không hiện lại; data-root đã có truyện (ví dụ khôi phục backup) → bỏ qua onboarding.
- [ ] Tạo vault → `secrets.enc` tồn tại, không chứa chuỗi key gốc (grep), khởi động lại → trạng thái `locked`.
- [ ] Sai mật khẩu → `VAULT_PASSWORD_INVALID`, có thời gian chờ tăng dần; đúng mật khẩu → `unlocked`, event `vault.status` tới FE.
- [ ] Chế độ key theo phiên: nhập key, dùng được; khởi động lại → key không còn; không có key trong `data/` (grep toàn bộ data-root, log, DB).
- [ ] Job cần key khi vault khóa → `waiting_slot` lý do `VAULT_LOCKED`, badge header hiện số tác vụ chờ; mở vault → job chạy tiếp, không tạo job mới.
- [ ] Copy cả data-root từ Windows sang macOS (app đã đóng) → mở vault bằng cùng mật khẩu thành công.
- [ ] Kill tiến trình khi đang ghi vault → `secrets.enc` vẫn là bản cũ hoặc bản mới đầy đủ, không hỏng.
- [ ] Các test luồng liên quan pass: [T02](../../tests/flows/T02-lan-chay-dau-va-vault.md); phần "vault khóa" của [T15](../../tests/flows/T15-loi-provider.md).

## Rủi ro và câu hỏi mở

- Quên mật khẩu vault = mất mọi key đã lưu (không có khôi phục, đúng thiết kế). UI phải nói rõ khi tạo; "Đặt lại vault" xóa toàn bộ key.
- Python không xóa bộ nhớ an toàn tuyệt đối (chuỗi bất biến, GC); khóa giữ trong `bytearray` và ghi đè khi khóa vault là best-effort. Ghi rõ giới hạn này, không hứa hơn.
- Tham số Argon2id: dùng mức tối thiểu OWASP làm mặc định, lưu trong file nên tăng được sau; thời gian mở khóa thực tế cần đo ở R1 (chưa có số đo).
- Plan §7 chỉ có `unlock | lock | status`; tạo vault, đổi mật khẩu, đặt lại, ghi secret và trạng thái onboarding là endpoint mới đề xuất (be.md) — cần đồng bộ Plan §7.
- Plan §23.1.D chỉ có `VAULT_LOCKED`; trường hợp chế độ theo phiên mà chưa nhập key (sau restart) cần một mã riêng `SECRET_MISSING` để FE mở đúng form nhập key thay vì hộp thoại mật khẩu.
- Có nên tự khóa vault sau một thời gian không dùng? Plan không yêu cầu; để mặc định tắt, đưa vào câu hỏi cho pilot.
