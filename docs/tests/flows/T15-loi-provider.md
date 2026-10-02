# T15 — Lỗi provider

Tính năng: F04, F10, F12. Nguồn: Plan §23.3 #2–#3, #10; §23.2 #7, #8, #13; §23.1.D; §4.2 (retry, `Retry-After`); §6.6 (timeout, cancel, usage); §7.1 (structured outputs); §21 (empty/truncated output). Cấp test chính: contract, integration.

## Mục đích

Chứng minh mọi lỗi từ provider được phân loại đúng và xử lý có giới hạn: refusal không retry lặp, cắt `max_tokens` được viết tiếp tối đa 2 lần, JSON hỏng được yêu cầu sửa đúng 1 lần, mất mạng và vault khóa đưa job về `waiting_slot` (không fail) rồi tự chạy tiếp, lỗi xác thực không retry; không lỗi nào dẫn tới commit chương thiếu state hợp lệ.

## Tiền điều kiện và dữ liệu

- Truyện `tests/fixtures/stories/tien_hiep_01/` (3 chương committed), viết ch.4; một truyện thứ hai `do_thi_01` chạy song song để kiểm cô lập.
- Timeout cấu hình test: connect 2 s, first-token 5 s, stream-idle 5 s, overall 120 s; backoff mất mạng: bắt đầu 1 s, nhân đôi, trần 300 s (rút ngắn bằng đồng hồ giả `WS_TEST_CLOCK`).
- Mock provider cơ sở như T05; biến thể theo từng kịch bản (ghi trong cột Bước). Model `claude-pro` có `structured_outputs=true`; model `oa-mini` (OpenAI-compatible) không có.
- Mọi lỗi API kiểm theo hợp đồng `{code, message, detail, retryable, action}`, `message` tiếng Việt.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T15-01 | lỗi | `refusal_on: ["write"]` (stop_reason refusal ở bước viết). | Mock nhận đúng 1 request `write` (không retry lặp); job `waiting_user` mã `PROVIDER_REFUSAL`, `action` gợi ý chỉnh chỉ dẫn hoặc đổi model; 0 commit; continuity không đổi (không `blocked_needs_resync` vì không có lỗi state); truyện `do_thi_01` vẫn chạy. | integration | `be/tests/integration/test_refusal.py` |
| T15-02 | lỗi | `refusal_on: ["review"]`. | Như T15-01 tại bước `review`; candidate đã viết được giữ `ready`, không mất bản nháp. | integration | như trên |
| T15-03 | phục hồi | `truncate_on: ["write"]` 1 lần. | Gửi 1 request viết tiếp từ điểm dừng; văn bản ghép không lặp đoạn nối (không câu nào xuất hiện hai lần tại chỗ nối); trace ghi 1 lần viết tiếp; pipeline tiếp tục bình thường. | contract, integration | `ai/tests/contract/test_max_tokens_continuation.py` |
| T15-04 | lỗi | `truncate_on: ["write"]` 3 lần liên tiếp. | Tối đa 2 lần viết tiếp (tổng 3 request `write`/`continue`); sau đó mã `OUTPUT_TRUNCATED`, job `waiting_user`, candidate `partial` giữ văn bản đã có; 0 commit. | integration | `be/tests/integration/test_truncation_limit.py` |
| T15-05 | phục hồi | Model `oa-mini`, `bad_json_on: ["settle"]` chỉ lần 1. | JSON mode + parse thất bại → đúng 1 request yêu cầu sửa kèm lỗi parse → Pydantic validate pass → tiếp tục; trace ghi 1 lần sửa JSON. | contract | `ai/tests/contract/test_bad_json_repair_once.py` |
| T15-06 | lỗi | Model `oa-mini`, `bad_json_on: ["settle"]` cả lần 1 và lần sửa. | Bước fail `STRUCTURED_OUTPUT_INVALID` sau đúng 2 request (không request thứ 3); job `failed` `retryable=true`; checkpoint các bước trước giữ nguyên; resume chạy lại từ `settle`. | contract, integration | `be/tests/integration/test_structured_output_invalid.py` |
| T15-07 | thành công | Model `claude-pro` (`structured_outputs=true`) cho `settle`, `validate`, `seam`, `review`. | Request dùng structured outputs/tool-use có JSON schema (không JSON mode thuần); output qua Pydantic; nếu JSON đúng cú pháp nhưng sai schema Pydantic → đi đường sửa 1 lần như T15-05. | contract | `ai/tests/contract/test_structured_outputs_native.py` |
| T15-08 | lỗi | `truncate_on: ["settle"]` (JSON bị cắt). | Xử lý như JSON hỏng: 1 lần sửa/viết tiếp; vẫn hỏng → `STRUCTURED_OUTPUT_INVALID`; không áp một phần delta. | contract | `ai/tests/contract/test_truncated_json.py` |
| T15-09 | lỗi | Mock ngừng nhận kết nối (connection refused) trong 10 phút giả; sau đó bật lại. | Job không `failed`: `waiting_slot` lý do `PROVIDER_UNREACHABLE`; khoảng thử lại tăng dần, không vượt 300 s; event `provider.status`; Phòng viết hiện đếm ngược tới lần thử kế tiếp. Khi mock bật lại: cùng `job_id` chạy tiếp từ checkpoint, không tạo job mới. | integration, e2e-fe | `be/tests/integration/test_provider_unreachable.py`, `fe/tests/e2e/writing_room_countdown.spec.ts` |
| T15-10 | phục hồi | `disconnect_after_tokens: 500` ở bước `write` (1 lần). | Bản nháp đến token 500 lưu checkpoint candidate `partial`; bước `write` chạy lại (lỗi tạm thời, tính vào giới hạn retry 3); candidate cuối không chứa phần lặp; usage của lần đứt được ghi nếu provider đã trả. | integration | `be/tests/integration/test_stream_disconnect.py` |
| T15-11 | lỗi | Batch 5 chương đang chạy; `POST /v1/vault/lock` khi ch.5 đang ở bước `plan`. | Request tiếp theo cần key không được gửi; job `waiting_slot` lý do `VAULT_LOCKED`; event `vault.status`, hộp thoại mở vault trên FE. Mở vault → cùng `job_id` chạy tiếp; batch hoàn tất ch.5–8. | integration | `be/tests/integration/test_vault_locked_mid_batch.py` |
| T15-12 | lỗi | `fail_sequence: [401]`; lặp với `[403]` và model không tồn tại (`404 model_not_found`). | Đúng 1 request mỗi trường hợp (không retry); mã `PROVIDER_AUTH` (401/403) kèm `action` sửa key; model không tồn tại có mã lỗi cụ thể kèm `action` chọn model khác; job `failed`; resume sau khi sửa cấu hình chạy được. | integration | `be/tests/integration/test_auth_errors_no_retry.py` |
| T15-13 | lỗi | `fail_sequence: [429(retry_after=2), ok]`. | Chờ ≥ 2 s trước request kế tiếp; `waiting_slot` lý do `PROVIDER_RATE_LIMIT` trong lúc chờ; không tính là lỗi job (chi tiết đa truyện ở T08-06). | integration | `be/tests/integration/test_retry_after_single.py` |
| T15-14 | lỗi | `fail_sequence: [500, 502, 503, 500]`. | Tối đa 3 retry, backoff tăng dần + jitter; hết retry → bước fail, job `failed` `retryable=true`, checkpoint giữ; 0 commit. | integration | `be/tests/integration/test_5xx_retry_limit.py` |
| T15-15 | lỗi | Mock trả output rỗng (stop bình thường, 0 token) ở `write`. | Không tạo candidate rỗng; bước được xem là lỗi, không đi tiếp `check`/`settle`; mã lỗi rõ ràng trong job. | contract | `ai/tests/contract/test_empty_output.py` |
| T15-16 | lỗi | `latency_ms: 8000` trước token đầu (vượt first-token 5 s); và stream dừng 6 s giữa chừng (vượt stream-idle 5 s). | Mỗi trường hợp hủy request đúng loại timeout, retry trong giới hạn; overall deadline 120 s không bị vượt. | integration | `be/tests/integration/test_provider_timeouts.py` |
| T15-17 | biên | Lỗi kéo dài (T15-09) với model dự phòng chưa cấu hình. | Không tự đổi sang model khác (model dự phòng là tính năng "Sau", mặc định tắt); trace không có lần gọi model khác. | integration | `be/tests/integration/test_no_implicit_fallback.py` |
| T15-18 | thành công | Snapshot hợp đồng lỗi: gọi các endpoint gây từng mã §23.1.D. | Mọi body lỗi có đủ `code`, `message` (tiếng Việt), `detail`, `retryable`, `action`; `REVISION_CONFLICT` là HTTP 409; snapshot khớp `contracts/examples/errors/*.json`. | contract | `be/tests/contract/test_error_contract.py` |

## Kiểm tra dữ liệu sau test

- DB: không có `chapter_revisions`/`story_states` mới cho chương gặp lỗi chưa xử lý; `jobs.error_code` khớp mã kỳ vọng; `job_steps` ghi số lần retry, số lần viết tiếp, số lần sửa JSON.
- Usage: chỉ ghi số provider trả; lần lỗi không trả usage để trống.
- Event: `provider.status` khi lỗi provider/khôi phục; `vault.status`; `job.state` với lý do chờ.
- Log mock: số request đúng giới hạn từng kịch bản.

## Tiêu chí pass

- Refusal: đúng 1 request; JSON hỏng: tối đa 2 request; cắt output: tối đa 3 request; 401/403/model không tồn tại: đúng 1 request; 5xx: tối đa 4 request (1 + 3 retry).
- Mất mạng/vault khóa: 0 job `failed`, 100% tiếp tục cùng `job_id` sau khi khôi phục.
- 0 commit sau bất kỳ lỗi nào chưa được giải quyết; 0 delta áp một phần.
- Truyện song song không bị ảnh hưởng bởi lỗi provider của truyện khác dùng provider khác.

## Ghi chú thủ công

- Live (`live`): rút cáp mạng thật trong lúc viết; kiểm đếm ngược trên Phòng viết và tự chạy tiếp khi có mạng.
- Live: thử chỉ dẫn có cảnh bạo lực điển hình kiếm hiệp với model thật để quan sát refusal thực tế và chất lượng gợi ý trên UI.

## Tên mới đề xuất

- Mã lỗi: `PROVIDER_MODEL_NOT_FOUND` (model không tồn tại), `OUTPUT_EMPTY` (output rỗng), `PROVIDER_SERVER_ERROR` (5xx hết retry) — §23.1.D chưa có.
- Cột `jobs.error_code`; bước mock `continue` (request viết tiếp sau `max_tokens`).
