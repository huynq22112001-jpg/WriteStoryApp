# T06 — Chương lỗi và bị chặn

Tính năng: F10, F11. Nguồn: Plan FL04 bước 4–7, §6.2 (quy tắc), §23.1.A (validator xác định), §23.1.B (`paragraph_id`, ops), §4.3 (`blocked_needs_resync`), §21 (LNG/MEM), UI §5.2 banner, §5.3. Cấp test chính: unit, contract, integration, e2e-fe.

## Mục đích

Chứng minh mọi lỗi liền mạch (seam, fact/timeline, tên riêng, nhân vật đã chết, lặp n-gram, state delta sai) đều chặn commit, được sửa cục bộ tối đa K vòng; hết vòng thì chương ở `waiting_user`, truyện `blocked_needs_resync`, không bao giờ commit chương thiếu state hợp lệ, và truyện khác không bị ảnh hưởng.

## Tiền điều kiện và dữ liệu

- Truyện `tests/fixtures/stories/tien_hiep_01/` như T05 (3 chương committed); nhân vật "Hắc Sát" `status=dead` từ ch.2; ending_state ch.3: Bến đò, đêm, mưa, Lâm Phong bị thương + Mộc Lan, đang truy đuổi.
- Truyện thứ hai `do_thi_01` chạy auto-write song song (kiểm không ảnh hưởng chéo).
- K = 2 vòng; trần token sửa mỗi chương: 20.000 (cấu hình test).
- Mock provider mặc định như T05, thay đổi theo kịch bản:
  - Seam fail rồi pass: `scripted_outputs.seam: [{pass: false, issues: [{paragraph_id: "p1", aspect: "location", expected: "Bến đò", found: "Tửu lâu"}]}, {pass: true}]`, `scripted_outputs.repair: "tien_hiep_01/repair_ch04_p1.json"`.
  - Seam fail mãi: `scripted_outputs.seam: [fail, fail, fail]`.
- Fixture state lỗi: `tests/fixtures/state/invalid_deltas/*.json` (mỗi file vi phạm đúng một ràng buộc).

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T06-01 | phục hồi | Viết ch.4 với seam fail lần 1, pass lần 2. | Finding `seam`/`blocker`/nguồn `seam` trích `p1` → `job.step` `repair` với payload vòng 1/2 → chạy lại từ `check` → seam pass → commit. Candidate `repair` mới, candidate `draft` thành `superseded`; finding chuyển `resolved`. Chỉ `p1` đổi, các đoạn khác giữ nguyên `paragraph_id` và nội dung (so hash). | integration | `be/tests/integration/test_seam_repair_once.py` |
| T06-02 | lỗi | Viết ch.4 với seam fail 3 lần liên tiếp. | Sau 2 vòng: job `waiting_user`, `work.continuity_status = blocked_needs_resync`, event `work.continuity`; 0 revision ch.4, 0 `story_states` ch.4, `state_applied` không được đặt; findings blocker `open`; candidate cuối `ready` để tác giả xem. Phòng viết hiện "⛔ waiting_user: seam fail sau 2 vòng". | integration | `be/tests/integration/test_seam_fail_blocks.py` |
| T06-03 | lỗi | Unit validator xác định với từng file `invalid_deltas/`: ID không tồn tại; `character.move` cho nhân vật `dead`; `time.advance` lùi không có cờ hồi tưởng; `hook.advance` cho hook đã `resolved`; nhân vật dùng fact chưa `character.learn`; thao tác thiếu `evidence`. | Mỗi file bị từ chối với lỗi chỉ đúng thao tác và ràng buộc vi phạm; delta hợp lệ (`tests/fixtures/state/delta_ch04_ok.json`) qua. Hồi tưởng có cờ được phép lùi thời gian. | unit | `ai/tests/unit/test_state_validator_rules.py` |
| T06-04 | lỗi | Mock `settle` trả delta có `character.move` cho "Hắc Sát" (đã chết), lần 2 vẫn sai. | Validator (a) fail → sửa (settle lại có chỉ dẫn lỗi) → vẫn fail → `waiting_user` + `blocked_needs_resync`; không commit. | integration | `be/tests/integration/test_validator_fail_blocks.py` |
| T06-05 | lỗi | Mock `validate` (LLM) trả `consistent: false` kèm trích dẫn đoạn mâu thuẫn fact #12 ở ch.2, lần 2 `consistent: true`. | Finding `fact`/`blocker` nguồn `validator` có trích dẫn `paragraph_id`; sửa cục bộ; lần 2 commit; finding `resolved`. | integration | `be/tests/integration/test_llm_validator_repair.py` |
| T06-06 | lỗi | Mock `write` có tên "Trương Tam" không thuộc canon/bí danh và không khai báo; lần sửa thay bằng "Mộc Lan". | Bước `check` tạo finding `name`/`blocker`; sửa đoạn chứa tên; commit; 0 tên ngoài canon trong văn bản committed. | integration | `be/tests/integration/test_undeclared_name.py` |
| T06-07 | biên | Như T06-06 nhưng plan/settle khai báo "Trương Tam" là nhân vật mới. | Không có finding `name`; sau commit `characters` có "Trương Tam" với nguồn chương 4. | integration | `be/tests/integration/test_declared_new_character.py` |
| T06-08 | lỗi | Mock `write` có "Hắc Sát vung đao" (nhân vật đã chết hành động, không phải hồi tưởng). | Finding blocker từ `check` (không cần LLM) trỏ đúng đoạn; sửa cục bộ. | unit, integration | `ai/tests/unit/test_dead_character_check.py` |
| T06-09 | lỗi | Mock `write` chép nguyên văn 3 đoạn cuối ch.3. | Tỷ lệ n-gram trùng vượt ngưỡng cấu hình → finding (nguồn `check`) → sửa các đoạn trùng → tỷ lệ dưới ngưỡng rồi commit. | unit, integration | `ai/tests/unit/test_ngram_overlap.py` |
| T06-10 | biên | Mock `review` chỉ trả findings `minor` (nhịp, giọng văn). | Commit bình thường, không vòng sửa; findings `minor` `open`; không đổi continuity. | integration | `be/tests/integration/test_minor_findings_not_blocking.py` |
| T06-11 | lỗi | Trần token sửa = 2.000; seam fail lần 1, repair dùng 2.500 token. | Dừng trước vòng 2 với lý do "hết trần token sửa" lưu trong job; `waiting_user` + `blocked_needs_resync`. | integration | `be/tests/integration/test_repair_token_cap.py` |
| T06-12 | lỗi | Mock `repair` trả ops sửa cả `p7` nằm ngoài phạm vi được phép (chỉ `p1`). | BE từ chối op ngoài phạm vi, `p7` không đổi; vòng đó tính là thất bại và ghi vào trace. | unit, integration | `be/tests/unit/test_paragraph_ops_scope.py` |
| T06-13 | lỗi | Truyện đang `blocked_needs_resync`: `POST /v1/jobs` write; `POST /v1/works/{id}/autowrite`. | Cả hai trả `WORK_BLOCKED`, `action` = mở xử lý chặn; scheduler không lấy job viết mới của truyện; truyện `do_thi_01` vẫn commit chương trong cùng thời gian. | integration | `be/tests/integration/test_blocked_work_isolation.py` |
| T06-14 | phục hồi | Banner "Sửa tay rồi settle lại": tác giả sửa đoạn `p1` của candidate ch.4, rồi `POST /v1/works/{id}/resync` `{from_chapter: 4}`. | Chạy lại `check` → `settle` → `validate` → `seam` → `review` trên văn bản đã sửa; pass → commit; continuity `ok`; event `work.continuity`. | integration, e2e-fe | `be/tests/integration/test_blocked_manual_fix_resettle.py` |
| T06-15 | phục hồi | Banner "Chấp nhận kèm ghi chú" khi chỉ có finding seam/LLM-validator, delta qua validator xác định. | Commit kèm state; findings chuyển `dismissed` kèm ghi chú tác giả; continuity `ok`. Nếu delta không qua validator xác định thì accept bị từ chối `VALIDATION` (không commit chương thiếu state hợp lệ). | integration | `be/tests/integration/test_accept_with_note.py` |
| T06-16 | biên | Review trả finding trích đoạn không tồn tại (`paragraph_id` sai hoặc quote không khớp văn bản). | Host đánh dấu finding không xác minh được, không tính là blocker, không kích hoạt sửa. | contract | `ai/tests/contract/test_review_quote_verification.py` |
| T06-17 | phục hồi | Truyện đang `waiting_user` + `blocked_needs_resync`; khởi động lại backend. | Sau restart job vẫn `waiting_user` (không chuyển `interrupted`), continuity vẫn `blocked_needs_resync`, candidate và findings còn nguyên. | integration | `be/tests/integration/test_blocked_survives_restart.py` |
| T06-18 | thành công | FE: mở truyện bị chặn. | Banner "⛔ Mạch truyện bị chặn ở Ch.4…" có 4 nút [Xem lỗi] [Sửa tay rồi settle lại] [Chấp nhận kèm ghi chú] [Settle lại từ Ch.4]; [Xem lỗi] mở tab Review, bấm finding nhảy tới đoạn; trạng thái có icon + chữ, không chỉ màu. | e2e-fe | `fe/tests/e2e/blocked_banner.spec.ts` |

## Kiểm tra dữ liệu sau test

- DB: chương bị chặn không có `chapter_revisions`, `story_states`, `chapter_handoffs` mới; `findings` có `source`, `kind`, `severity`, trích dẫn `paragraph_id`, `status` đúng; `chapter_candidates` có chuỗi `draft` → `repair` với trạng thái `superseded`/`ready`.
- `job_steps`: số vòng sửa ≤ K; lý do dừng (hết vòng/hết trần token) được lưu.
- Event: `finding.added`, `job.step` (`repair`, vòng k/K), `work.continuity` khi đổi trạng thái, `job.state` `waiting_user`.

## Tiêu chí pass

- 0 chương committed có `state_applied=false` sau toàn bộ kịch bản.
- Số vòng sửa không bao giờ vượt K = 2; trần token sửa không bị vượt quá một request.
- 100% đoạn ngoài phạm vi sửa giữ nguyên nội dung và `paragraph_id`.
- Truyện song song không bị chậm/chặn: số chương commit của `do_thi_01` trong thời gian test bằng lần chạy đối chứng không có truyện lỗi (sai lệch ≤ 1 chương).
- 0 tên nhân vật ngoài canon chưa khai báo trong văn bản committed.

## Ghi chú thủ công

- Với model thật (`live`), đọc 5 lần sửa cục bộ: đoạn sửa phải nối mạch với đoạn trước/sau, không lặp ý.

## Tên mới đề xuất

- Trạng thái finding cho trích dẫn không xác minh được: `unavailable` (FL06 nói "đánh dấu unavailable", §5 chỉ có `open`/`resolved`/`dismissed`).
- Trường `findings.note` (ghi chú khi "Chấp nhận kèm ghi chú").
- `POST /v1/works/{id}/resync` nhận `{from_chapter, mode: resettle_only}` cho nút "Settle lại từ Ch.N" (không viết lại văn bản).
- Cờ hồi tưởng trong `time.advance`: `flashback: true`.
- Cấu hình `repair_token_cap` (trần token sửa mỗi chương).
