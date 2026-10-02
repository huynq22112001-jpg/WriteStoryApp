# T11 — Candidate và xung đột

Tính năng: F11. Nguồn: Plan FL06, §6.3, §4.2 (optimistic concurrency), §5 (`chapter_candidates`, `findings`), §7 (`/candidates`, `/jobs/{id}/accept`, `/findings`), §23.1.B, §23.2 #1–#2, UI §5.5. Cấp test chính: integration, e2e-fe.

## Mục đích

Chứng minh AI không bao giờ ghi thẳng vào chương: mọi đề xuất là candidate gắn base revision, nhận cả chương hoặc từng đoạn qua kiểm tra expected revision, xung đột trả 409 kèm dữ liệu để diff 3 bên, phần ngoài phạm vi sửa giữ nguyên, và review-only không sửa văn bản.

## Tiền điều kiện và dữ liệu

- Truyện `tests/fixtures/stories/do_thi_01/` (3 chương committed, xưng hô anh–em); ch.2 có 12 đoạn `p1`..`p12`.
- Mock provider: `{latency_ms: 30, tokens_per_sec: 300, scripted_outputs: {revise: "do_thi_01/revise_ch02_p3_p5.json", review: "do_thi_01/review_ch02.json", settle: "do_thi_01/delta_ch02_rev.json", validate: {consistent: true}}}`; file revise trả ops `replace p3`, `replace p5`, `insert_after p5`.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T11-01 | thành công | Chọn `p3`–`p5` ch.2, yêu cầu "viết lại cho căng hơn" → `POST /v1/jobs` `{type: revise, chapter_id, base_revision, scope: [p3, p4, p5]}`. | Candidate `kind=revise`, `status` `streaming` → `ready`, ghi base revision; event `candidate.ready`; editor ch.2 không đổi; pane CandidateStream hiển thị token, không ghi vào editor. | integration, e2e-fe | `be/tests/integration/test_revise_candidate.py`, `fe/tests/e2e/candidate_stream.spec.ts` |
| T11-02 | thành công | `POST /v1/candidates/{id}/accept` (cả candidate). | Trước accept có revision chụp working copy hiện tại (nguồn `pre_agent`); sau accept tạo revision mới nguồn `agent` (tên nguồn đề xuất ở T12); `p1`, `p2`, `p6`–`p12` giữ nguyên nội dung và `paragraph_id`; đoạn chèn có `paragraph_id` mới; candidate `accepted`. | integration | `be/tests/integration/test_accept_candidate_full.py` |
| T11-03 | thành công | Accept từng đoạn: `{paragraph_ids: [p3]}`. | Chỉ `p3` thay; `p5` và đoạn chèn không áp; candidate ghi các đoạn đã nhận; có thể nhận tiếp `p5` sau đó (vẫn kiểm expected revision mới). | integration, e2e-fe | `be/tests/integration/test_accept_candidate_partial.py` |
| T11-04 | lỗi | Tạo candidate từ revision R5; người dùng sửa ch.2 và tạo R6; accept candidate. | `409 REVISION_CONFLICT` với `detail` gồm base (R5), hiện tại (R6), candidate; không ghi gì; candidate vẫn `ready`; FE hiện diff 3 bên với lựa chọn áp lại trên R6. | integration, e2e-fe | `be/tests/integration/test_accept_conflict.py`, `fe/tests/e2e/conflict_three_way.spec.ts` |
| T11-05 | lỗi | Autosave working copy (chưa tạo revision) có sửa `p3` trong lúc candidate đang chạy; accept. | Phát hiện xung đột với working copy (base của working copy khác/working copy có thay đổi chồng phạm vi) → 409, không mất chữ người dùng gõ. | integration | `be/tests/integration/test_accept_vs_working_copy.py` |
| T11-06 | thành công | `POST /v1/candidates/{id}/reject`. | Candidate `rejected`; chương không đổi; candidate bị dọn sau 30 ngày (kiểm bằng đồng hồ giả + `POST /v1/storage/cleanup`). | integration | `be/tests/integration/test_reject_candidate.py` |
| T11-07 | biên | Tạo candidate thứ hai cho cùng phạm vi khi candidate thứ nhất còn `ready`. | Candidate thứ nhất `superseded`; `GET /v1/chapters/{id}/candidates` trả cả hai với trạng thái đúng. | integration | `be/tests/integration/test_candidate_superseded.py` |
| T11-08 | thành công | Revise và accept chương mới nhất ch.3. | Sau accept: settle lại ch.3 và cập nhật handoff ch.3 trước khi cho viết ch.4; continuity về `ok` sau settle. | integration | `be/tests/integration/test_accept_latest_resettle.py` |
| T11-09 | thành công | Revise và accept ch.2 (không phải mới nhất). | Continuity `stale_from(2)`; không tự viết lại ch.3. | integration | `be/tests/integration/test_accept_old_marks_stale.py` |
| T11-10 | thành công | Job review-only cho ch.2. | Findings có `paragraph_id` và trích dẫn khớp văn bản; 0 revision mới; văn bản ch.2 không đổi (hash). `POST /v1/findings/{id}/resolve` và `/dismiss` đổi `status` đúng. | integration | `be/tests/integration/test_review_only.py` |
| T11-11 | lỗi | Mock revise trả op `replace p99` (không tồn tại) hoặc op chạm `p9` ngoài scope. | Op không hợp lệ bị loại, candidate ghi cảnh báo trong tóm tắt kiểm tra; không đoạn ngoài scope nào bị đổi khi accept. | unit, integration | `be/tests/unit/test_apply_paragraph_ops.py` |
| T11-12 | lỗi | Accept candidate `partial` (job bị hủy giữa stream) không chỉ định đoạn. | Từ chối `VALIDATION` (bản nháp chưa hoàn chỉnh); cho phép xem diff; chỉ nhận được khi chọn rõ `paragraph_ids` hoàn chỉnh. | integration | `be/tests/integration/test_accept_partial_candidate.py` |
| T11-13 | hủy | Hủy job revise khi đang stream. | Candidate `partial`; không ghi vào chương; khóa truyện nhả. | integration | `be/tests/integration/test_revise_cancel.py` |
| T11-14 | thành công | FE Review/Diff: chế độ Song song/Inline, mức Từ/Câu; phím Ctrl+Enter nhận, Esc bỏ. | Diff theo đoạn neo bằng UniqueID rồi mức từ (jsdiff trong Web Worker, không chặn main thread > 50 ms); số âm tiết +/− hiển thị; Ctrl+Enter gửi accept một transaction với `expected_revision`. | e2e-fe | `fe/tests/e2e/review_diff.spec.ts` |
| T11-15 | biên | `POST /v1/jobs/{id}/accept` và `POST /v1/candidates/{id}/accept` cho cùng candidate. | Hai đường cho cùng kết quả hoặc một đường bị bỏ (cần chốt); không được commit hai lần (lần hai trả trạng thái đã `accepted`). | integration | `be/tests/integration/test_accept_endpoints_equivalent.py` |

## Kiểm tra dữ liệu sau test

- DB: `chapter_candidates` có `kind`, base revision, job, `status` đúng chuỗi chuyển trạng thái; `chapter_revisions` chỉ tăng khi accept (và revision chụp trước accept); `findings` có `paragraph_id`.
- So hash từng đoạn ngoài phạm vi trước/sau accept: bằng nhau.
- Event: `candidate.ready`, `finding.added`, `work.continuity` (T11-08, T11-09).

## Tiêu chí pass

- 0 lần AI ghi vào chương mà không qua accept.
- 0 lần accept ghi đè revision/working copy mới hơn base (mọi trường hợp lệch trả 409).
- 100% đoạn ngoài phạm vi giữ nguyên nội dung và `paragraph_id`.
- Review-only: 0 revision mới.

## Ghi chú thủ công

- Kiểm cảm nhận diff tiếng Việt: `Intl.Segmenter('vi', {granularity: 'word'})` trên WebView2 và WKWebView có thể chỉ tách âm tiết; xác nhận diff vẫn đọc được.

## Tên mới đề xuất

- Body `POST /v1/jobs` cho revise: `{type: revise, chapter_id, base_revision, scope: [paragraph_id], instruction}`.
- Trường `chapter_candidates.accepted_paragraph_ids` (ghi các đoạn đã nhận từng phần).
