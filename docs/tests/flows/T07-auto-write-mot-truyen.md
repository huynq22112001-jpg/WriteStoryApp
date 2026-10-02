# T07 — Auto-write một truyện

Tính năng: F12. Nguồn: Plan FL05, §4.2 (chế độ `auto`/`review_each`/`review_every_k`), §6.2, §7 (`/autowrite`, `/autowrite/estimate`), §23.2 #6, §23.3 #5–6, §9 Giai đoạn 4, UI §5.3. Cấp test chính: integration, e2e-fe.

## Mục đích

Chứng minh viết N chương tự động trong một truyện luôn tuần tự (chương N+1 chỉ được tạo sau khi chương N commit cùng state), ba chế độ duyệt dừng đúng chỗ, dừng giữa batch không mất chương đã hoàn tất, resume chỉ chạy phần còn thiếu, và một truyện 20 chương đạt các chỉ số liền mạch.

## Tiền điều kiện và dữ liệu

- Truyện `tests/fixtures/stories/tien_hiep_01/` (3 chương committed) và bản sao `tien_hiep_01_fresh` (0 chương, chỉ nền truyện) cho chạy 20 chương.
- Mock provider: `{latency_ms: 40, tokens_per_sec: 200, scripted_outputs: {plan: "tien_hiep_01/plans/ch{n}.json", write: "tien_hiep_01/chapters/ch{n}.txt", settle: "tien_hiep_01/deltas/ch{n}.json", validate: {consistent: true}, seam: {pass: true}, review: {findings: []}, summary: "tien_hiep_01/summaries/ch{n}.txt"}}` (bộ 20 chương kịch bản sẵn, tiếng Việt).
- Biến thể: `scripted_outputs.seam` cho ch.6 = `[fail, fail, fail]` (T07-05).
- Ngân sách test: truyện $0,50/ngày, toàn app $10/ngày; đồng hồ giả `WS_TEST_CLOCK` với timezone `Asia/Ho_Chi_Minh`.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T07-01 | thành công | `POST /v1/works/{id}/autowrite` `{count: 5, mode: auto, priority: 0}`. | Viết ch.4 → ch.8 tuần tự; với mọi n, job ch.n+1 được tạo SAU event `chapter.committed` của ch.n (so `created_at` với `ts`); tại mọi thời điểm ≤ 1 job ghi `running`; 5 event `chapter.committed`; batch kết thúc, `queue.changed` báo truyện không còn job. | integration | `be/tests/integration/test_autowrite_auto.py` |
| T07-02 | thành công | `{count: 3, mode: review_each}`; accept từng chương qua `POST /v1/candidates/{id}/accept`. | Sau mỗi chương job `waiting_user`, candidate `ready`; chưa accept thì không có job chương kế tiếp và không có request nào tới mock cho chương đó. Accept → commit → chương kế tiếp chạy. | integration, e2e-fe | `be/tests/integration/test_autowrite_review_each.py`, `fe/tests/e2e/autowrite_review_each.spec.ts` |
| T07-03 | thành công | `{count: 6, mode: review_every_k}`, K = 2. | Ch.4 tự commit; ch.5 dừng `waiting_user`; accept → ch.6 tự commit; ch.7 dừng; … Tổng 3 lần dừng chờ duyệt (ch.5, ch.7, ch.9). | integration | `be/tests/integration/test_autowrite_review_every_k.py` |
| T07-04 | thành công | `{target_chapter: 10, mode: auto}` trên truyện 3 chương. | Range tính ra ch.4–10 (7 chương); kết quả giống `count: 7`. | integration | `be/tests/integration/test_autowrite_target.py` |
| T07-05 | lỗi | `{count: 5, mode: auto}`, seam ch.6 fail 3 lần. | Ch.4, ch.5 committed; ch.6 `waiting_user` + `blocked_needs_resync`; batch dừng, ch.7–8 không được tạo; Phòng viết hiện lý do. Sau khi xử lý (T06-14) và `POST /v1/works/{id}/autowrite/resume`: chỉ chạy ch.7–8 (ch.6 đã commit qua xử lý chặn), không viết lại ch.4–5. | integration | `be/tests/integration/test_autowrite_stops_on_block.py` |
| T07-06 | lỗi | `{count: 3}` với `start_chapter: 6` khi chương kế tiếp là 4; và `POST autowrite` lần hai khi batch đang chạy với range chồng lấn. | Cả hai trả `CHAPTER_RANGE_CONFLICT` kèm chương kế tiếp đúng và batch đang chạy trong `detail`. | integration | `be/tests/integration/test_autowrite_range_conflict.py` |
| T07-07 | hủy | Batch 5 chương đang ở ch.5 bước `write`; `POST /v1/works/{id}/autowrite/cancel`. | Job ch.5 `cancelled`, request HTTP đóng, candidate `partial` không commit; ch.4 giữ committed; không có job ch.6; khóa truyện nhả. | integration | `be/tests/integration/test_autowrite_cancel.py` |
| T07-08 | hủy | Batch 5 chương đang ở ch.5; `POST /autowrite/pause`; chờ; `POST /autowrite/resume`. | Pause: ch.5 chạy nốt tới commit (hoặc `waiting_user`), không tạo job ch.6; Phòng viết hiện "tạm dừng". Resume: tiếp ch.6–8 với cấu hình đã ghim lúc bắt đầu batch. | integration | `be/tests/integration/test_autowrite_pause_resume.py` |
| T07-09 | thành công | `POST /v1/works/{id}/autowrite/estimate` `{count: 10}` (a) truyện có 3 chương với usage thực; (b) truyện mới chưa có usage. | Trả khoảng token min–max, chi phí min–max theo giá trong `provider_models`, thời gian ước tính; (a) dựa usage trung bình các chương trước; (b) dựa độ dài mục tiêu. Hộp thoại auto-write hiển thị ước tính. | integration, e2e-fe | `be/tests/integration/test_autowrite_estimate.py` |
| T07-10 | lỗi | Ước tính vượt ngân sách còn lại của truyện; gửi `autowrite` không xác nhận rồi có xác nhận. | Không xác nhận: `BUDGET_EXCEEDED` kèm ước tính. Có xác nhận: batch chạy; khi usage thực chạm ngân sách, job kế tiếp `waiting_slot` lý do `BUDGET_EXCEEDED`; sang ngày mới (đồng hồ giả qua 00:00 theo timezone cấu hình) tự chạy tiếp. | integration | `be/tests/integration/test_autowrite_budget.py` |
| T07-11 | biên | Batch đang chạy ch.6; sửa thông tin nhân vật trong Story Bible. | Ch.6 dùng revision Story Bible cũ (lớp 2 không đổi); ch.7 dùng revision mới; trace ghi revision Story Bible đã dùng. | integration | `be/tests/integration/test_autowrite_bible_revision.py` |
| T07-12 | biên | Truyện mục tiêu 20 chương, 12 sự kiện; mock planner cố ý dồn 6 sự kiện vào ch.4; sau đó mock cố kết thúc truyện ở ch.12. | Planner nhận "ngân sách chương" (sự kiện còn lại / chương còn lại); có cảnh báo dồn nhịp; kết thúc sớm trước ch.20 bị chặn khi tác giả chưa cho phép (finding/`waiting_user`). | contract, integration | `ai/tests/contract/test_pacing_budget.py` |
| T07-13 | biên | Sau ch.10 (K = 10) hoặc khi ≥ 2 sự kiện `moved`: bước xét lại dàn ý. | `review_*`: đề xuất sửa `story_events` chờ tác giả duyệt, chưa áp. `auto`: áp đề xuất không đụng sự kiện tác giả đã khóa; đề xuất đụng sự kiện khóa bị bỏ qua và ghi lại. | integration | `be/tests/integration/test_outline_review.py` |
| T07-14 | thành công | `tien_hiep_01_fresh`, `{count: 20, mode: auto}`; sau đó chạy bộ kiểm chỉ số liền mạch. | Đạt mọi tiêu chí ở mục "Tiêu chí pass" (chỉ số §9 Giai đoạn 4 trên 1 truyện; 3 truyện song song ở T08). | integration | `tests/integration/test_continuity_metrics_single.py` |
| T07-15 | thành công | Luồng FE: hộp thoại auto-write (số chương, chế độ, ưu tiên, ước tính) → chạy → theo dõi trong Phòng viết. | Phòng viết hiện pipeline đúng bước §6.2, bước hiện tại in đậm, `↻ vòng k/K` khi sửa, chi phí cập nhật theo `usage.updated`. | e2e-fe | `fe/tests/e2e/autowrite_dialog.spec.ts` |

## Kiểm tra dữ liệu sau test

- DB: chương committed liên tục 1..N, không lỗ số chương; mỗi chương có `story_states`, `chapter_handoffs`, `summaries` cấp chương; `work_queues` phản ánh chế độ, ưu tiên, range; `usage_counters` theo ngày/timezone.
- Job: không có hai job ghi của cùng truyện có khoảng `running` chồng nhau (kiểm từ `job_events`).
- Event: mỗi chương có `chapter.committed`; batch dừng có `job.state` `waiting_user`/`cancelled` và `queue.changed`.

## Tiêu chí pass

Trên truyện 20 chương (T07-14), tính bằng script `tests/integration/continuity_metrics.py`:

- 0 chương committed có `state_applied=false`.
- Seam check pass ≥ 95% số chương (pass ở lần đầu hoặc sau ≤ 2 vòng sửa).
- 0 tên nhân vật ngoài canon chưa khai báo trong văn bản committed.
- 0 lỗi xưng hô sai `address_rules` mà không có thao tác `address.change` trong state; 0 truyện trộn hai kiểu bỏ dấu.
- 100% hook quá `due_by_chapter` có finding/cảnh báo.
- Tỷ lệ n-gram trùng giữa mọi cặp chương liền kề dưới ngưỡng cấu hình.
- 0 job chương N+1 được tạo trước khi chương N commit; 0 chương viết dựa trên candidate chưa commit.

## Ghi chú thủ công

- Chạy T07-14 với model thật (`live`) trên một truyện mẫu; tác giả đọc và chấm từng chương + cả truyện theo rubric kiểu EQ-Bench Longform (tiếng Việt); kết quả lưu để so sánh khi đổi prompt/model.

## Tên mới đề xuất

- Trường `start_chapter` trong body `POST /v1/works/{id}/autowrite` (để phát hiện range không bắt đầu ở chương kế tiếp) và `confirm_over_budget: true`.
- Cờ `story_events.locked` (sự kiện tác giả đã khóa, §23.3 #6).
- Ngữ nghĩa `autowrite/pause`: chạy nốt chương hiện tại rồi dừng (Plan chưa nói rõ; khác "Tạm dừng để sửa" ở T10).
- Biến môi trường test `WS_TEST_CLOCK` (đồng hồ giả cho ngân sách theo ngày).
