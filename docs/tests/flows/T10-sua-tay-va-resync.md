# T10 — Sửa tay và resync

Tính năng: F11, F07. Nguồn: Plan FL07, §6.2 (quy tắc `stale_from`), §6.3, §23.2 #3–#4, §23.4 #3, #11, #12, §7 (`/resync`, `/chapters/reorder`, `/handoff`), UI §5.2. Cấp test chính: integration, e2e-fe.

## Mục đích

Chứng minh sửa tay không bao giờ làm state truyện lệch âm thầm: sửa chương nền khi đang auto-write được chặn ở FE và BE, sửa chương cũ tạo `stale_from(K)` và dừng batch đúng lúc, resync settle lại tuần tự K..N mà không viết lại văn bản các chương sau, và chèn/xóa/đổi thứ tự chương đều đi qua cùng cơ chế.

## Tiền điều kiện và dữ liệu

- Truyện `tests/fixtures/stories/tien_hiep_01_10ch/` (10 chương committed, `story_states` 0–10, handoff 1–10; ch.3 chứa fact #12 "Lâm Phong mất kiếm Thanh Phong" được dùng lại ở ch.7).
- Mock provider: `{latency_ms: 40, tokens_per_sec: 200, scripted_outputs: {settle: "tien_hiep_01_10ch/resettle/ch{n}.json", validate: {consistent: true}, seam: {pass: true}, write: <như T07>}}`; biến thể T10-06: `scripted_outputs.validate` cho ch.7 = `{consistent: false, quote: "kiếm Thanh Phong"}`.
- Auto-write chạy ch.11–15 ở các kịch bản có batch.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T10-01 | biên | Auto-write đang viết ch.11; mở ch.10 trong editor. | Editor ch.10 read-only, nhãn "đang làm nền cho Ch.11", nút "Tạm dừng để sửa". BE: `PUT /v1/chapters/{ch10}` hoặc working copy ch.10 bị từ chối (chương đang là nền của job chạy), không ghi gì. | e2e-fe, integration | `fe/tests/e2e/base_chapter_readonly.spec.ts`, `be/tests/integration/test_base_chapter_guard.py` |
| T10-02 | hủy | Bấm "Tạm dừng để sửa" khi ch.11 ở bước `write`. | Batch dừng sau bước hiện tại; job ch.11 `cancelled`, candidate ch.11 `superseded` vì base đổi; ch.10 mở khóa sửa. Sửa ch.10 → state ch.10 phải settle lại trước khi viết tiếp (continuity `stale_from(10)`). Resume batch → resync ch.10 rồi viết lại ch.11 từ handoff mới. | integration, e2e-fe | `be/tests/integration/test_pause_to_edit.py` |
| T10-03 | thành công | Auto-write đang viết ch.11; sửa tay ch.5 (không phải nền) và lưu. | Lưu thành công (expected revision khớp); `work.continuity_status = stale_from(5)`, event `work.continuity`; ch.11 chạy tới hết (commit hoặc `waiting_user`), không tạo job ch.12; banner "Mạch truyện cần settle lại từ Ch.5". | integration | `be/tests/integration/test_edit_old_chapter_during_batch.py` |
| T10-04 | thành công | Từ trạng thái `stale_from(5)`: `POST /v1/works/{id}/resync` `{from_chapter: 5}`. | Job `resync` lấy khóa truyện; settle tuần tự ch.5 → ch.11 từ snapshot ch.4; với mỗi chương: `story_states` và `chapter_handoffs` thay bằng bản mới (bản cũ còn trong lịch sử), `summaries` cập nhật, FTS cập nhật; văn bản `chapter_revisions` của ch.6–11 không đổi (hash bằng nhau, 0 revision mới); xong → continuity `ok`. | integration | `be/tests/integration/test_resync_sequential.py` |
| T10-05 | biên | Thứ tự gọi mock trong T10-04. | Request `settle` theo đúng thứ tự chương 5, 6, …, 11; request chương n chỉ gửi sau khi state chương n-1 đã ghi; 0 request bước `write`. | integration | như trên |
| T10-06 | lỗi | Sửa ch.3 xóa fact "mất kiếm Thanh Phong"; resync từ 3; validate ch.7 phát hiện ch.7 vẫn nhắc kiếm bị mất. | Resync dừng ở ch.7: finding `fact`/`blocker` trỏ đoạn ch.7; continuity `blocked_needs_resync`; state ch.3–6 đã cập nhật, ch.7 trở đi chưa; không tự sửa văn bản ch.7. | integration | `be/tests/integration/test_resync_conflict_downstream.py` |
| T10-07 | biên | `stale_from(5)`, chọn "Bỏ qua có xác nhận". | Yêu cầu xác nhận rõ; sau xác nhận continuity `ok`, lựa chọn được ghi vào lịch sử thao tác (ai, khi nào, chương); không chạy settle. | integration, e2e-fe | `be/tests/integration/test_stale_skip_confirm.py` |
| T10-08 | biên | Sửa ch.7 rồi ch.4 (khi chưa resync). | Continuity = `stale_from(4)` (K nhỏ nhất). | unit, integration | `be/tests/unit/test_stale_from_min.py` |
| T10-09 | lỗi | Truyện `stale_from(5)`: tạo job write ch.11 hoặc `autowrite`. | `WORK_BLOCKED`, `action` = resync; không tạo job. | integration | `be/tests/integration/test_write_blocked_when_stale.py` |
| T10-10 | thành công | Không có batch; sửa tay chương mới nhất ch.10. | Continuity chuyển trạng thái cần settle lại ch.10 (đề xuất `stale_from(10)`); job write ch.11 bị chặn tới khi settle lại ch.10 xong; handoff ch.10 sau settle phản ánh văn bản mới. | integration | `be/tests/integration/test_edit_latest_chapter.py` |
| T10-11 | thành công | Tab "Nối": sửa `ending_state` ch.10 (đổi địa điểm) qua `PUT /v1/chapters/{ch10}/handoff`; viết ch.11. | Handoff lưu revision mới; plan ch.11 có `input_hash` mới; prompt Writer ch.11 chứa `ending_state` đã sửa; seam check ch.11 so với bản đã sửa. | integration, e2e-fe | `be/tests/integration/test_edit_handoff.py` |
| T10-12 | lỗi | Khi batch đang chạy: chèn chương giữa, xóa chương, `POST /v1/works/{id}/chapters/reorder`. | Cả ba bị từ chối (truyện đang chạy), không đổi dữ liệu; thông báo hướng dẫn tạm dừng batch trước. | integration | `be/tests/integration/test_structure_change_while_running.py` |
| T10-13 | thành công | Batch dừng; chèn chương mới sau ch.4 (`POST /v1/works/{id}/chapters`). | Chương mới thành ch.5, các chương sau dời số; continuity `stale_from(5)`; resync bắt buộc trước khi viết tiếp. | integration | `be/tests/integration/test_insert_chapter_middle.py` |
| T10-14 | thành công | Xóa chương mới nhất ch.10 (`DELETE /v1/chapters/{id}`) có xác nhận. | Ch.10 vào thùng rác/lưu trữ (khôi phục được); state quay về snapshot ch.9; handoff ch.10 và FTS ch.10 bị gỡ; continuity `ok`; chương kế tiếp để viết là 10. | integration | `be/tests/integration/test_delete_latest_chapter.py` |
| T10-15 | thành công | Xóa ch.6 (giữa truyện) có xác nhận. | UI hiện phụ thuộc (chương 7–10 bị ảnh hưởng) và lựa chọn rebuild; không xóa hàng loạt; continuity `stale_from(6)`. | integration, e2e-fe | `be/tests/integration/test_delete_middle_chapter.py` |
| T10-16 | thành công | Đổi thứ tự ch.6 và ch.7. | Continuity `stale_from(6)`; văn bản giữ nguyên; resync theo thứ tự mới. | integration | `be/tests/integration/test_reorder_chapters.py` |
| T10-17 | thành công | Restore revision cũ của ch.8 (`POST /v1/chapters/{id}/revisions/{rev}/restore`). | Tạo revision mới nguồn restore (không xóa revision nào); trước restore có revision chụp bản hiện tại; continuity `stale_from(8)`. | integration | `be/tests/integration/test_restore_marks_stale.py` |
| T10-18 | thành công | Luồng Playwright: tạo truyện → auto-write → bị chặn (seam fail) → sửa tay → settle lại → chạy tiếp. | Toàn bộ luồng chạy với mock backend; banner và Phòng viết đổi trạng thái đúng mỗi bước; batch tiếp tục và commit thêm chương. | e2e-fe | `fe/tests/e2e/main_flow_block_fix_continue.spec.ts` |

## Kiểm tra dữ liệu sau test

- DB: sau resync thành công, `story_states`/`chapter_handoffs` hiện hành của K..N là bản mới, bản cũ còn trong lịch sử; `chapter_revisions` của các chương sau K không có dòng mới; continuity đúng giá trị mong đợi từng kịch bản.
- Lịch sử thao tác ghi: sửa tay, bỏ qua stale, xóa, chèn, đổi thứ tự, restore.
- Event: `work.continuity` mỗi lần đổi giữa `ok`, `stale_from(K)`, `blocked_needs_resync`; `job.step` `settle` theo chương trong job `resync`.

## Tiêu chí pass

- 0 lần văn bản chương sau K bị AI viết lại trong resync (so hash toàn bộ chương K+1..N).
- 0 chương được viết khi truyện ở `stale_from(K)` hoặc `blocked_needs_resync`.
- 0 lần ghi được vào chương đang làm nền của job đang chạy.
- Thứ tự settle trong resync tuần tự tuyệt đối (kiểm từ log mock).
- Sau mọi kịch bản kết thúc ở `ok`: 0 chương committed có `state_applied=false`.

## Ghi chú thủ công

- Kiểm bằng mắt hộp thoại xóa chương giữa: liệt kê đúng các chương phụ thuộc và lựa chọn, ngôn ngữ rõ ràng.

## Tên mới đề xuất

- Lưu `stale_from(K)`: `works.continuity_status` + `works.continuity_chapter_no` (Plan §24 D33).
- Mã lỗi khi ghi vào chương đang làm nền: `CHAPTER_IS_BASE` (hoặc dùng `WORK_BLOCKED` — cần chốt).
- Nguồn revision `restore` trong `chapter_revisions.source`; bảng lịch sử thao tác `work_action_log` (FL07 "lịch sử action được giữ").
- Ngữ nghĩa "Tạm dừng để sửa": `POST /v1/works/{id}/autowrite/pause` `{reason: "edit_base"}` (hủy candidate chương đang viết, khác pause thường ở T07-08).
