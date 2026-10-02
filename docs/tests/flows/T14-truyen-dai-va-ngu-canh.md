# T14 — Truyện dài và ngữ cảnh

Tính năng: F09, F10. Nguồn: Plan §23.3 #1, #4–#7, §6.4, §5 (`summaries`, FTS), §4.4 (corpus lớn), §9 Giai đoạn 4, §21 (LNG/MEM), Review §2.1, §4.1 (ConStory-Bench). Cấp test chính: integration, contract.

## Mục đích

Chứng minh truyện 200+ chương vẫn viết được với kích thước context ổn định: tóm tắt phân tầng (chương → arc → synopsis) được tạo đúng nhịp, composer giữ phần bảo vệ và nén đúng lớp, dữ kiện/hook từ rất sớm vẫn được truy xuất khi cần, nhịp truyện không kết thúc sớm, và hiệu năng thư viện/chương không suy giảm theo độ dài.

## Tiền điều kiện và dữ liệu

- Truyện tổng hợp `tests/fixtures/stories/synthetic_long_220/` sinh bằng script `tests/fixtures/stories/generate_synthetic_long.py` (seed cố định): 220 chương committed, mỗi chương ~2.800 âm tiết tiếng Việt, `story_states` 0–220, `chapter_handoffs` 1–220, `summaries` cấp chương 1–220, 11 arc (20 chương/arc) có tóm tắt arc, 1 synopsis; 60 nhân vật, 400 facts, 80 hooks (trong đó hook #H7 mở ở ch.7, `due_by_chapter=221`; fact #F12 ở ch.12 "Lâm Phong mất kiếm Thanh Phong").
- Corpus hiệu năng: 50 tác phẩm, tổng 10.000 chương (sinh bằng cùng script, nội dung ngắn hơn).
- Model mock khai báo `max_input_tokens=200000`, `max_tokens=32000`; biến thể nhỏ `max_input_tokens=32000`.
- Mock provider: `{latency_ms: 20, tokens_per_sec: 500, scripted_outputs: {plan: "synthetic_long_220/plan_ch221.json", write: "synthetic_long_220/ch221.txt", settle: "synthetic_long_220/delta_ch221.json", validate: {consistent: true}, seam: {pass: true}, review: {findings: []}, summary: "synthetic_long_220/summary_ch221.txt", arc_summary: "synthetic_long_220/arc12.txt"}}`.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T14-01 | thành công | Compose context cho ch.21, ch.101, ch.221 (cùng mức cấu hình). | Mỗi lần gồm: synopsis + tóm tắt arc hiện tại + K tóm tắt chương gần nhất + kết quả tìm kiếm + handoff + `tail_text` + plan; số token context của ba lần chênh nhau ≤ 10% và luôn ≤ ngân sách (`max_input_tokens` − `max_tokens` − biên). | contract | `ai/tests/contract/test_context_size_stable.py` |
| T14-02 | thành công | Viết ch.221 (FL04 đầy đủ). | Commit thành công; thời gian compose < 1 s; prompt Writer không chứa toàn văn chương nào ngoài `tail_text` ch.220. | integration | `be/tests/integration/test_write_chapter_221.py` |
| T14-03 | thành công | Plan ch.221 có hook #H7 đến hạn. | Trace ch.221 có kết quả FTS trỏ ch.7 (đoạn mở hook) và fact liên quan; hook #H7 nằm trong mục bắt buộc của plan. | integration | `be/tests/integration/test_long_range_retrieval.py` |
| T14-04 | lỗi | Mock `write` ch.221 cho Lâm Phong dùng kiếm Thanh Phong (mâu thuẫn fact #F12 từ ch.12). | Validator/review phát hiện mâu thuẫn fact từ chương rất sớm (fact nằm trong `StoryState`, không chỉ trong tóm tắt) → finding `fact`/`blocker` có trích dẫn cả ch.12 → sửa cục bộ. | integration | `be/tests/integration/test_long_range_fact_conflict.py` |
| T14-05 | thành công | Viết ch.221–240 (auto, 20 chương) để đóng arc 12. | Sau mỗi chương có tóm tắt chương; khi đóng arc (hoặc tối đa mỗi 10–20 chương) tạo tóm tắt arc 12; synopsis cập nhật sau arc; bảng `summaries` phân biệt cấp chương/arc/synopsis. | integration | `be/tests/integration/test_hierarchical_summaries.py` |
| T14-06 | biên | Dùng model `max_input_tokens=32000`. | Composer nén/bỏ lớp compressible (tóm tắt chương cũ, FTS) trước; synopsis, handoff, `tail_text`, plan giữ nguyên; trace ghi phần bị nén. | contract | `ai/tests/contract/test_composer_small_window.py` |
| T14-07 | thành công | Ước lượng token trước khi gửi: (a) provider Anthropic có endpoint count tokens; (b) OpenAI-compatible dùng tỷ lệ token/âm tiết đo được trong `provider_models`. | (a) Dùng số đếm chính xác khi cấu hình yêu cầu. (b) Ước lượng = âm tiết × tỷ lệ × 1,15; nếu vượt ngân sách thì nén lớp compressible, không cắt phần bảo vệ; sai số ước lượng so usage thực được ghi để hiệu chỉnh tỷ lệ. | contract | `ai/tests/contract/test_token_estimation.py` |
| T14-08 | biên | Mục tiêu 240 chương, còn 25 sự kiện chưa `done` sau ch.220; mock planner cố kết thúc truyện ở ch.225. | Planner nhận ngân sách chương (25 sự kiện / 20 chương); cảnh báo dồn nhịp; kết thúc trước ch.240 bị chặn nếu tác giả chưa cho phép. | contract | `ai/tests/contract/test_pacing_long.py` |
| T14-09 | biên | 3 sự kiện chuyển `moved` trong ch.221–223. | Bước xét lại dàn ý chạy ngay (điều kiện ≥ 2 sự kiện `moved`) và mỗi 10 chương; đề xuất sửa `story_events` áp theo chế độ (T07-13). | integration | `be/tests/integration/test_outline_review_long.py` |
| T14-10 | thành công | So prefix prompt bước `write` giữa ch.221 và ch.222. | Lớp 1–2 giống từng byte, gồm 1–2 đoạn mẫu giọng văn cố định; đổi model Viết giữa truyện tạo cảnh báo trên UI. | contract | `ai/tests/contract/test_voice_sample_fixed.py` |
| T14-11 | hiệu năng | Đo kích thước `story_states` ch.1, ch.110, ch.220 và tổng dung lượng bảng. | Ghi số đo; nếu snapshot đầy đủ mỗi chương làm DB tăng > ngưỡng cấu hình (ví dụ 50 MB cho 220 chương) thì báo để cân nhắc delta + snapshot định kỳ (Plan §23.1.A). | integration | `be/tests/integration/test_state_snapshot_size.py` |
| T14-12 | hiệu năng | Corpus 50 truyện/10.000 chương: mở Thư viện, mở truyện 220 chương, cuộn cây chương, mở ch.180. | Thư viện chỉ tải metadata phân trang (không tải bản thảo); cây chương ảo hóa (DOM < 200 node chương); mở chương p95 < 300 ms; RAM FE không tăng tuyến tính theo số chương. | e2e-fe, integration | `fe/tests/e2e/large_corpus.spec.ts`, `be/tests/integration/test_large_corpus_api.py` |
| T14-13 | thành công | Tìm "thanh phong" trên truyện 220 chương. | Kết quả có nguồn chương/đoạn, ch.12 xếp đầu theo `bm25()`; truy vấn p95 < 200 ms (đề xuất). | integration | `be/tests/integration/test_search_long.py` |
| T14-14 | thành công | Kiểm hook quá hạn trên toàn truyện 220 chương (fixture có 9 hook quá `due_by_chapter`). | 9/9 hook quá hạn có cảnh báo trong Story Bible và finding mở. | integration | `be/tests/integration/test_overdue_hooks_long.py` |

## Kiểm tra dữ liệu sau test

- DB: `summaries` đủ cấp chương cho mọi chương committed, cấp arc cho mọi arc đã đóng, synopsis mới nhất; `story_states` ch.221+ có đủ facts từ chương sớm còn hiệu lực; `chapter_handoffs` chỉ chứa `tail_text` cắt theo đoạn.
- Trace: mỗi chương ghi số token từng lớp, phần bị nén, kết quả FTS kèm chương nguồn.
- Event: `chapter.committed` cho ch.221–240; không có `job.state` `failed` do vượt ngân sách context.

## Tiêu chí pass

- Kích thước context ch.21/ch.101/ch.221 chênh ≤ 10% và không bao giờ vượt ngân sách model.
- 0 lần cắt phần bảo vệ (plan, handoff, `tail_text`) trong mọi lần compose.
- 100% hook quá hạn được báo (9/9).
- Mâu thuẫn fact từ ch.12 được phát hiện ở ch.221 (T14-04).
- Ch.221–240: 0 chương `state_applied=false`, seam pass ≥ 95% sau ≤ 2 vòng sửa.
- Mở chương p95 < 300 ms trên corpus 10.000 chương (tiêu chí đề xuất §4.4).

## Ghi chú thủ công

- Live (`live`, quy mô nhỏ): tiếp 5 chương của truyện 220 chương bằng model thật; tác giả kiểm nhân vật phụ xuất hiện sớm có được gọi đúng tên/xưng hô và trạng thái hay không.

## Tên mới đề xuất

- Cột `summaries.level` = `chapter` / `arc` / `synopsis`; `summaries.arc_no`.
- Cột `provider_models.tokens_per_syllable` (tỷ lệ token/âm tiết đo được, §23.3 #4).
- Bước mock `arc_summary`, `outline_review`.
