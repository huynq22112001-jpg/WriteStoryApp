# T03 — Cấu hình mô hình AI

Tính năng: F04. Nguồn: Plan §7.1, §7 (API providers/settings), FL26, §5 (`providers`, `provider_models`, `role_models`), UI §5.6.1–5.6.2. Cấp test chính: contract, integration, e2e-fe.

## Mục đích

Chứng minh việc tự lấy danh sách model (Anthropic có phân trang, OpenAI-compatible, Ollama/LM Studio), merge không ghi đè trường người dùng sửa, danh sách ghi đè có thứ tự, effort và model theo vai trò được áp đúng thứ tự ưu tiên và được ghim vào job.

## Tiền điều kiện và dữ liệu

- Data-root tạm, vault đã mở (T02), một truyện `tests/fixtures/stories/tien_hiep_01/`.
- Mock provider Anthropic: `{models_endpoint: "anthropic", models_pages: 2}` trang 1 trả `has_more=true`, `after_id` hợp lệ; tổng 5 model, model `claude-pro` có `capabilities.effort.{low,medium,high,xhigh,max}.supported=true`, `structured_outputs=true`.
- Mock OpenAI-compatible: `{models_endpoint: "openai", ...}` chỉ trả `data[].id` (3 model).
- Mock Ollama: `{models_endpoint: "openai", require_key: false}`.
- `fail_sequence` dùng riêng cho discovery: `[401]`, `[404]`, `[timeout(11s)]`, `[bad_json]`.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T03-01 | thành công | `POST /v1/providers/{id}/discover` với mock Anthropic 2 trang. | Gọi `GET {base_url}/v1/models` với `x-api-key` + `anthropic-version`, theo `after_id` tới hết; `provider_models` có 5 dòng nguồn `discovered`, đủ `display_name`, `max_input_tokens`, `max_tokens`, effort hỗ trợ; response báo 5 mới, 0 biến mất. | contract, integration | `ai/tests/contract/test_discovery_anthropic.py`, `be/tests/integration/test_provider_discover.py` |
| T03-02 | thành công | Discover với mock OpenAI-compatible. | Header `Authorization: Bearer`; 3 dòng chỉ có `model_id`; context/output/effort/giá để trống; UI mục mở rộng cho người dùng tự điền. | contract | `ai/tests/contract/test_discovery_openai_compat.py` |
| T03-03 | thành công | Discover Ollama/LM Studio không nhập key. | Không gửi header key, không yêu cầu vault mở; model được thêm; `max_concurrent_requests` mặc định 1. | integration | `be/tests/integration/test_provider_local.py` |
| T03-04 | biên | 1. Người dùng sửa `display_name` và giá của `claude-pro`. 2. Mock đổi `display_name` server. 3. Discover lại. | Trường người dùng sửa giữ nguyên; trường khác cập nhật; thời điểm thấy gần nhất cập nhật. | integration | `be/tests/integration/test_provider_merge_user_fields.py` |
| T03-05 | biên | Mock bỏ 1 model khỏi danh sách; discover lại. | Model không bị xóa, được đánh dấu ⚠ "không còn trên server"; response báo 1 biến mất; nếu model đó đang trong danh sách ghi đè thì UI hiện ⚠ tại dòng. | integration, e2e-fe | `be/tests/integration/test_provider_missing_model.py`, `fe/tests/e2e/models_settings.spec.ts` |
| T03-06 | lỗi | Discover lần lượt với `401`, `404`, timeout 11 s (vượt timeout ~10 s), JSON sai. | Mỗi lỗi lưu kèm thời điểm, nút "Kiểm tra lấy danh sách" chấm đỏ kèm thông điệp cụ thể (sai key / endpoint không có / quá thời gian / dữ liệu không hợp lệ); 401 trả `PROVIDER_AUTH`, timeout trả `PROVIDER_UNREACHABLE`; danh sách đã có không mất dòng nào. | integration | `be/tests/integration/test_provider_discover_errors.py` |
| T03-07 | thành công | Bật "Tự lấy danh sách model", khởi động lại với mock trễ 8 s. | Readiness không chờ discovery (readiness < mock latency); discovery chạy nền, kết quả xuất hiện sau; event `provider.status` phát khi xong. | integration | `be/tests/integration/test_discovery_background.py` |
| T03-08 | biên | Tắt tự lấy: (a) danh sách thủ công có 2 model; (b) danh sách rỗng. Khởi động lại. | (a) Mock nhận 0 request `/v1/models`. (b) Không gọi; UI nhắc người dùng thêm model. | integration, e2e-fe | `be/tests/integration/test_discovery_disabled.py` |
| T03-09 | thành công | `PUT /v1/providers/{id}/models` với danh sách ghi đè `[claude-balance, claude-pro]`; sau đó xóa hết danh sách ghi đè. | Có mục: danh sách hiệu lực đúng thứ tự, mặc định = `claude-balance`; model tự lấy khác nằm ở "Model khả dụng khác". Rỗng: danh sách hiệu lực = toàn bộ danh sách tự lấy. | integration, e2e-fe | `be/tests/integration/test_effective_model_list.py`, `fe/tests/e2e/models_reorder.spec.ts` |
| T03-10 | thành công | Đặt effort: truyện ghi đè vai trò Viết = `max`; toàn app vai trò Viết = `high`; effort mặc định = `medium`. Chạy job write rồi bỏ lần lượt từng mức. | Request writer gửi `output_config.effort` = `max`, rồi `high`, rồi `medium`, cuối cùng không gửi tham số (mặc định provider). Trace ghi nguồn của effort. | contract, integration | `be/tests/integration/test_effort_precedence.py` |
| T03-11 | biên | Model OpenAI-compatible không khai báo hỗ trợ effort; vai trò đặt `high`. Model Anthropic chỉ hỗ trợ `low/medium/high`, cấu hình `xhigh`. | OpenAI-compatible: request không có tham số reasoning, trace ghi chú đã bỏ. Anthropic: không gửi mức ngoài danh sách hỗ trợ; UI ô chọn chỉ hiện mức được hỗ trợ, khóa kèm giải thích khi model không hỗ trợ effort. | contract, e2e-fe | `ai/tests/contract/test_effort_mapping.py` |
| T03-12 | thành công | `PUT /v1/settings/roles`: Lập kế hoạch/Viết = `claude-pro` `high`; Kiểm tra/Settle, Mối nối/Review = `claude-balance` `medium`; Tóm tắt = `claude-balance` `low`. Chạy 1 chương. | Mỗi bước gọi đúng model + effort theo vai trò (đối chiếu log mock theo bước `plan`, `write`, `settle`, `validate`, `seam`, `review`, `summary`). | integration | `be/tests/integration/test_role_models.py` |
| T03-13 | biên | Job write đang chạy ở bước `write`; đổi vai trò Viết sang model khác và effort khác. | Job hiện tại giữ model + effort đã ghim (mọi request còn lại của job dùng giá trị cũ); chương kế tiếp dùng giá trị mới; UI ghi "áp từ chương kế tiếp". | integration | `be/tests/integration/test_pinned_model_effort.py` |
| T03-14 | biên | Bật "Ưu tiên bản context dài": (a) chưa chọn model, model mặc định có biến thể 1M trong metadata; (b) người dùng đã chọn model. | (a) Dùng biến thể 1M, composer lấy ngân sách từ `max_input_tokens` của biến thể; (b) không đổi model đã chọn. Mặc định công tắc tắt. | integration | `be/tests/integration/test_long_context_pref.py` |
| T03-15 | lỗi | `POST /v1/providers/test` với key sai và base URL không phân giải. | Lần lượt `PROVIDER_AUTH` (không retry) và `PROVIDER_UNREACHABLE`; message tiếng Việt, có `action` gợi ý sửa key/URL. | integration | `be/tests/integration/test_provider_test_endpoint.py` |
| T03-16 | biên | Đặt "Đồng thời riêng" = 1 cho `claude-pro`, provider = 4; 3 truyện cùng viết. | Tối đa 1 request đồng thời tới `claude-pro`, các bước dùng model khác vẫn chạy song song tới 4. | integration | `be/tests/integration/test_per_model_concurrency.py` |

## Kiểm tra dữ liệu sau test

- DB: `provider_models` đúng số dòng, nguồn `discovered`/`manual`, trường người dùng sửa được đánh dấu và giữ nguyên; model biến mất vẫn còn dòng; `role_models` có bản toàn app và bản ghi đè theo truyện.
- `job_steps`: mỗi bước lưu model + effort đã ghim và prompt version.
- Event: `provider.status` sau discovery/test.
- Log mock: số request `/v1/models` khớp kỳ vọng (0 khi tắt tự lấy và đã có danh sách thủ công).

## Tiêu chí pass

- 0 trường người dùng sửa bị ghi đè sau 3 lần discover liên tiếp.
- 0 request gửi mức effort ngoài danh sách hỗ trợ của model.
- 100% request trong một job dùng cùng model + effort đã ghim, kể cả khi cài đặt đổi giữa chừng.
- Discovery không làm readiness chậm thêm (so với khi tắt tự lấy, chênh < 100 ms).

## Ghi chú thủ công

- Live (chỉ chạy khi cấu hình key thật, đánh dấu `live`): discover với Anthropic thật và một gateway OpenAI-compatible; đối chiếu số model và metadata hiển thị.
- Kiểm UI kéo thả danh sách model bằng bàn phím (accessibility).

## Tên mới đề xuất

- `POST /v1/providers`, `PATCH /v1/providers/{id}`, `DELETE /v1/providers/{id}` (§7 chỉ có GET/test/discover).
- Cột `provider_models`: `position`, `source` (`discovered`/`manual`), `user_overridden_fields`, `last_seen_at`, `missing_on_server`, `max_concurrent_requests`; `providers.last_discovery_at`, `providers.last_discovery_error`.
- Tham số mock: `models_pages`, `require_key` (bổ sung cho `models_endpoint`).
