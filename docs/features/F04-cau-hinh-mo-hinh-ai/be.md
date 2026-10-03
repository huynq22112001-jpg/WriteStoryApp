# F04 — Backend

## Module và file

```text
be/src/writestory_be/modules/settings/
  router.py        /v1/providers*, /v1/settings/roles, /v1/settings/limits
  schemas.py       ProviderIn/Out, ProviderModelOut, ModelsPutIn, DiscoveryResult, RoleAssignment, LimitsIn/Out
  service.py       Use case: tạo/sửa provider, test, discover, sửa danh sách model, vai trò, limits
  domain.py        Thuần: merge_discovered(), effective_models(), resolve_effort(), validate_roles()
be/src/writestory_be/infrastructure/ai/
  factory.py       Tạo TextProvider từ ProviderConfig + secret (lấy từ vault/RAM phiên), một httpx.AsyncClient/provider
  discovery.py     Điều phối: gọi adapter.list_models() → domain.merge_discovered() → ghi qua writer queue (Plan §7.1)
  model_resolver.py ModelResolver: (work_id, role) → PinnedModelConfig; ghim vào job (F12 gọi)
  limits.py        Chỉ đọc cấu hình provider_limits cho limiter của F12 (thực thi limiter thuộc F12)
be/src/writestory_be/infrastructure/db/models/settings.py   ORM 5 bảng dưới
be/migrations/versions/<rev>_f04_providers_models_roles.py
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `providers` | `id` TEXT PK, `name`, `protocol` (`anthropic`\|`openai_compatible`\|`ollama_lmstudio`), `base_url`, `secret_ref` NULL, `key_storage` (`vault`\|`session`\|`none`), `auto_discover` BOOL=1, `prefer_long_context` BOOL=0, `default_effort` NULL, `enabled` BOOL=1, `discovery_status` (`never`\|`ok`\|`error`\|`waiting_vault`), `discovery_error` JSON NULL, `discovered_at` NULL, `discovery_attempted_at` NULL, `connection_status` (`unknown`\|`ok`\|`error`), `connection_checked_at`, `revision` INT, `created_at`, `updated_at` | UNIQUE(`name`); CHECK `default_effort IN (low,medium,high,xhigh,max)` | Plan §5 "providers": chỉ lưu reference tới secret. `ollama_lmstudio` cho phép `key_storage=none` |
| `provider_models` | `id` PK, `provider_id` FK CASCADE, `model_id`, `position` INT NULL, `source` (`discovered`\|`manual`), `discovery_rank` INT NULL, `display_name`, `max_input_tokens`, `max_tokens`, `supported_efforts` JSON NULL, `capabilities` JSON NULL, `price_input_per_mtok`, `price_output_per_mtok`, `price_cache_read_per_mtok`, `price_cache_write_per_mtok` (REAL NULL, USD), `allowed_roles` JSON NULL, `max_concurrent_requests` INT NULL, `long_context_variant_model_id` NULL, `long_context_params` JSON NULL, `tokens_per_syllable` REAL NULL, `user_edited_fields` JSON `[]`, `first_seen_at`, `last_seen_at` NULL, `missing_since` NULL, `last_call_ok_at` NULL, `updated_at` | UNIQUE(`provider_id`,`model_id`); INDEX(`provider_id`,`position`) | Plan §5 "provider_models". `position` NOT NULL ⇔ thuộc danh sách ghi đè. `supported_efforts`: NULL = chưa biết, `[]` = không hỗ trợ effort |
| `role_models` | `id` PK, `work_id` NULL FK `works` CASCADE, `role` (`planner`\|`writer`\|`checker`\|`reviewer`\|`summary`), `provider_id` NULL, `model_id` NULL, `effort` NULL, `updated_at` | UNIQUE partial: (`role`) WHERE `work_id IS NULL`; (`work_id`,`role`) WHERE `work_id IS NOT NULL` | Plan §5 "role_models". NULL = kế thừa cấp trên |
| `provider_limits` | `provider_id` PK FK, `max_concurrent_requests` INT, `rpm` INT NULL, `tpm` INT NULL, `max_retries` INT=3, `updated_at` | — | Mặc định: cloud 4, `ollama_lmstudio` 1 (Plan §4.2, UI §5.6.3) |
| `settings` | `key` TEXT PK, `value` JSON, `updated_at` | — | Khóa F04: `scheduler.worker_pool` (4), `budget.app_daily_usd`, `budget.app_daily_tokens`, `budget.work_daily_usd_default`, `budget.timezone` (IANA) |

Migration mới, không backfill. Khi tạo provider, service tạo luôn dòng `provider_limits` theo mặc định của giao thức. Không có cột chứa API key ở bất kỳ bảng nào.

## API

Lỗi theo Plan §23.1.D. Mã HTTP giả định (chốt ở F01): `VALIDATION` 422, `NOT_FOUND` 404, `REVISION_CONFLICT` 409, `VAULT_LOCKED` 423, `PROVIDER_IN_USE` 409.

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/providers` | — | `[ProviderOut]` (không có key; có `has_key`, `discovery_status`, `discovery_error`, `effective_default_model_id`) | — |
| POST | `/v1/providers` | `{name, protocol, base_url, api_key?, key_storage}` | `201 ProviderOut` | `VALIDATION`, `VAULT_LOCKED` (khi `key_storage=vault` mà vault khóa) |
| PATCH | `/v1/providers/{id}` | `{expected_revision, name?, base_url?, api_key?, key_storage?, auto_discover?, prefer_long_context?, default_effort?\|null, enabled?}` | `ProviderOut` | `NOT_FOUND`, `REVISION_CONFLICT`, `VALIDATION`, `VAULT_LOCKED` |
| DELETE | `/v1/providers/{id}` | — | `204` | `NOT_FOUND`, `PROVIDER_IN_USE` (job đang chạy ghim provider) |
| POST | `/v1/providers/test` | `{provider_id?}` hoặc `{protocol, base_url, api_key?}`; tùy chọn `model_id` | `{ok, latency_ms, model_count?, called_model?, error?: ErrorBody}` | `VALIDATION`, `VAULT_LOCKED` |
| POST | `/v1/providers/{id}/discover` | — | `DiscoveryResult {status: ok\|error, found, added[], missing[], reappeared[], error?: ErrorBody, discovered_at}` | `NOT_FOUND`, `VAULT_LOCKED` |
| GET | `/v1/providers/{id}/models` | — | `{override_active, default_model_id, effective: [ProviderModelOut], others: [ProviderModelOut], revision}` | `NOT_FOUND` |
| PUT | `/v1/providers/{id}/models` | `{expected_revision, items: [{model_id, display_name?, max_input_tokens?, max_tokens?, supported_efforts?, price_*?, allowed_roles?, max_concurrent_requests?, long_context_variant_model_id?, long_context_params?, reset_fields?: [str]}]}` | như GET | `REVISION_CONFLICT`, `VALIDATION` (trùng `model_id`, effort lạ, số âm) |
| GET | `/v1/settings/roles` | `?work_id=` (tùy chọn) | `{scope: app\|work, roles: [{role, provider_id, model_id, effort, inherited_from: work\|app\|default}]}` | `NOT_FOUND` |
| PUT | `/v1/settings/roles` | `?work_id=`; `{roles: [{role, provider_id?, model_id?, effort?}]}` | như GET | `VALIDATION` (model không thuộc danh sách hiệu lực, effort không hỗ trợ, `allowed_roles` không cho phép) |
| GET/PUT | `/v1/providers/{id}/limits` | PUT `{max_concurrent_requests, rpm?, tpm?, max_retries}` | `LimitsOut` | `VALIDATION` (concurrency < 1) |
| GET/PUT | `/v1/settings/limits` | PUT `{worker_pool, app_daily_usd?, app_daily_tokens?, work_daily_usd_default?, timezone}` | như GET | `VALIDATION` (timezone không hợp lệ) |

`POST /discover` trả 200 cả khi provider lỗi (`status=error`): lần thử đã được lưu và hiển thị trên nút (Plan §7.1 bước 5). Chỉ lỗi nội bộ app (vault khóa, không tìm thấy) mới trả mã lỗi HTTP. `DELETE` model khỏi danh sách = PUT không còn mục đó: mục `manual` bị xóa hẳn, mục `discovered` chỉ đặt `position=NULL` (về "Model khả dụng khác").

## Logic xử lý

**Discovery** (`discovery.py`, Plan §7.1):

1. Kích hoạt: (a) sau readiness, task nền cho mỗi provider `enabled && auto_discover` (không chặn khởi động); (b) `POST /discover`. Provider có `auto_discover=false` không tự gọi; nếu danh sách ghi đè rỗng, FE nhắc thêm model.
2. Lấy secret: `key_storage=vault` mà vault khóa → `discovery_status=waiting_vault`, đăng ký chạy lại khi nhận `vault.status` = unlocked; `POST /discover` trả `VAULT_LOCKED`.
3. Gọi `TextProvider.list_models()` (ai.md), timeout tổng 10 giây (Plan §7.1 "khoảng 10 giây"). Không giữ transaction DB trong lúc gọi mạng.
4. Thất bại (bất kỳ trang nào): lưu `discovery_status=error`, `discovery_error={code, http_status, reason, message, at}`, `discovery_attempted_at`; **không** đụng `provider_models`. Ánh xạ: 401/403 → `PROVIDER_AUTH`; 404 → `PROVIDER_UNREACHABLE` + `reason=endpoint_not_found`; timeout/kết nối/DNS → `PROVIDER_UNREACHABLE` + `reason=timeout|connection`; 429 → `PROVIDER_RATE_LIMIT` (retry 1 lần theo `Retry-After` nếu ≤ 10 s); JSON sai/thiếu `data` → `PROVIDER_UNREACHABLE` + `reason=bad_response`.
5. Thành công: `domain.merge_discovered(rows, discovered, now)` trong **một** transaction qua writer queue:
   - Model mới → INSERT `source=discovered`, `position=NULL`, `discovery_rank=i`, `first_seen_at=last_seen_at=now`.
   - Model đã có → `last_seen_at=now`, `missing_since=NULL`, `discovery_rank=i`; với mỗi trường discoverable (`display_name`, `max_input_tokens`, `max_tokens`, `supported_efforts`) chỉ cập nhật khi **không** nằm trong `user_edited_fields` và giá trị mới khác NULL. `capabilities` (thô) luôn cập nhật.
   - Dòng có `last_seen_at` khác NULL nhưng không có trong lần này → `missing_since=now` nếu đang NULL (⚠). Dòng `manual` chưa từng thấy (`last_seen_at` NULL) không bị đánh ⚠ mà báo "chưa thấy trên server".
   - Không bao giờ DELETE trong merge.
6. Cập nhật `discovery_status=ok`, `discovered_at`; phát `provider.status`; trả `added/missing/reappeared`.

**Danh sách hiệu lực** (`domain.effective_models`): nếu tồn tại dòng `position NOT NULL` → các dòng đó theo `position` tăng dần; ngược lại → dòng `source=discovered` có `missing_since IS NULL` theo `discovery_rank`. `default_model_id` = phần tử đầu. `others` = dòng discovered không thuộc danh sách hiệu lực.

**Sửa danh sách** (`PUT /models`): kiểm `expected_revision` = `providers.revision`; với mỗi item tạo/cập nhật dòng, gán `position` theo thứ tự mảng; trường nào client gửi khác giá trị đang lưu thì thêm vào `user_edited_fields`; `reset_fields` xóa khỏi `user_edited_fields` và chép lại giá trị từ `capabilities`/lần discovery gần nhất (nếu không còn thì NULL). Tăng `revision`.

**Resolver** (`model_resolver.py`, gọi lúc job bắt đầu – F12; mỗi chương là một job nên đổi cài đặt áp từ chương kế tiếp):

1. Model: `role_models(work_id, role)` → `role_models(NULL, role)` → model mặc định của provider ưu tiên (provider đầu tiên `enabled`). Khi dùng model mặc định (người dùng chưa chọn cho vai trò) và `prefer_long_context=true` và dòng có `long_context_variant_model_id`/`long_context_params` → dùng biến thể (Plan §7.1).
2. Model mặc định có `allowed_roles` không chứa vai trò → lấy model đầu tiên trong danh sách hiệu lực cho phép vai trò; không có → lỗi `VALIDATION` (`detail.reason=no_model_for_role`).
3. Model có `missing_since` → vẫn dùng, thêm `notes: ["model_missing_on_server"]`; lỗi model-not-found lúc gọi thì không retry (Plan §4.2).
4. Effort: vai trò truyện → vai trò app → `providers.default_effort` → không gửi. Mức chọn không nằm trong `supported_efforts` (hoặc `supported_efforts` NULL) → bỏ, thêm note `effort_dropped_unsupported`.
5. Trả `PinnedModelConfig {provider_id, model_id, request_model_id, effort, max_input_tokens, max_tokens, extra_params, prices, notes, resolved_at}`; F12 lưu vào job (input/pinned config). Mọi bước, retry và vòng sửa của job dùng đúng cấu hình đã ghim; không đọc lại settings giữa chừng (Plan §7.1 "giữ effort cố định trong một lượt viết").

Quy tắc transaction: không transaction nào bao quanh request mạng; merge và PUT là transaction ngắn qua writer queue. Secret chỉ đọc trong `factory.py`, không truyền vào schema/log.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `provider.status` | Discovery xong/lỗi, đổi `connection_status`, chuyển `waiting_vault` | `{provider_id, discovery_status, found?, added?, missing?, error?: {code, reason, http_status}, at}` |

Không tạo job bền cho discovery (tác vụ ngắn, không tốn token sinh văn bản). F04 tiêu thụ `vault.status` để chạy lại discovery đang `waiting_vault`.

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| `base_url` có sẵn hậu tố `/v1` hoặc dấu `/` cuối | Chuẩn hóa khi lưu: bỏ `/` cuối; adapter tự tránh `/v1/v1` | — |
| `base_url` không phải http(s) hoặc rỗng | Từ chối | `VALIDATION` |
| Anthropic phân trang vô hạn (`has_more` luôn true) | Giới hạn 20 trang × 1.000 (giả định đủ), vượt → lỗi `bad_response` | `PROVIDER_UNREACHABLE` |
| Trùng `model_id` khác hoa/thường | Coi là khác nhau (ID nguyên văn), không gộp | — |
| Xóa provider đang được vai trò tham chiếu | Cho xóa nếu không có job chạy; `role_models` tham chiếu chuyển NULL (kế thừa) và trả `warnings` | `PROVIDER_IN_USE` nếu có job |
| Đổi `base_url`/giao thức | Đặt `discovery_status=never`, giữ danh sách cũ, chạy discovery nếu `auto_discover` | — |
| Vai trò gán model ⚠ | Cho phép, UI cảnh báo | — |
| Hai tab sửa cùng danh sách | `expected_revision` | `REVISION_CONFLICT` |
| `key_storage=session` rồi khởi động lại app | `has_key=false`; job cần key → `waiting_slot` lý do `VAULT_LOCKED` (F12, Plan §23.2 #7) | — |

## Việc cần làm

- [x] Migration 5 bảng + partial unique index cho `role_models`.
- [x] ORM + repository; service CRUD provider; tích hợp vault (F03) qua port `SecretStore`.
- [x] `discovery.py` + task nền sau readiness + chạy lại khi vault mở.
- [x] `domain.merge_discovered`, `effective_models`, `resolve_effort` (thuần, có unit test).
- [x] API bảng trên + schema Pydantic; export OpenAPI.
- [ ] `ModelResolver` + `PinnedModelConfig`; hook để F12 gọi khi job bắt đầu.
- [x] `limits.py` đọc cấu hình cho F12; mặc định theo giao thức.
- [x] Che secret: filter log, kiểm tra response/OpenAPI example không có key.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Merge: thêm mới, giữ trường người dùng sửa, ⚠ missing, reappeared, manual chưa thấy, không xóa | `be/tests/unit/settings/test_merge_discovered.py` |
| unit | Danh sách hiệu lực ghi đè/tự lấy, mặc định, `others` | `be/tests/unit/settings/test_effective_models.py` |
| unit | Resolver: thứ tự vai trò, context dài, `allowed_roles`, effort không hỗ trợ bị bỏ | `be/tests/unit/settings/test_model_resolver.py` |
| integration | Discover với mock provider `models_endpoint` Anthropic (2 trang) và OpenAI-compatible; lỗi 401/404/timeout giữ danh sách cũ | `be/tests/integration/settings/test_discovery_api.py` |
| integration | Vault khóa → `waiting_vault` → mở vault → discovery chạy lại, phát `provider.status` | `be/tests/integration/settings/test_discovery_vault.py` |
| integration | Job ghim cấu hình; đổi vai trò giữa job không ảnh hưởng job đang chạy, áp ở job sau | `be/tests/integration/settings/test_pinned_config.py` |
| contract | Snapshot OpenAPI các endpoint F04; không có trường key trong response | `be/tests/contract/test_openapi_settings.py` |

Luồng: [T03](../../tests/flows/T03-cau-hinh-mo-hinh-ai.md), [T15](../../tests/flows/T15-loi-provider.md).

## Tên mới đề xuất

- API: `POST /v1/providers`, `PATCH /v1/providers/{id}`, `DELETE /v1/providers/{id}`, `GET|PUT /v1/providers/{id}/limits`, `GET|PUT /v1/settings/limits`, query `?work_id=` cho `/v1/settings/roles`.
- Mã lỗi: `PROVIDER_IN_USE`, `NOT_FOUND` (nếu F01 chưa có); `detail.reason` cho `PROVIDER_UNREACHABLE`: `timeout|connection|endpoint_not_found|bad_response`.
- Cột `providers`: `name`, `protocol` (giá trị `anthropic|openai_compatible|ollama_lmstudio`), `secret_ref`, `key_storage`, `auto_discover`, `prefer_long_context`, `default_effort`, `enabled`, `discovery_status`, `discovery_error`, `discovered_at`, `discovery_attempted_at`, `connection_status`, `connection_checked_at`, `revision`.
- Cột `provider_models`: `position`, `source`, `discovery_rank`, `supported_efforts`, `capabilities`, `price_input_per_mtok`, `price_output_per_mtok`, `price_cache_read_per_mtok`, `price_cache_write_per_mtok`, `allowed_roles`, `max_concurrent_requests`, `long_context_variant_model_id`, `long_context_params`, `tokens_per_syllable`, `user_edited_fields`, `first_seen_at`, `last_seen_at`, `missing_since`, `last_call_ok_at`.
- Cột `role_models`: `work_id`, `role` (giá trị `planner|writer|checker|reviewer|summary`), `provider_id`, `model_id`, `effort`.
- Cột `provider_limits`: `max_concurrent_requests`, `rpm`, `tpm`, `max_retries`. Khóa `settings`: `scheduler.worker_pool`, `budget.app_daily_usd`, `budget.app_daily_tokens`, `budget.work_daily_usd_default`, `budget.timezone`.
- Code: `PinnedModelConfig`, `merge_discovered`, `effective_models`, `resolve_effort`, port `SecretStore`.
