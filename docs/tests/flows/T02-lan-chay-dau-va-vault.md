# T02 — Lần chạy đầu và vault

Tính năng: F03. Nguồn: Plan §23.4 #1, #4; §2 (Secret); §3.1 (vault portable); §23.2 #7; Review §7.4. Cấp test chính: unit, integration, e2e-fe.

## Mục đích

Chứng minh onboarding dẫn người dùng từ app trống tới truyện đầu tiên, vault mã hóa đúng chuẩn (Argon2id + AES-GCM, nonce không lặp, khóa chỉ ở RAM), API key không bao giờ nằm dạng plaintext trong data-root, và trạng thái khóa/mở vault được phản ánh đúng lên job và UI.

## Tiền điều kiện và dữ liệu

- Data-root tạm rỗng; macOS dùng data-root đã chọn ở T01-17.
- API key giả dễ grep: `sk-test-WSA-0123456789abcdef`.
- Mock provider: `{models_endpoint: "anthropic", latency_ms: 30, tokens_per_sec: 300, scripted_outputs: {foundation: "do_thi_01/foundation.json"}}`.
- Fixture truyện mẫu: `tests/fixtures/stories/do_thi_01/`.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T02-01 | thành công | 1. Mở app lần đầu (Windows). 2. Đặt mật khẩu vault `Mật-khẩu-1`. 3. Thêm provider Anthropic (mock), nhập key, "Kiểm tra kết nối", "Kiểm tra lấy danh sách". 4. Chọn "Tạo truyện mẫu". | Không có bước chọn data-root trên Windows. Tạo `data/secrets.enc`; `providers` có 1 dòng chỉ chứa tham chiếu secret, không có key; `provider_models` có model từ mock; `works` có truyện mẫu; onboarding đánh dấu hoàn tất. Mở lại app vào thẳng Thư viện. | e2e-fe, integration | `fe/tests/e2e/onboarding.spec.ts`, `be/tests/integration/test_onboarding_flow.py` |
| T02-02 | thành công | macOS: onboarding bắt đầu bằng bước chọn data-root rồi các bước như T02-01. | Thứ tự bước: data-root → vault → provider → truyện đầu tiên; data-root đã chọn được dùng cho `secrets.enc`. | desktop | `tests/desktop/macos_onboarding.md` |
| T02-03 | thành công | Unit: tạo vault, mã hóa một secret, đọc header file. | Header ghi KDF `argon2id` với m ≥ 19 MiB, t ≥ 2, p = 1, salt ngẫu nhiên; AES-GCM nonce 12 byte; giải mã đúng. Mã hóa cùng plaintext 2 lần cho nonce và ciphertext khác nhau. | unit | `be/tests/unit/test_vault_crypto.py` |
| T02-04 | bảo mật | Ghi/xóa secret 1.000 lần (thêm/xóa key provider). | 1.000 nonce đều khác nhau; file luôn giải mã được sau mỗi lần ghi (ghi file tạm rồi rename). | unit | `be/tests/unit/test_vault_nonce_unique.py` |
| T02-05 | lỗi | `POST /v1/vault/unlock` với mật khẩu sai. | Trả lỗi theo hợp đồng `{code, message, detail, retryable, action}` với `retryable=true`, message tiếng Việt; `GET /v1/vault/status` vẫn `locked`; file `secrets.enc` không đổi (so checksum). | integration | `be/tests/integration/test_vault_api.py` |
| T02-06 | thành công | 1. `POST /v1/vault/lock`. 2. Tạo job write cần key. 3. `POST /v1/vault/unlock` đúng mật khẩu. | Bước 1: event `vault.status` (locked), header hiện badge "vault đang khóa". Bước 2: job `waiting_slot` lý do `VAULT_LOCKED`, FE mở hộp thoại nhập mật khẩu. Bước 3: event `vault.status` (unlocked), scheduler chạy tiếp đúng `job_id` cũ, không tạo job mới. | integration, e2e-fe | `be/tests/integration/test_vault_lock_jobs.py`, `fe/tests/e2e/vault_unlock_dialog.spec.ts` |
| T02-07 | phục hồi | Khởi động lại backend sau khi vault đã mở. | Sau restart `GET /v1/vault/status` = `locked`; khóa giải mã không còn (gọi provider → `VAULT_LOCKED`); danh sách provider/model vẫn hiển thị (không cần key). | integration | `be/tests/integration/test_vault_restart.py` |
| T02-08 | thành công | Chọn "Dùng key theo phiên" thay vì đặt mật khẩu; chạy 1 job mock; khởi động lại. | Không tạo hoặc không sửa `secrets.enc`; job chạy được; grep key trong `data/**` (DB, `-wal`, logs, cache, tmp) = 0. Sau restart provider hiện "chưa có key cho phiên này", job cần key vào `waiting_slot` lý do `VAULT_LOCKED` (xem mục mâu thuẫn). | integration | `be/tests/integration/test_session_only_key.py` |
| T02-09 | bảo mật | Bật log AI debug (§23.2 #11), chạy 1 chương mock, tạo backup không kèm vault. | Grep `sk-test-WSA` trong `data/**` ngoại trừ `secrets.enc` = 0; header `x-api-key`/`Authorization` trong `data/logs/ai/**` bị che; bảng `providers`, `settings` không chứa key. | integration | `be/tests/integration/test_secret_never_plaintext.py` |
| T02-10 | lỗi | Cắt cụt hoặc sửa 1 byte `secrets.enc`; mở vault. | Báo vault hỏng (không phải "sai mật khẩu" chung chung); file không bị ghi đè; tạo vault mới chỉ sau xác nhận rõ, file cũ đổi tên `secrets.enc.corrupt-<ts>`. | integration | `be/tests/integration/test_vault_corrupt.py` |
| T02-11 | hủy | Đóng app ở bước thêm provider (vault đã tạo). Mở lại. | Onboarding tiếp tục đúng bước provider; vault giữ nguyên; không có dòng `providers` dở dang. | e2e-fe | `fe/tests/e2e/onboarding_resume.spec.ts` |
| T02-12 | biên | Bỏ qua bước provider, tạo truyện thủ công. | Thư viện, editor dùng được không cần AI; nút AI hiển thị trạng thái "chưa cấu hình provider" kèm hành động mở Cài đặt › Mô hình AI. | e2e-fe | `fe/tests/e2e/onboarding_skip_ai.spec.ts` |
| T02-13 | biên | Monkeypatch để Argon2id không khả dụng; tạo vault. Sau đó mở vault Argon2id trên bản không có Argon2id. | Vault tạo bằng Scrypt N=2^17, r=8, p=1 và header ghi rõ KDF; mở vault khác KDF không hỗ trợ báo lỗi cụ thể, không ghi đè. | unit | `be/tests/unit/test_vault_kdf_fallback.py` |
| T02-14 | phục hồi | Copy cả `data/` (app đã đóng) từ Windows sang macOS, chọn làm data-root, mở vault bằng mật khẩu cũ. | Mở vault thành công; key dùng được; không cần cấu hình lại provider. | thủ công | `tests/desktop/vault_cross_os.md` |

## Kiểm tra dữ liệu sau test

- DB: `providers` chỉ chứa tham chiếu secret; không cột nào chứa chuỗi key.
- File: `data/secrets.enc` tồn tại khi đặt mật khẩu; không tồn tại hoặc không đổi khi dùng key theo phiên; không có file tạm vault sót lại trong `data/tmp/`.
- Event: `vault.status` phát mỗi lần lock/unlock; job bị chặn do vault có lý do `VAULT_LOCKED`.
- RAM: sau `lock` và sau restart, provider không gọi được (xác nhận gián tiếp qua lỗi `VAULT_LOCKED`).

## Tiêu chí pass

- Grep API key giả trong toàn bộ data-root (kể cả `-wal`, logs, backup) ngoài `secrets.enc` = 0 lần ở mọi kịch bản.
- 1.000/1.000 nonce khác nhau; tham số KDF ≥ mức OWASP (m ≥ 19 MiB, t ≥ 2, p = 1).
- Job chờ vault tiếp tục với cùng `job_id` sau khi mở vault, không mất checkpoint.
- Onboarding hoàn tất < 10 bước thao tác với mock provider và tiếp tục đúng bước sau khi đóng giữa chừng.

## Ghi chú thủ công

- T02-14 cần hai máy thật hoặc VM; kiểm cả hướng macOS → Windows.
- Kiểm bằng mắt toàn bộ chuỗi onboarding tiếng Việt đủ dấu, `aria-label` tiếng Việt cho nút chỉ có icon.

## Tên mới đề xuất

- `POST /v1/vault/init` (tạo vault + mật khẩu); `POST /v1/providers/{id}/session-key` (key chỉ giữ trong RAM phiên).
- Mã lỗi: `VAULT_BAD_PASSWORD`, `VAULT_CORRUPT` (§23.1.D chưa có mã cho sai mật khẩu/vault hỏng).
- Cột `providers.secret_ref`; `settings.onboarding_step` (bước onboarding đang dở).
- Payload `vault.status`: `{state: locked/unlocked/absent/session_only}`.
