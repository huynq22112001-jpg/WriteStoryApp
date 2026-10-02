# F10 — Viết chương liền mạch

Giai đoạn: R2 (vertical slice cốt lõi của MVP; Plan §9 Giai đoạn 4). Trạng thái: planned.

## Mục tiêu

Tác giả bấm "Viết tiếp" (hoặc auto-write gọi thay) và nhận chương N nối liền chương N-1: cùng địa điểm/thời điểm/nhân vật có mặt, xử lý hành động dở dang, tiến đúng sự kiện và hook đến hạn, không mâu thuẫn state. Chương chỉ được lưu khi state sau chương hợp lệ; nếu sau tối đa K vòng sửa cục bộ vẫn còn lỗi chặn, truyện dừng ở `waiting_user` + `blocked_needs_resync` với lý do và hành động rõ ràng – không bao giờ viết chương N+1 trên nền hỏng.

Bảo đảm liền mạch N → N+1 dựa trên 8 cơ chế (chi tiết ở [ai.md](./ai.md#bảo-đảm-liền-mạch-n--n1)):

1. **Cổng vào**: N-1 committed, `state_applied`, `continuity_status = ok`, đúng số chương kế tiếp.
2. **Handoff có cấu trúc**: `ending_state(N-1)` + `tail_text(N-1)` (1.000–2.000 token, cắt theo đoạn) đi vào **cả Planner và Writer**, thuộc phần context **bảo vệ**.
3. **Plan buộc cảnh mở nối từ `ending_state`**, lưu kèm `input_hash`; đầu vào đổi thì lập lại plan.
4. **Seam check** đối chiếu đoạn mở N với `ending_state(N-1)` (địa điểm, thời điểm, người có mặt, cảm xúc, hành động dở dang).
5. **State có bằng chứng, kiểm tra xác định trước LLM**; lỗi fact/timeline/seam/tên riêng là `blocker`.
6. **Sửa cục bộ có giới hạn** (K=2 vòng, trần token), không viết lại cả chương.
7. **Commit một transaction**: revision + snapshot + handoff(N) + tóm tắt + hooks + timeline + FTS + kết quả job; chương N+1 chỉ được enqueue sau commit.
8. **Sửa của tác giả có hiệu lực xuôi dòng**: sửa handoff → plan N+1 lập lại; sửa chương cũ → `stale_from(K)` (F11).

## Phạm vi

- Trong phạm vi: pipeline một chương Plan §6.2 (11 bước), bảng `chapter_handoffs`, `chapter_plans`, đo đạc chương, ngân sách nhịp truyện và chống kết thúc sớm (§23.3 #5), xét lại dàn ý mỗi K chương (§23.3 #6), style anchor (§23.3 #7), refusal / viết tiếp khi bị cắt `max_tokens` / fallback structured output (§23.3 #2–#3), các bước job + checkpoint + điểm resume, event (`job.step`, `token.delta`, `candidate.ready`, `finding.added`, `chapter.committed`, `work.continuity`), chỉ số Plan §9 Giai đoạn 4; FE: tab AI (`CandidateStream`, tiến độ pipeline), tab "Nối" (xem/sửa handoff, kết quả seam), banner bị chặn (UI §5.2).
- Ngoài phạm vi: nhận từng đoạn, diff, sửa theo yêu cầu, resync `stale_from` (F11); hàng đợi đa truyện, chế độ auto-write, ước tính chi phí (F12); contract state, Composer, tìm kiếm (F09); kiểm tra tiếng Việt (F08); revise theo yêu cầu tác giả (§6.3, F11); forecast (LNG15, R3).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F04 | Provider, model theo vai trò + effort ghim vào job, limiter, capability `structured_outputs`, `max_input_tokens` |
| F07 | `paragraph_id`, revision, working copy; chương N-1 read-only khi N đang viết |
| F08 | Chuẩn hóa output AI, kiểm tra tiếng Việt bước 5, prompt + manifest, đếm âm tiết |
| F09 | `StoryState`/`StateDelta`, reducer, validator xác định, Composer, `tail_text`, tóm tắt, trace |
| F01/F02 | Event envelope, job/job_steps, writer queue, khóa truyện |
| F06 (song song) | Nền truyện, `story_events`, hooks, `address_rules`, state seed chương 0 |

## Nguồn thiết kế

- Plan §6.2 (pipeline và quy tắc), §6.4, §6.5, §4.2–§4.3 (tuần tự trong truyện, trạng thái job), §5 (`chapter_handoffs`, `chapter_plans`, `findings`, `chapter_candidates`), §7 (API jobs/continuity/handoff/trace), §7.1 (vai trò + effort, ghim trong lượt viết), §9 Giai đoạn 4 (chỉ số), FL04, FL06, §21 dòng LNG/MEM, §23.1.A–D, §23.2 #1, #3, §23.3 #2, #3, #5, #6, #7.
- Arch §6 (`workflows/longform/pipeline.py`, `planner.py`, `writer.py`, `settlement.py`, `seam_check.py`, `repair.py`, `handoff.py`, `pacing.py`, `outline_review.py`, `reviewer.py`), §8 (luồng AI viết một chương).
- UI §5.2 (tab AI, tab Nối, banner), §5.3 (pipeline ở Phòng viết), §6 (hiệu năng stream).
- Review §2 (luồng InkOS), §2.3 (9 điểm yếu), §4 (thiết kế liền mạch), §4.7 (chỉ số).
- InkOS (AGPL, chỉ tham khảo ý tưởng): `pipeline/runner.ts` (`writeNextChapter`), `agents/composer.ts`, `agents/writer.ts`, `agents/state-validator.ts`, `pipeline/chapter-truth-validation.ts`.
- Nghiên cứu: Re3 ([arxiv 2210.06774](https://arxiv.org/abs/2210.06774)) và ConWriter ([arxiv 2608.05169](https://arxiv.org/abs/2608.05169)) – sửa cục bộ, kiểm tra chuyển tiếp; StoryWriter ([arxiv 2506.16445](https://arxiv.org/abs/2506.16445)) – sự kiện phân bổ theo chương; DOME ([arxiv 2412.13575](https://arxiv.org/abs/2412.13575)) – dàn ý động; NstAgent ([arxiv 2609.35759](https://arxiv.org/abs/2609.35759)) – việc tương lai bắt buộc; ConStory-Bench ([arxiv 2603.05890](https://arxiv.org/html/2603.05890v1)); so sánh 7 framework ([arxiv 2608.26177](https://arxiv.org/abs/2608.26177)) – trôi thuộc tính, length collapse; Antislop ([arxiv 2510.15061](https://arxiv.org/abs/2510.15061)); EQ-Bench Longform ([GitHub](https://github.com/EQ-bench/longform-writing-bench)).
- Mã Plan §15: LNG05, LNG07, LNG09, LNG10, LNG11, LNG12, LNG13, LNG14.

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Job `write`: cổng vào, ghim cấu hình, gọi pipeline AI với sink tiến độ/checkpoint, commit một transaction, bước sau commit; bảng `chapter_handoffs`, `chapter_plans`, `chapter_measurements`; API continuity/handoff/plan/seam/metrics/outline proposals |
| FE | [fe.md](./fe.md) | Tab AI: `CandidateStream`, `PipelineProgress`, card candidate; tab Nối: handoff xem/sửa, kết quả seam, hook đến hạn; `BlockedBanner` với 4 hành động |
| AI | [ai.md](./ai.md) | `pipeline.py` từng bước có input/output, contract plan/settle/seam/review/repair, vòng sửa, nhịp truyện, xét lại dàn ý, style anchor, refusal/cắt output/structured output, so sánh với InkOS, đánh giá |

## Tiêu chí hoàn thành

- [ ] Một chương mock đi hết 11 bước, commit một transaction; kill process ở mọi bước rồi resume không tạo chương trùng, không commit thiếu state.
- [ ] Không có đường code nào commit chương khi validator xác định còn `error` (test thuộc tính + review code).
- [ ] Seam fail / blocker → sửa cục bộ ≤ K vòng; hết vòng → `waiting_user` + `blocked_needs_resync`, chương N+1 không được enqueue.
- [ ] Refusal không retry lặp; `max_tokens` viết tiếp ≤ 2 lần; JSON hỏng sửa 1 lần rồi `STRUCTURED_OUTPUT_INVALID`.
- [ ] Plan dùng lại chỉ khi `input_hash` khớp (sửa điểm yếu InkOS #8).
- [ ] 3 truyện mẫu × 20 chương chạy song song (với F12) đạt chỉ số Plan §9 Giai đoạn 4: 0 chương `state_applied=false`; seam pass ≥ 95% sau ≤ 2 vòng; 0 tên nhân vật ngoài canon chưa khai báo; 0 lỗi xưng hô không có sự kiện, không trộn kiểu bỏ dấu; 100% hook quá hạn được báo; n-gram trùng chương kề dưới ngưỡng; người đọc chấm theo kiểu EQ-Bench Longform; tác giả xem được context/review/history.
- [ ] Test luồng pass: [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md); phần F10 của [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md), [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md), [T15](../../tests/flows/T15-loi-provider.md), [T07](../../tests/flows/T07-auto-write-mot-truyen.md).

## Rủi ro và câu hỏi mở

- Hiệu quả của "đuôi chương nguyên văn" và "hợp đồng mở chương" chưa có nguồn sơ cấp so sánh (Review §10) – là [Suy luận], phải đo trên bộ truyện mẫu.
- Seam check và review dùng LLM có thể báo nhầm; ngưỡng ≥ 95% seam pass có thể buộc nới/siết quy tắc chuyển cảnh. Ghi tỷ lệ báo nhầm do tác giả bác bỏ.
- Chi phí mỗi chương tăng do nhiều bước (settle, validate, seam, review, sửa); prompt theo lớp và cache giảm một phần – cần đo `cache_read_tokens` thực tế.
- Plan §6.6 yêu cầu sửa cụm sáo cục bộ, nhưng §6.2 chỉ kích hoạt sửa khi có `blocker`/seam fail; thiết kế ở đây gộp cụm sáo vào vòng sửa khi vòng đó đã chạy, và có tùy chọn bật vòng riêng (ai.md).
- Nhân vật mới do Writer tự thêm ngoài plan: mặc định chỉ `major` (được khai báo qua `character.add`), tùy chọn `strict_new_characters` biến thành `blocker` – cần tác giả chốt.
- UI §5.3 rút gọn pipeline thành 6 bước (Kế hoạch▸Viết▸Kiểm tra▸Nối▸Review▸Lưu), Plan §6.2 có 11 bước: cần bảng ánh xạ hiển thị (fe.md).
