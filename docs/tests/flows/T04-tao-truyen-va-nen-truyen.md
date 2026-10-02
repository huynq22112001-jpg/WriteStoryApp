# T04 — Tạo truyện và nền truyện

Tính năng: F05, F06. Nguồn: Plan FL03, §6.1, §5 (`works`, `style_profile`, `address_rules`, `characters`, `story_events`, `hooks`, `story_states`), §23.1.A, §23.3 #2, UI §5.4, §5.7. Cấp test chính: integration, e2e-fe.

## Mục đích

Chứng minh wizard tạo được truyện tiếng Việt có nền truyện, nhân vật kèm bí danh, quy tắc xưng hô theo giai đoạn, dàn ý sự kiện có phụ thuộc và state seed chương 0; truyện chỉ sẵn sàng viết khi nền truyện hợp lệ, lỗi giữa chừng không làm mất phần đã nhập.

## Tiền điều kiện và dữ liệu

- Data-root tạm, vault mở, provider mock đã cấu hình (T03).
- Fixture brief: `tests/fixtures/stories/tien_hiep_01/brief.json` (tiên hiệp, xưng hô ta–ngươi, huynh–muội; 12 sự kiện; 4 hook có `due_by_chapter`).
- Mock provider: `{latency_ms: 30, tokens_per_sec: 300, scripted_outputs: {foundation: "tien_hiep_01/foundation.json", outline: "tien_hiep_01/events.json"}}`; biến thể `bad_json_on: ["foundation"]`, `fail_sequence: [500, 500, 500, 500]` cho T04-06, T04-07.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T04-01 | thành công | 1. Wizard: ngôn ngữ Tiếng Việt, thể loại tiên hiệp, style profile (Hán Việt nhiều, thoại gạch đầu dòng, kiểu bỏ dấu `hòa`). 2. Brief. 3. Sinh nền truyện (job `foundation`), sửa tên 1 nhân vật. 4. Nhập quy tắc xưng hô. 5. Dàn ý sự kiện. 6. Cấu hình viết (2.500–3.500 âm tiết, `review_every_k` K=5, ngân sách). 7. Tạo. | `works` có `language=vi`; `style_profile`, `characters` (kèm bí danh có/không dấu), `address_rules`, `story_events` (12 dòng `planned`, có `planned_chapter`, phụ thuộc), `hooks` (4 dòng có `due_by_chapter`, `priority`); `story_states` có snapshot `chapter_no=0`; truyện ở trạng thái sẵn sàng viết; `GET /v1/works/{id}/continuity` trả `ok`. | e2e-fe, integration | `fe/tests/e2e/create_work_wizard.spec.ts`, `be/tests/integration/test_create_work_foundation.py` |
| T04-02 | thành công | `GET /v1/works/{id}/state?chapter=0`. | Trả `StoryState` đúng schema §23.1.A: `chapter_no=0`, `characters[]` có `status=alive` và `location_id`, `hooks[]` có `due_by`, `events[]` trạng thái `planned`. | contract | `be/tests/contract/test_story_state_schema.py` |
| T04-03 | biên | Ô ngôn ngữ trong wizard. | Chỉ có một lựa chọn "Tiếng Việt"; `POST /v1/works` với `language=en` trả `VALIDATION`. | e2e-fe, integration | `be/tests/integration/test_work_language.py` |
| T04-04 | phục hồi | Đóng app ở bước 4 (xưng hô) của wizard; mở lại, vào "Tiếp tục tạo truyện". | Bước 1–3 giữ nguyên (gồm chỉnh sửa nền truyện); wizard mở đúng bước 4; truyện ở trạng thái nháp, không xuất hiện như truyện sẵn sàng viết. | e2e-fe | `fe/tests/e2e/wizard_resume.spec.ts` |
| T04-05 | lỗi | Tạo job write cho truyện còn ở trạng thái nháp (chưa nhận nền truyện). | Bị từ chối với `VALIDATION` (`action` dẫn về wizard); không tạo job, không gọi provider. | integration | `be/tests/integration/test_write_requires_foundation.py` |
| T04-06 | lỗi | Mock `bad_json_on: ["foundation"]` lần 1, lần 2 hợp lệ. Sau đó chạy lại với cả 2 lần hỏng. | Lần đầu: một request sửa JSON duy nhất rồi thành công. Lần hai: bước fail `STRUCTURED_OUTPUT_INVALID`, truyện vẫn nháp, brief và phần nền truyện đã có hiển thị kèm nút "Khôi phục/Sinh lại nền truyện". | contract, integration | `ai/tests/contract/test_foundation_structured_output.py` |
| T04-07 | lỗi | Mock `fail_sequence: [500, 500, 500, 500]` cho bước `foundation`. | Retry tối đa 3 lần có backoff, sau đó job `failed` với mã lỗi provider; brief giữ nguyên; resume tạo request mới không mất brief. | integration | `be/tests/integration/test_foundation_provider_error.py` |
| T04-08 | hủy | Hủy job `foundation` khi đang stream. | Job `cancelled`; request HTTP tới mock bị đóng; candidate nền truyện (nếu có) không được nhận; truyện vẫn nháp, brief còn. | integration | `be/tests/integration/test_foundation_cancel.py` |
| T04-09 | lỗi | Dàn ý: sự kiện A phụ thuộc B, B phụ thuộc A; hoặc phụ thuộc tới ID không tồn tại. | `VALIDATION` chỉ rõ chu trình/ID sai; không lưu thay đổi dở dang. | unit, integration | `be/tests/unit/test_story_events_dependencies.py` |
| T04-10 | thành công | Quy tắc xưng hô theo giai đoạn: Lâm Phong → Mộc Lan "ta/ngươi" từ ch.1, "huynh/muội" từ ch.15. `GET /v1/works/{id}/address-rules`. | Trả 2 quy tắc có khoảng chương; quy tắc hiệu lực ở ch.10 là "ta/ngươi", ở ch.20 là "huynh/muội". Tab Xưng hô trong hồ sơ nhân vật hiển thị đúng. | integration, e2e-fe | `be/tests/integration/test_address_rules_stages.py` |
| T04-11 | biên | Nhập tên nhân vật dạng NFD (dán từ Word) và bí danh không dấu "Lam Phong". | Lưu dạng NFC; bí danh không dấu được dùng cho kiểm tra tên ở T13; tìm "lam phong" thấy nhân vật. | unit | `ai/tests/unit/test_vi_normalizer_names.py` |
| T04-12 | biên | Khi truyện đang auto-write (T07), sửa mô tả nhân vật trong Story Bible. | Tạo revision mới cho dữ liệu Story Bible; UI ghi "áp từ chương kế tiếp"; request của chương đang chạy không đổi lớp 2 (so prefix prompt). | integration | `be/tests/integration/test_bible_edit_during_batch.py` |
| T04-13 | thành công | Tạo truyện mẫu từ onboarding (`tests/fixtures/stories/do_thi_01/`). | Truyện đô thị với xưng hô anh–em, có 3 chương đã duyệt, `story_states` cho chương 0–3, `chapter_handoffs` cho chương 3; continuity `ok`; có thể viết chương 4 ngay. | integration | `be/tests/integration/test_sample_work.py` |

## Kiểm tra dữ liệu sau test

- DB: truyện hoàn tất có đủ `works`, `style_profile`, `characters`, `address_rules`, `story_events`, `hooks`, `story_states(chapter_no=0)`; truyện lỗi/hủy vẫn ở trạng thái nháp, không có `story_states`.
- Văn bản trong DB đều là NFC (kiểm `unicodedata.is_normalized("NFC", ...)` cho mọi cột văn bản đã ghi).
- Event: `job.queued`, `job.state`, `job.step` cho job `foundation`; `candidate.ready` khi nền truyện sẵn sàng để duyệt.

## Tiêu chí pass

- 0 truyện chuyển sang sẵn sàng viết khi nền truyện chưa hợp lệ hoặc thiếu state seed chương 0.
- 0 dữ liệu wizard bị mất khi đóng app/hủy/lỗi provider.
- Lỗi JSON hỏng chỉ dẫn tới đúng 1 request sửa trước khi kết luận `STRUCTURED_OUTPUT_INVALID`.

## Ghi chú thủ công

- Đọc nền truyện và dàn ý do mock/model thật sinh ra (khi chạy `live`) để đánh giá tự nhiên của tiếng Việt; không tự động hóa được.

## Tên mới đề xuất

- `works.status` = `draft` / `ready` (FL03 nói "Work draft" và "readiness" nhưng §5 chưa có cột).
- Loại job `foundation` và `outline` trong `POST /v1/jobs` (§7 chỉ ghi "create foundation/write/review/revise").
- Cột `address_rules.from_chapter`, `address_rules.to_chapter` cho "theo giai đoạn truyện".
- Bước mock `foundation`, `outline`.
