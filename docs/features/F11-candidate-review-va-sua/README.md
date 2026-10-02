# F11 — Candidate, review và sửa

Giai đoạn: R2. Trạng thái: planned.

## Mục tiêu

Tác giả xem bản nháp AI (candidate) cạnh bản hiện tại, nhận cả chương hoặc từng đoạn mà không bao giờ ghi đè chỉnh sửa mới hơn của mình; xử lý findings có bằng chứng; yêu cầu AI sửa có phạm vi (vùng chọn / các đoạn / cả chương). Khi một chương đã commit bị đổi, truyện được đánh dấu `stale_from(K)` và đồng bộ lại tuần tự K..N từ snapshot K-1, không tự viết lại văn bản các chương sau.

## Phạm vi

- Trong phạm vi:
  - Vòng đời `chapter_candidates`: `streaming → partial | ready → accepted | rejected | superseded`; loại `draft | repair | revise` (Plan §5, §23.2 #1).
  - Nhận candidate cả chương hoặc theo `paragraph_id` với `expected_revision_id`; xung đột → `409 REVISION_CONFLICT` kèm dữ liệu diff 3 bên (Plan §4.2, §23.1.B, Arch §8 bước 7).
  - Bảng `findings` gộp (nguồn `check | validator | seam | review | user`), resolve/dismiss, kiểm chứng trích dẫn (Plan §5, §23.2 #14, FL06 bước 2).
  - Revise theo yêu cầu tác giả có phạm vi và mode `spot_fix | polish | rewrite | rework` (Plan §6.3, FL06, EDT02–EDT03).
  - Hệ quả liền mạch: sửa chương mới nhất → settle lại + handoff mới; sửa chương cũ → `stale_from(K)`; job `resync` K..N tuần tự (Plan §6.2 quy tắc cuối, §4.3, Review §4.4).
  - Chèn/xóa/đổi thứ tự chương theo Plan §23.2 #4; xóa chương mới nhất có trash + rollback snapshot (EDT09, FL07 bước 4).
  - Phân biệt rework (sửa văn bản, không rollback state) với rollback/regenerate (FL07, EDT13).
  - FE: màn Review/Diff (UI §5.5), lịch sử candidate, phím tắt nhận/bỏ, UI xung đột, banner chặn/stale và hộp thoại resync (UI §5.2).
- Ngoài phạm vi:
  - Pipeline viết/sửa tự động trong một chương (vòng repair K lần) – F10. F11 chỉ dùng chung hàm áp `ParagraphOps` và quy trình commit.
  - Working copy, autosave, revision, restore revision – F07 (F11 gọi lại use case của F07).
  - Scheduler, khóa truyện, hàng đợi – F12 (job `revise`/`resync` của F11 chạy qua scheduler F12).
  - Rollback/regenerate đầy đủ (EDT13) là R3: F11 chỉ chốt hợp đồng và chặn nhầm lẫn với rework; mode `anti_detect` (EDT02) là R3.
  - Đổi tên entity xuyên chương (EDT05, R3); cascade tự sửa nhiều chương sau (NEW10).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F01 | Envelope event (`candidate.ready`, `finding.added`, `work.continuity`) và hợp đồng lỗi §23.1.D |
| F02 | Writer queue, transaction ngắn, FTS rebuild cho chương đổi |
| F07 | `chapter_revisions`, `chapter_working_copy`, `paragraph_id` (Tiptap UniqueID), diff/restore |
| F09 | `StoryState`/`StateDelta`, snapshot theo chương, summaries – dùng cho resettle/resync |
| F10 | Workflow settle/validate/seam/review và use case `commit_chapter` một transaction |
| F12 | Scheduler + `work_locks` để chạy job `revise`/`resync` tuần tự trong truyện |

## Nguồn thiết kế

- Plan §4.2 (optimistic concurrency), §4.3 (`continuity_status`), §5 (`findings`, `chapter_candidates`), §6.2 (quy tắc `stale_from`), §6.3, §7 (API), §23.1.B, §23.2 #1–#4 #10 #14, §23.5 mục 3; FL06, FL07; §21 dòng "EDT, FL06–07".
- Arch §5 (`modules/chapters/service.py`), §6 (`contracts/paragraphs.py`, `workflows/longform/repair.py`), §8 bước 6–8.
- UI §5.2 (banner, tab Review), §5.5 (Review/Diff), §6, §8 (Ctrl+Enter / Esc).
- Review §4.3, §4.4.
- Mã Plan §15: EDT02, EDT03, EDT04, EDT08, EDT09, EDT10, EDT13 (R3), WRK04, WRK05, LNG11, NEW05.

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Bảng `chapter_candidates`, `findings`, cột liền mạch; API accept/reject/findings/resync/cấu trúc chương; merge 3 bên theo đoạn; job `revise`, `review`, `resync` |
| FE | [fe.md](./fe.md) | Màn Review/Diff (worker jsdiff), nhận từng đoạn, UI 409 ba bên, findings, form sửa có phạm vi, banner + hộp thoại resync, lịch sử |
| AI | [ai.md](./ai.md) | Workflow revise trả `ParagraphOps`, context có phạm vi, review-only trả findings có bằng chứng, resettle văn bản có sẵn |

## Tiêu chí hoàn thành

- [ ] Nhận candidate không bao giờ ghi đè revision/working copy mới hơn: mọi trường hợp lệch trả 409 kèm `conflicts[]` đủ `base/current/candidate` theo đoạn.
- [ ] Nhận từng đoạn: đoạn ngoài `paragraph_ids` giữ nguyên byte-by-byte (so sánh sau NFC) – kiểm bằng test.
- [ ] Revise phạm vi vùng chọn/đoạn: văn bản ngoài phạm vi không đổi; op ngoài phạm vi bị host loại và ghi trace.
- [ ] Sửa chương mới nhất → job resettle N..N, handoff(N) mới trước khi scheduler cho viết N+1.
- [ ] Sửa chương K < N → `continuity_status = stale_from`, `continuity_chapter_no = min(cũ, K)`; auto-write dừng sau chương đang chạy.
- [ ] Resync K..N tuần tự, commit từng chương, checkpoint được; lỗi ở chương k → `blocked_needs_resync` tại k, không mất kết quả k-1.
- [ ] Chèn/xóa/đổi thứ tự bị từ chối khi truyện đang chạy; khi dừng thì tạo `stale_from(K)` với K nhỏ nhất bị ảnh hưởng.
- [ ] Findings: trích dẫn được host xác minh; quote không khớp → `evidence_status = unavailable`; dismiss blocker bắt buộc ghi chú.
- [ ] Các test luồng liên quan pass: [T10](../../tests/flows/T10-sua-tay-va-resync.md), [T11](../../tests/flows/T11-candidate-va-xung-dot.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md).

## Rủi ro và câu hỏi mở

- Đoạn được thay bằng text AI mất định dạng inline (bold/italic) của đoạn cũ; MVP chấp nhận, FE hiển thị cảnh báo khi đoạn gốc có mark. Cần chốt có cho AI trả markdown tối thiểu không.
- Chương chèn giữa truyện (Plan §23.2 #4) cần nội dung trước khi resync. MVP: tác giả tự viết hoặc dùng revise `rework` trên chương rỗng; job "viết chương chèn" có seam hai đầu (K-1 và K+1) để mở sau.
- "Chấp nhận kèm ghi chú" (Plan §6.2) được hiểu là dismiss các finding chặn có ghi chú rồi commit với delta đã qua kiểm tra schema; nếu delta sai schema thì bắt buộc settle lại. Cần tác giả sản phẩm xác nhận cách hiểu này.
- Resync chương rất dài/nhiều chương tốn chi phí; dùng ước tính `dry_run` trước khi chạy (số liệu thật đo ở R2).
- Rollback/regenerate (EDT13) ở R3 nhưng FL07 nằm trong parity flow; MVP chỉ có xóa chương mới nhất + rollback snapshot.
