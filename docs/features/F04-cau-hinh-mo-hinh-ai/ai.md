# F04 — AI

Phần AI của F04 là **tầng adapter provider**: liệt kê model, kiểm tra kết nối, chuẩn hóa metadata và ánh xạ effort sang tham số request. Không có prompt hay workflow sinh văn bản. BE (`infrastructure/ai/discovery.py`, `model_resolver.py`) điều phối và lưu DB; AI không import BE (Arch §6).

## Module và file

```text
ai/src/writestory_ai/
  contracts/models.py          ProviderConfig, DiscoveredModel, ModelListResult, EffortLevel,
                               ModelSelection, RequestOptions, ProviderErrorInfo
  ports/provider.py            TextProvider Protocol: list_models(), test_connection(), stream()/generate()
  providers/anthropic.py       Messages API + GET /v1/models (phân trang)
  providers/openai_compatible.py  Chat Completions + GET /v1/models (data[].id)
  providers/ollama.py          Ollama/LM Studio: kế thừa openai_compatible, không cần key, timeout dài hơn cho model local
  providers/effort.py          map_effort(protocol, model_meta, effort) → tham số request hoặc None + ghi chú
  providers/registry.py        protocol → class adapter
  policies/retry.py            Retry transport hữu hạn (dùng chung với F10/F12)
ai/tests/unit/providers/, ai/tests/contract/providers/, ai/tests/fixtures/mock_provider.py
```

## Contract (Pydantic)

```text
EffortLevel = Literal["low","medium","high","xhigh","max"]
Protocol    = Literal["anthropic","openai_compatible","ollama_lmstudio"]

ProviderConfig:   protocol, base_url, api_key: SecretStr | None, timeout_s=10, extra_headers={}
DiscoveredModel:  model_id, display_name | None, max_input_tokens | None, max_tokens | None,
                  supported_efforts: list[EffortLevel] | None   # None = server không cho biết
                  supports_structured_outputs: bool | None, capabilities_raw: dict | None
ModelListResult:  models: list[DiscoveredModel] (giữ thứ tự server), pages: int
ProviderErrorInfo: code (PROVIDER_AUTH|PROVIDER_UNREACHABLE|PROVIDER_RATE_LIMIT),
                  http_status | None, reason | None, retry_after_s | None, message (không chứa key)
ConnectionTestResult: ok, latency_ms, model_count | None, called_model | None, error | None

ModelSelection:   role, provider_id, model_id (ID gửi lên server, đã thay biến thể 1M nếu có),
                  effort: EffortLevel | None, max_input_tokens, max_tokens, extra_params: dict,
                  supported_efforts | None, supports_structured_outputs | None, notes: list[str]
RequestOptions:   model, max_tokens, effort | None, extra_params, stream: bool, response_schema | None
```

`ModelSelection` là hình chiếu phía AI của `PinnedModelConfig` (BE). Workflow (F06, F10) nhận `dict[role, ModelSelection]` trong input, không tự chọn model, không đọc settings.

## Workflow

**list_models (Anthropic)**:

1. `GET {root}/v1/models?limit=1000` với header `x-api-key`, `anthropic-version: 2023-06-01`; `root` = `base_url` bỏ `/` cuối và bỏ hậu tố `/v1` nếu có.
2. Lặp khi `has_more=true`: thêm `after_id=<last_id>` (giới hạn 20 trang, vượt → `bad_response`).
3. Mỗi phần tử → `DiscoveredModel`: `id`, `display_name`, `max_input_tokens`, `max_tokens`; `supported_efforts` = các mức `L` có `capabilities.effort[L].supported == true` khi `capabilities.effort.supported == true`; `[]` khi `capabilities.effort.supported == false`; `None` khi không có `capabilities`. `supports_structured_outputs` = `capabilities.structured_outputs.supported`. Lưu `capabilities_raw`.

**list_models (OpenAI-compatible, Ollama/LM Studio)**:

1. `GET {root}/v1/models`, header `Authorization: Bearer <key>` (bỏ header khi không có key).
2. Đọc `data[].id`; các trường khác `None` trừ khi gateway trả thêm trường mở rộng có tên trùng (`display_name`, `max_input_tokens`, `max_tokens`) thì đọc (Plan §7.1).
3. Thiếu `data` hoặc không phải mảng → `ProviderErrorInfo(PROVIDER_UNREACHABLE, reason=bad_response)`.

**test_connection**: không có `model_id` → gọi `list_models` trang đầu (`limit=1` với Anthropic) và đo `latency_ms`. Có `model_id` → một request sinh tối thiểu (`max_tokens` nhỏ, prompt cố định "ping") để xác nhận model gọi được; BE ghi `last_call_ok_at` ("✓ đã thử gọi").

**Ánh xạ effort** (`providers/effort.py`, Plan §7.1):

| Giao thức | Effort khác None và nằm trong `supported_efforts` | Không hỗ trợ / `supported_efforts` None |
|---|---|---|
| `anthropic` | Gửi `output_config: {effort: "<level>"}` | Không gửi; note `effort_dropped_unsupported` |
| `openai_compatible` | Gửi tham số reasoning của endpoint với giá trị mức nguyên văn (giả định: Chat Completions `reasoning_effort`); chỉ khi người dùng khai báo mức hỗ trợ cho model | Không gửi; note vào trace |
| `ollama_lmstudio` | MVP không gửi | note `effort_not_applicable_local` |

Effort trống = không gửi tham số, dùng mặc định provider (Anthropic mặc định `high`, riêng một số model như Opus 5.5 là `medium` – Plan §7.1). Adapter **không** đổi effort giữa các request của cùng một `ModelSelection`; đổi effort top-level giữa các request làm mất prompt cache (Plan §7.1, §6.4).

## Prompt

Không áp dụng – F04 không có prompt. Request `test_connection` dùng chuỗi cố định trong code, không qua template.

## Model, effort, giới hạn

- Vai trò (Plan §7.1): `planner`, `writer`, `checker` (Kiểm tra/Settle), `reviewer` (Mối nối & Review), `summary`. Gợi ý ban đầu: planner/writer model mạnh nhất `high`; checker/reviewer model cân bằng `medium`; summary model rẻ `low` (điều chỉnh sau bộ đánh giá tiếng Việt R2).
- `max_tokens` lấy từ `ModelSelection.max_tokens`; workflow có thể đặt thấp hơn theo bước. Effort cao tăng token đầu ra nên vai trò Viết cần `max_tokens` đủ lớn (Plan §7.1).
- Structured output: adapter Anthropic gửi `output_config.format` (JSON schema) khi `supports_structured_outputs`; nếu không, workflow dùng chế độ JSON + parse + một lần sửa (Plan §23.3 #2, chi tiết ở F10). Adapter không tự gửi tham số `thinking`; cấu hình thinking chốt ở F10 nếu cần.
- Timeout (Plan §6.6): discovery/test 10 s tổng; generation có connect, first-token, stream-idle, overall deadline (giá trị chốt ở F10/F12). Ollama/LM Studio: first-token dài hơn vì nạp model (giả định, đo ở R2).
- Retry transport (`policies/retry.py`): tối đa 3 lần, backoff + jitter, ưu tiên `Retry-After`; không retry 401/403/model-not-found (Plan §4.2). Discovery chỉ retry 429 một lần.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Không áp dụng cho discovery; với `test_connection` có `model_id`, `stop_reason=refusal` vẫn tính là kết nối thành công, ghi chú |
| Bị cắt `max_tokens` | Không áp dụng (test dùng output tối thiểu) |
| JSON không hợp lệ | `/v1/models` trả không phải JSON/thiếu trường → `PROVIDER_UNREACHABLE` `reason=bad_response`, kèm 200 ký tự đầu (đã che key) cho log debug |
| 401/403 | `PROVIDER_AUTH`, không retry |
| 404 | `PROVIDER_UNREACHABLE` `reason=endpoint_not_found` (base URL sai hoặc server không có endpoint) |
| Timeout/DNS/TLS | `PROVIDER_UNREACHABLE` `reason=timeout|connection` |
| 429 | `PROVIDER_RATE_LIMIT` + `retry_after_s` |
| Model trùng ID trong cùng trang | Giữ lần đầu, bỏ lần sau |
| Key xuất hiện trong thông báo lỗi server | Lọc chuỗi key khỏi `message` trước khi trả |

## Đánh giá

- Không có rubric chất lượng văn; đánh giá bằng contract test với fixture ghi/phát lại response (Plan §23.2 #13).
- Bộ dữ liệu mẫu: `ai/tests/fixtures/models/anthropic_page1.json`, `anthropic_page2.json`, `openai_compatible.json`, `lmstudio.json`, `bad_payload.json` (không chứa key thật).

## Việc cần làm

- [ ] `contracts/models.py` và `ports/provider.py` (`TextProvider` Protocol).
- [ ] Adapter `anthropic`, `openai_compatible`, `ollama` + `registry`.
- [ ] Chuẩn hóa `DiscoveredModel` cho cả hai định dạng; xử lý `root` URL.
- [ ] `providers/effort.py` + ghi chú trace.
- [ ] Mở rộng `mock_provider.py` với `models_endpoint` (Anthropic có phân trang / OpenAI-compatible) như tests/README.
- [ ] Test live (đánh dấu `live`) với provider thật chỉ chạy khi cấu hình rõ.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Chuẩn hóa capabilities → `supported_efforts` (`None`/`[]`/danh sách) | `ai/tests/unit/providers/test_normalize_models.py` |
| unit | `map_effort` theo giao thức, mức không hỗ trợ bị bỏ kèm note | `ai/tests/unit/providers/test_effort_mapping.py` |
| unit | Ghép URL: `https://x`, `https://x/`, `https://x/v1` → cùng `…/v1/models` | `ai/tests/unit/providers/test_base_url.py` |
| contract (mock provider) | Anthropic 2 trang `has_more/after_id`; OpenAI-compatible `data[].id`; 401/404/429/timeout/JSON hỏng | `ai/tests/contract/providers/test_list_models.py` |
| contract (mock provider) | Request Anthropic chứa `output_config.effort` đúng mức; không có khi effort None | `ai/tests/contract/providers/test_request_params.py` |

Luồng: [T03](../../tests/flows/T03-cau-hinh-mo-hinh-ai.md), [T15](../../tests/flows/T15-loi-provider.md).

## Tên mới đề xuất

- File: `ai/src/writestory_ai/contracts/models.py`, `ai/src/writestory_ai/providers/effort.py`.
- Contract: `ProviderConfig`, `DiscoveredModel`, `ModelListResult`, `ProviderErrorInfo`, `ConnectionTestResult`, `ModelSelection`, `RequestOptions`, `EffortLevel`.
- Method port: `TextProvider.list_models()`, `TextProvider.test_connection()`; hàm `map_effort()`.
- Note trace: `effort_dropped_unsupported`, `effort_not_applicable_local`, `model_missing_on_server`.
