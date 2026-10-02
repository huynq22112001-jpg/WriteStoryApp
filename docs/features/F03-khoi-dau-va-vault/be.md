# F03 — Backend

## Module và file

```text
be/src/writestory_be/
  infrastructure/secrets/
    vault.py              VaultFile (định dạng), derive_key (Argon2id/Scrypt), encrypt/decrypt, ghi nguyên tử
    session_store.py      SessionSecretStore: dict trong RAM, không serialize
    secret_store.py       SecretStore: facade get/put/delete/availability/on_change (session → vault)
    redaction.py          Đăng ký giá trị secret để bộ lọc log che; strip `input` khỏi lỗi validate
  modules/vault/
    router.py             /v1/vault/*, /v1/secrets/*
    schemas.py            VaultStatus, CreateVaultRequest, UnlockRequest, ChangePasswordRequest, ResetVaultRequest,
                          SecretInfo, PutSecretRequest (giá trị dùng pydantic.SecretStr)
    service.py            VaultService: tạo/mở/khóa/đổi mật khẩu/đặt lại, throttle, phát vault.status
  modules/onboarding/
    router.py             /v1/onboarding
    schemas.py            OnboardingState
    service.py            Tính trạng thái từng bước, tự hoàn tất khi đã có truyện
```

## Dữ liệu và migration

Không tạo bảng mới. Dùng bảng `settings` của F02 và file `data/secrets.enc`.

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `settings` key `vault.mode` | `value_json`: `"undecided" \| "vault" \| "session_only"` | — | Mặc định `undecided` |
| `settings` key `secrets.index` | `value_json`: `{<secret_ref>: {storage: "vault", label, updated_at}}` | — | Chỉ metadata, **không có giá trị**; cho UI biết key nằm trong vault kể cả khi vault khóa |
| `settings` key `onboarding.state` | `value_json`: `{status: "pending" \| "completed" \| "skipped", step: "security" \| "provider" \| "first_work" \| null, completed_at}` | `revision` dùng cho `expected_revision` | — |

Định dạng `data/secrets.enc` (JSON UTF-8):

```text
{ "format": "writestory-vault", "version": 1, "vault_id": "<UUIDv7>",
  "kdf": {"name": "argon2id", "salt": "<base64 16 byte>", "memory_cost_kib": 19456, "iterations": 2, "lanes": 1, "length": 32}
       | {"name": "scrypt",   "salt": "<base64 16 byte>", "n": 131072, "r": 8, "p": 1, "length": 32},
  "cipher": "AES-256-GCM", "nonce": "<base64 12 byte>", "ciphertext": "<base64, gồm tag 16 byte>",
  "created_at": "…", "updated_at": "…" }
plaintext (sau giải mã) = {"v": 1, "entries": {"<secret_ref>": {"value": "…", "label": "…", "updated_at": "…"}}}
AAD = JSON chuẩn hóa (sort_keys, không khoảng trắng) của {format, version, vault_id, kdf, cipher}
```

Migration: không có (chỉ thêm khóa `settings`, giá trị mặc định đọc khi thiếu).

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/vault/status` | — | `VaultStatus = {state: "absent" \| "locked" \| "unlocked", mode, kdf: "argon2id" \| "scrypt" \| null, created_at?, updated_at?, waiting_jobs: int, throttle_ms: int}` | `UNAUTHORIZED` |
| POST | `/v1/vault` | `{password, password_confirm, import_session_secrets: bool = true}` | 201 `VaultStatus` (`unlocked`) | `VALIDATION` (ngắn, không khớp), `VAULT_ALREADY_EXISTS` (409) |
| POST | `/v1/vault/unlock` | `{password}` | `VaultStatus` | `VAULT_NOT_FOUND` (404), `VAULT_PASSWORD_INVALID` (422, `detail.retry_after_ms`), `VAULT_UNLOCK_THROTTLED` (429 + `Retry-After`), `VAULT_CORRUPT` (500) |
| POST | `/v1/vault/lock` | — | `VaultStatus` | — (khóa khi đã khóa vẫn 200) |
| POST | `/v1/vault/change-password` | `{current_password, new_password, new_password_confirm}` | `VaultStatus` | `VAULT_PASSWORD_INVALID`, `VAULT_UNLOCK_THROTTLED`, `VALIDATION` |
| POST | `/v1/vault/reset` | Header `Idempotency-Key`; `{confirm: "XÓA VAULT"}` | `VaultStatus` (`absent`) | `VALIDATION` (sai chuỗi xác nhận) |
| PUT | `/v1/vault/mode` | `{mode: "vault" \| "session_only", expected_revision}` | `VaultStatus` | `REVISION_CONFLICT`, `VALIDATION` (`vault` khi chưa tạo vault) |
| GET | `/v1/secrets` | — | `SecretInfo[] = [{ref, storage: "vault" \| "session", available: bool, label, updated_at}]` | — |
| PUT | `/v1/secrets/{ref}` | `{value: SecretStr, storage: "vault" \| "session", label?}` | `SecretInfo` | `VAULT_LOCKED` (423), `VALIDATION` (`ref` sai dạng, `detail.reason="vault_absent"`) |
| DELETE | `/v1/secrets/{ref}` | — | 204 | `VAULT_LOCKED` (nếu ref nằm trong vault khóa) |
| GET | `/v1/onboarding` | — | `OnboardingState = {status, step, revision, steps: {data_root: "done" \| "not_applicable", security, provider, first_work: "done" \| "pending" \| "skipped"}, platform}` | — |
| PUT | `/v1/onboarding` | `{step, expected_revision}` | `OnboardingState` | `REVISION_CONFLICT`, `VALIDATION` |
| POST | `/v1/onboarding/complete` | `{skipped: bool}` | `OnboardingState` | — |

Giá trị secret **không bao giờ** có trong response. `ref` hợp lệ: `^[a-z0-9_.:-]{1,128}$`; F04 dùng dạng `provider:<provider_id>:api_key`.

## Logic xử lý

### A. Tạo vault

1. Kiểm tra `password == password_confirm`; chuẩn hóa NFC (bộ gõ macOS/Windows có thể sinh dạng Unicode khác nhau — bắt buộc để mở được trên máy khác, Plan §3.1); độ dài tối thiểu 8 ký tự (giả định), cảnh báo nếu < 12 (FE).
2. Vault đã có → `VAULT_ALREADY_EXISTS`.
3. `salt = os.urandom(16)`; KDF Argon2id (`cryptography.hazmat.primitives.kdf.argon2.Argon2id`, `memory_cost=19456 KiB, iterations=2, lanes=1, length=32` — mức tối thiểu OWASP, Review §7.4). Nếu thư viện báo không hỗ trợ (`UnsupportedAlgorithm`) → Scrypt `n=2**17, r=8, p=1`. Chạy KDF trong `asyncio.to_thread` để không chặn event loop.
4. Plaintext = mục nhập từ `SessionSecretStore` nếu `import_session_secrets` (rồi xóa khỏi session store), ngược lại rỗng.
5. Mã hóa (mục D), ghi file nguyên tử; `vault.mode = "vault"`; cập nhật `secrets.index`; giữ khóa trong RAM (`unlocked`); phát `vault.status`.

### B. Mở/khóa

1. Unlock: throttle trước — sau 3 lần sai liên tiếp, lần sai thứ n ≥ 3 khóa thử `min(2^(n-3), 30)` giây (giả định); trong thời gian chờ trả `VAULT_UNLOCK_THROTTLED` mà không chạy KDF. Bộ đếm chỉ trong RAM.
2. Đọc file, kiểm tra `format`/`version` (lạ → `VAULT_CORRUPT`), dẫn xuất khóa theo `kdf` ghi trong file, giải mã với AAD. `InvalidTag` → `VAULT_PASSWORD_INVALID` (không phân biệt sai mật khẩu với file bị sửa — cả hai đều không mở được).
3. Thành công: khóa (32 byte) giữ trong `bytearray`, bản giải mã giữ trong `dict` của `VaultService`; reset bộ đếm; phát `vault.status {state:"unlocked"}`; gọi các callback `on_change` (scheduler F12 đánh thức job chờ `VAULT_LOCKED`).
4. Lock: ghi đè `bytearray` bằng 0 (best-effort), xóa `dict`, phát `vault.status {state:"locked"}`. Request HTTP tới provider đang bay không bị hủy; lần lấy key tiếp theo sẽ thấy vault khóa.
5. Backend khởi động: vault luôn ở `locked` (hoặc `absent`). Không tự hỏi mật khẩu; chỉ hỏi khi cần key (FL01 bước 4).

### C. Đổi mật khẩu, đặt lại

1. Đổi mật khẩu: xác minh `current_password` bằng cách giải mã lại (áp throttle), salt mới, khóa mới, mã hóa lại toàn bộ, ghi nguyên tử. `vault_id` giữ nguyên.
2. Đặt lại: xóa `secrets.enc`, xóa mục `storage="vault"` trong `secrets.index`, `vault.mode = "undecided"`, trạng thái `absent`. Không đụng secret trong session.

### D. Mã hóa và ghi file

1. Mỗi lần ghi: `nonce = os.urandom(12)` mới (không bao giờ dùng lại; số lần ghi của vault cá nhân rất nhỏ so với giới hạn an toàn của nonce ngẫu nhiên 96 bit), `AESGCM(key).encrypt(nonce, plaintext, aad)`.
2. Ghi `data/secrets.enc.tmp` → `flush` + `fsync` → `os.replace` sang `secrets.enc` → fsync thư mục (macOS). Không bao giờ ghi plaintext ra đĩa, kể cả file tạm.
3. Một `asyncio.Lock` bao mọi thao tác đọc-sửa-ghi vault.

### E. SecretStore (dùng bởi F04, F12)

1. `availability(ref)`: có trong session → `session`; có trong `secrets.index` và vault mở → `vault`; có trong index nhưng vault khóa → `vault_locked`; không có → `missing`.
2. `get(ref)`: thứ tự session → vault. `vault_locked` → raise `VaultLockedError` (BE ánh xạ `VAULT_LOCKED`); `missing` mà `vault.mode="session_only"` hoặc ref chưa từng lưu → raise `SecretMissingError` (`SECRET_MISSING`).
3. `put(ref, value, storage)`: `session` → session store; `vault` → cần `unlocked` (không thì `VAULT_LOCKED`), vault chưa có → `VALIDATION reason=vault_absent`. Cập nhật `secrets.index` qua `UnitOfWork.write`. Đăng ký `value` với `redaction` để che trong log.
4. `on_change(callback)`: gọi khi lock/unlock/put/delete; F12 dùng để đánh giá lại job `waiting_slot` lý do `VAULT_LOCKED`/`SECRET_MISSING`.
5. `infrastructure/ai/factory.py` (F04) tiêm vào adapter provider của package AI một hàm lấy key bọc `get(ref)`; adapter gọi hàm này **mỗi request**, không cache key lâu hơn một request (AI không import BE, Arch §6).

### F. Hành vi VAULT_LOCKED (Plan §23.2 #7)

1. Lời gọi đồng bộ cần key (F04: `POST /v1/providers/test`, `POST /v1/providers/{id}/discover`) → 423 `VAULT_LOCKED`, `action="unlock_vault"`; `SECRET_MISSING` → 409, `action="open_provider_settings"`.
2. Job: trước khi cấp slot, scheduler (F12) kiểm `availability` của secret ref đã ghim; `vault_locked` → `waiting_slot`, `wait_reason="VAULT_LOCKED"`, phát `job.state`; `missing` → `wait_reason="SECRET_MISSING"`. Không fail job, không tạo job mới khi mở khóa.
3. Đang chạy mà `get` raise giữa bước → bước dừng ở ranh giới checkpoint gần nhất, job về `waiting_slot` cùng lý do (F12 thực hiện), chạy tiếp từ checkpoint sau khi mở khóa.
4. Discovery nền lúc khởi động (Plan §7.1) gặp vault khóa → bỏ qua, ghi trạng thái "chờ mở vault", không bật hộp thoại.
5. `VaultStatus.waiting_jobs` = số job `waiting_slot` với `wait_reason="VAULT_LOCKED"` (truy vấn `jobs`, F02).

### G. Onboarding

1. `GET /v1/onboarding`: nếu `status="pending"` mà đã có ít nhất một tác phẩm (bảng `works`, F05) → tự đặt `completed` (data-root khôi phục từ backup không phải onboard lại).
2. Bước: `data_root` = `done` trên macOS (đã qua F00), `not_applicable` trên Windows; `security` = `done` khi `vault.mode ≠ "undecided"`; `provider` = `done` khi có ≥ 1 provider (F04), `skipped` nếu người dùng bỏ qua; `first_work` = `done` khi có tác phẩm.
3. `complete {skipped}` → `status = "skipped"` hoặc `"completed"`, `completed_at = now`. FE không tự vào `/onboarding` nữa (vẫn mở được từ Cài đặt).

### H. Chống rò rỉ

1. Request model dùng `SecretStr`; handler `VALIDATION` (F01) bỏ trường `input` trong `detail.fields` cho mọi route `/v1/vault/*` và `/v1/secrets/*` (FastAPI mặc định đưa giá trị đầu vào vào lỗi validate).
2. Log access của uvicorn không ghi body; bộ lọc `redaction` che mọi giá trị đã đăng ký và chuỗi giống API key phổ biến (tiền tố `sk-`, `sk-ant-`) — heuristic bổ sung.
3. `secrets.index` và `settings` không chứa giá trị secret; test grep bảo đảm.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `vault.status` | Tạo, mở, khóa, đổi mật khẩu, đặt lại, đổi `mode` | `{state, mode, waiting_jobs}` |
| `job.state` (do F12 phát) | Job chuyển `waiting_slot` vì vault | `{status: "waiting_slot", wait_reason: "VAULT_LOCKED" \| "SECRET_MISSING"}` |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Sai mật khẩu | 422, đếm lần sai | `VAULT_PASSWORD_INVALID` |
| Sai quá nhiều lần | 429 + `Retry-After` | `VAULT_UNLOCK_THROTTLED` |
| `secrets.enc` hỏng/không đọc được JSON | Không ghi đè; báo lỗi, gợi ý khôi phục từ backup (F13) hoặc đặt lại | `VAULT_CORRUPT` |
| Ghi vault khi đĩa đầy | Giữ file cũ (do ghi tạm + rename), báo lỗi | `INTERNAL` |
| `secrets.index` có ref nhưng vault không chứa ref đó (file thay bằng bản khác) | Sau unlock đồng bộ lại index theo nội dung vault | — |
| Unlock đồng thời hai request | `asyncio.Lock`; request sau thấy đã `unlocked` → trả trạng thái | — |
| Session-only, restart | Key mất; job cần key → `waiting_slot` `SECRET_MISSING` | `SECRET_MISSING` |
| Data-root chép sang máy khác | Mở bằng mật khẩu cũ (NFC giúp khớp giữa OS) | — |
| Argon2id không có trong bản `cryptography` đóng gói | Tạo vault bằng Scrypt, ghi `kdf.name="scrypt"`; vault Argon2id cũ không mở được → `VAULT_CORRUPT` với `detail.reason="kdf_unsupported"` | `VAULT_CORRUPT` |

## Việc cần làm

- [ ] Pin `cryptography>=44` trong `be/pyproject.toml`; kiểm Argon2id có trong bản PyInstaller (smoke F00).
- [ ] `vault.py` (định dạng, KDF, AAD, ghi nguyên tử) + test vector cố định.
- [ ] `session_store.py`, `secret_store.py`, `redaction.py`.
- [ ] `modules/vault/` (router, schemas với `SecretStr`, service, throttle).
- [ ] Ẩn `input` trong lỗi validate cho route vault/secrets.
- [ ] `modules/onboarding/` + tự hoàn tất khi đã có tác phẩm.
- [ ] Phát `vault.status`; expose `on_change` cho F12; `waiting_jobs`.
- [ ] Đo thời gian unlock trên máy tham chiếu Win/Mac, ghi ADR (không đặt số trước khi đo).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Mã hóa/giải mã vòng; sửa 1 byte ciphertext/AAD/kdf → `InvalidTag`; nonce khác nhau giữa hai lần ghi; NFC/NFD cùng mật khẩu mở được | `be/tests/unit/secrets/test_vault_crypto.py` |
| unit | Scrypt fallback khi giả lập Argon2id không hỗ trợ; mở vault scrypt | `be/tests/unit/secrets/test_vault_kdf.py` |
| unit | `SecretStore.availability/get` cho mọi tổ hợp session/vault/khóa/thiếu | `be/tests/unit/secrets/test_secret_store.py` |
| unit | Throttle: thời gian chờ tăng, reset khi đúng | `be/tests/unit/secrets/test_unlock_throttle.py` |
| integration | API vòng đời: tạo → khóa → mở sai/đúng → đổi mật khẩu → đặt lại; `vault.status` phát qua SSE | `be/tests/integration/vault/test_vault_api.py` |
| integration | Không rò rỉ: sau các thao tác, grep data-root (DB, log, tmp) không thấy giá trị key; lỗi validate không chứa giá trị | `be/tests/integration/vault/test_no_secret_leak.py` |
| integration | Kill tiến trình giữa lúc ghi vault (subprocess) → file cũ hoặc mới đầy đủ, mở được | `tests/integration/test_vault_crash_write.py` |
| integration | Onboarding: DB trống → pending; có tác phẩm → tự completed; complete/skip | `be/tests/integration/onboarding/test_onboarding_api.py` |
| integration | Job giả cần key + vault khóa → `waiting_slot VAULT_LOCKED`; unlock → chạy tiếp (sau khi F12 có scheduler; trước đó test callback `on_change`) | `be/tests/integration/vault/test_vault_locked_jobs.py` |

## Tên mới đề xuất

- API: `POST /v1/vault`, `POST /v1/vault/change-password`, `POST /v1/vault/reset`, `PUT /v1/vault/mode`, `GET /v1/secrets`, `PUT /v1/secrets/{ref}`, `DELETE /v1/secrets/{ref}`, `GET /v1/onboarding`, `PUT /v1/onboarding`, `POST /v1/onboarding/complete`.
- Mã lỗi: `VAULT_PASSWORD_INVALID`, `VAULT_UNLOCK_THROTTLED`, `VAULT_ALREADY_EXISTS`, `VAULT_NOT_FOUND`, `VAULT_CORRUPT`, `SECRET_MISSING` (cả là `wait_reason`).
- Setting key: `vault.mode`, `secrets.index`, `onboarding.state`.
- File/định dạng: trường JSON của `secrets.enc` (`format`, `version`, `vault_id`, `kdf`, `cipher`, `nonce`, `ciphertext`), file tạm `secrets.enc.tmp`.
- Module: `infrastructure/secrets/session_store.py`, `secret_store.py`, `redaction.py`; `modules/vault/`, `modules/onboarding/`; lớp `VaultService`, `SessionSecretStore`, `SecretStore`, `VaultLockedError`, `SecretMissingError`; schema `VaultStatus`, `SecretInfo`, `OnboardingState`.
- Quy ước `secret_ref` dạng `provider:<provider_id>:api_key` (F04 xác nhận).
