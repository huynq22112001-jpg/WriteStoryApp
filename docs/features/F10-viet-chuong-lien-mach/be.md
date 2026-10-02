# F10 — Backend

BE sở hữu cổng vào, ghim cấu hình, khóa truyện, checkpoint, commit và trạng thái liền mạch. Pipeline AI (ai.md) chỉ trả `PipelineResult`; BE quyết định commit (Arch §6, §8).

## Module và file

```text
be/src/writestory_be/modules/longform/chapter_write/
  router.py        /v1/works/{id}/continuity*, /v1/chapters/{id}/handoff|plan|seam, outline proposals
  schemas.py       WriteJobRequest, ContinuityDTO, HandoffDTO, HandoffUpdate, PlanDTO, SeamResultDTO, MetricsDTO, OutlineProposalDTO
  service.py       enqueue_write, resolve_block, update_handoff, apply_outline_proposal
  gate.py          entry_gate(work, chapter_no) -> GateResult
  pinning.py       PinnedConfig: model+effort theo vai trò, bible_revision, manifest prompt, WriteSettings
  commit.py        commit_chapter(uow, result) – một transaction
  measurements.py  Tính và lưu chapter_measurements
be/src/writestory_be/jobs/handlers/chapter_write.py   Điều phối bước, checkpoint, resume, hủy
be/src/writestory_be/infrastructure/ai/progress_adapter.py  ProgressSink/CheckpointSink → job_steps, job_events, chapter_candidates
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `chapter_handoffs` | `id`, `work_id`, `chapter_no`, `revision_id` (revision nguồn), `handoff_revision`, `ending_state` JSON (`EndingState` F09), `tail_text`, `tail_paragraph_ids` JSON, `tail_tokens`, `tail_counted_for_model`, `open_threads` JSON, `next_opening_requirements` JSON, `source` (`pipeline`\|`user_edit`), `note`, `is_current`, `created_at` | UNIQUE (`work_id`,`chapter_no`) WHERE `is_current`; FK `revision_id` | Plan §5; chương 0 có handoff mở đầu sinh từ nền truyện (không có `tail_text`) |
| `chapter_plans` | `id`, `work_id`, `chapter_no`, `input_hash`, `inputs` JSON (`state_hash`, `handoff_id`+`handoff_revision`, `outline_revision`, `story_events_revision`, `bible_revision`, `brief_hash`, `prompt_version`), `plan_json` (`ChapterPlan`), `status` (`active`\|`superseded`), `edited_by_user`, `job_id`, `model_id`, `created_at` | index (`work_id`,`chapter_no`,`input_hash`) | Plan §5: dùng lại chỉ khi hash khớp |
| `chapter_candidates` (F11 định nghĩa) | F10 ghi: `kind` (`draft`\|`repair`), `parent_candidate_id`, `round`, `paragraphs` JSON, `status` (`streaming`\|`partial`\|`ready`\|…), `stop_reason`, `continuations`, `length_units`, `checks_summary` JSON, `delta_json`, `ending_state` JSON, `summary_json`, `seam_json`, `base_state_id`, `plan_id` | — | Plan §5, §23.2 #1 |
| `findings` (F11 định nghĩa) | F10 ghi `source` (`check`\|`validator`\|`seam`\|`review`), `kind`, `severity`, `paragraph_id`, `quote`, `candidate_id`, `round`, `needs_confirmation`, `status`, `override_note` | index (`work_id`,`status`) | |
| `chapter_measurements` | `chapter_id`, `revision_id`, `chapter_no`, `length_units`, `length_chars`, `seam_pass_first_try`, `seam_rounds`, `repair_rounds`, `unknown_character_names`, `address_violations`, `accent_mixed`, `overdue_hooks_reported`, `ngram_overlap_prev`, `findings_by_severity` JSON, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_estimate`, `writer_model_id`, `writer_effort`, `duration_ms`, `state_applied` | PK (`chapter_id`,`revision_id`) | "measurement" trong commit của FL04 bước 8; nguồn chỉ số Plan §9 |
| `works` (F05) | Dùng cột F05: `continuity_status` (`ok`\|`blocked_needs_resync`\|`stale_from`), `target_chapters`, `chapter_length_min`/`max`, `max_repair_rounds`, `autowrite_mode_default`, `review_every_k`. Chương bị chặn ghi vào `continuity_chapter_no` + `continuity_reason` JSON (thống nhất theo Plan §24 D33). F10 thêm: `allow_early_ending` BOOL, `writing_config` JSON (khóa `WriteSettings` không có cột riêng) | — | Plan §4.3 |
| `chapters` (F07) | Dùng cột F07 `status` (`draft`\|`drafting`\|`checking`\|`revising`\|`waiting_user`\|`committed`) và `state_applied` | — | Review §4.4; F10 ghi `status` theo bước |
| `story_events` (F06) | Dùng `locked`, `done_in_chapter`, `moved_from_chapter` của F06 | — | Xét lại dàn ý không đụng sự kiện tác giả khóa (§23.3 #6) |
| `outline_proposals` | `id`, `work_id`, `after_chapter_no`, `changes` JSON, `status` (`pending`\|`applied`\|`rejected`\|`partially_applied`), `job_id`, `created_at` | index (`work_id`,`status`) | Kết quả bước xét lại dàn ý |

Migration: `be/migrations/versions/<rev>_chapter_pipeline.py`. Không cần backfill.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| POST | `/v1/jobs` | `{type:"write", work_id, chapter_no?, brief?, instruction?, idempotency_key}` | `202 {job_id, chapter_no, status:"queued"\|"waiting_slot"}` | `WORK_BLOCKED`, `CHAPTER_RANGE_CONFLICT`, `VALIDATION` |
| GET | `/v1/works/{id}/continuity` | — | `{status, chapter_no, reason, latest_handoff: HandoffDTO, open_findings: {blocker, major, minor}, blocked_candidate_id?, last_seam?: SeamResultDTO}` | 404 |
| GET | `/v1/works/{id}/continuity/metrics?from=&to=` | — | Tổng hợp `chapter_measurements` + tỷ lệ seam pass, số hook quá hạn được báo | — |
| GET | `/v1/chapters/{id}/handoff` | — | `HandoffDTO` | 404 |
| PUT | `/v1/chapters/{id}/handoff` | `{expected_handoff_revision, ending_state, open_threads, next_opening_requirements, note}` | `HandoffDTO` (revision mới) | `REVISION_CONFLICT`, `WORK_BLOCKED` (job chương N+1 đã qua bước plan), `VALIDATION` (người có mặt đã chết, địa điểm không tồn tại) |
| GET | `/v1/chapters/{id}/plan` | — | `PlanDTO` (plan hiện hành, `input_hash`, có còn khớp đầu vào không) | 404 |
| PUT | `/v1/chapters/{id}/plan` | `{expected_plan_id, plan}` | `PlanDTO` (`edited_by_user=true`) | `REVISION_CONFLICT`, `VALIDATION` (plan sai ràng buộc) |
| GET | `/v1/chapters/{id}/seam` | — | `SeamResultDTO` mới nhất | 404 |
| POST | `/v1/jobs/{id}/resume` | `{action: "continue"\|"retry_repair"\|"resettle"\|"settle_author_text", working_copy_revision?}` | `202 {job_id}` | `WORK_BLOCKED`, `VALIDATION` |
| POST | `/v1/candidates/{id}/accept` | (F11) + `{note?, override_finding_ids?}` | `{revision_id}` | `WORK_BLOCKED` (`detail.reason="STATE_INVALID"`), `REVISION_CONFLICT` |
| GET | `/v1/works/{id}/outline-proposals?status=pending` | — | `[OutlineProposalDTO]` | — |
| POST | `/v1/outline-proposals/{id}/apply` \| `/reject` | `{change_ids?}` | `OutlineProposalDTO` | `REVISION_CONFLICT`, `VALIDATION` (đụng sự kiện khóa) |

Hủy/xem job dùng API chung `POST /v1/jobs/{id}/cancel`, `GET /v1/jobs/{id}` (F01/F12).

## Logic xử lý

**Cổng vào (`gate.py`)** – chạy khi tạo job và lặp lại khi job được cấp slot:

1. `works.continuity_status == ok`; ngược lại `WORK_BLOCKED` (`detail.status`, `detail.chapter_no`).
2. N = số chương committed liên tục cuối + 1; `chapter_no` truyền vào khác N → `CHAPTER_RANGE_CONFLICT`.
3. Chương N-1 (N>1) có `state_applied=true`; `chapter_working_copy` của N-1 không có thay đổi chưa tạo revision (nếu có → `waiting_user` lý do `PREV_CHAPTER_DIRTY`, hành động "Tạo revision và settle lại").
4. Không có job ghi khác của truyện đang chạy (khóa `work_locks` có lease; đến sau thì `waiting_slot`, Plan §4.2).
5. Tạo/khôi phục hàng `chapters` N (`status=drafting`), ghim `PinnedConfig` vào `jobs` (model + effort theo vai trò, `bible_revision`, phiên bản manifest prompt, `WriteSettings`). Thay đổi cài đặt sau thời điểm này chỉ áp từ chương kế tiếp (Plan §7.1).

**Chạy pipeline (`jobs/handlers/chapter_write.py`):**

1. Đóng mọi transaction đọc; dựng `GenerationInput` + `ContextPort` (F09) + `ProgressSink` + `CheckpointSink` + `CancelToken`.
2. Áp `state_pending_deltas` (F09) lên state N-1 trước khi plan.
3. Gọi `ai.workflows.longform.pipeline.run_chapter(...)`. Mỗi bước: ghi `job_steps` (`step`, `round`, `attempt`, `input_hash`, `output_ref`, `prompt_version`, model/effort, usage, timing) và phát `job.step`.
4. Kết quả:
   - `ready` + chế độ `auto` (hoặc job một chương do tác giả bấm và cài đặt "tự lưu khi qua mọi cổng") → **commit**.
   - `ready` + `review_each`/mốc `review_every_k` → job `waiting_user` (chờ accept), `continuity_status` giữ `ok`.
   - `needs_user` lý do `REPAIR_EXHAUSTED` hoặc state không hợp lệ → job `waiting_user`, `works.continuity_status = blocked_needs_resync`, phát `work.continuity`.
   - `needs_user` lý do provider (`PROVIDER_REFUSAL`, `OUTPUT_TRUNCATED`, `STRUCTURED_OUTPUT_INVALID`, `CONTEXT_PROTECTED_OVER_BUDGET`, review không khả dụng) → job `waiting_user`, continuity giữ `ok` (chương N chưa commit nên cổng vẫn chặn N+1).

**Commit (`commit.py`) – một transaction qua writer queue (Plan §6.2 bước 11, FL04 bước 8):**

1. Kiểm tra lại: job chưa bị hủy; khóa còn lease; chương N chưa commit (nếu đã commit bằng chính `candidate_id` này → trả kết quả cũ, idempotent); `story_states` hiện hành N-1 có `state_hash == delta.base_state_hash`.
2. Chạy lại validator xác định (F09) trên delta cuối – còn `error` → abort, không commit.
3. Chèn `chapter_revisions` (F07: `source=agent`, `reason=pipeline_commit`, `candidate_id`, `doc_json` + `plain_text` + `paragraphs_json` theo `paragraph_id`, NFC); cập nhật `chapters.current_revision_id`, `status=committed`.
4. F09 `commit_chapter_state`: snapshot N, sổ cái facts/hooks/timeline/story_events/address_rules/characters, FTS, `state_applied=true`.
5. Chèn `chapter_handoffs` N (`ending_state` từ settle, `tail_text` từ `cut_tail`, `open_threads`, `next_opening_requirements`).
6. Chèn `summaries` cấp chương.
7. `findings` của candidate: blocker/major đã xử lý → `resolved`; override của tác giả → `dismissed` + `override_note`; `minor` giữ `open`.
8. `chapter_candidates`: candidate cuối `accepted`, các bản cùng job `superseded`.
9. `chapter_measurements`; `jobs` kết quả + usage; `usage_counters`.
10. `job_events`: `chapter.committed`, `work.continuity` (`ok`).

Không giữ transaction trong lúc gọi AI; toàn bộ bước 1–10 là ghi thuần, dự kiến vài chục ms (giả định, đo ở R0).

**Sau commit (vẫn giữ khóa truyện):** `summarize_hierarchy` (F09) → `outline_review` khi `N % outline_review_every_k == 0` (mặc định 10) hoặc ≥ 2 sự kiện chuyển `moved` từ lần xét trước → áp đề xuất theo chế độ (ai.md) → nhả khóa → báo F12 enqueue N+1 → thông báo đã cấu hình (FL04 bước 9). Lỗi ở hai bước này không hoàn tác commit.

**Sửa handoff (`PUT /handoff`):** chỉ cho chương committed mới nhất; validate `ending_state` với snapshot (người có mặt `alive`, địa điểm tồn tại); tạo `handoff_revision` mới → `input_hash` của plan N+1 đổi → plan N+1 sẽ lập lại. Nếu job N+1 đang ở bước write trở đi → `WORK_BLOCKED` (hành động: hủy job N+1 rồi sửa). Đổi vị trí nhân vật trong `ending_state` không tự đổi state; FE đề xuất kèm delta người dùng (F09).

**Gỡ chặn (banner UI §5.2):**

| Nút | API | Điều kiện |
|---|---|---|
| Xem lỗi | `GET /v1/works/{id}/findings?status=open` (F11) | — |
| Sửa tay rồi settle lại | Nạp candidate vào working copy chương N (F11) → `POST /v1/jobs/{id}/resume {action:"settle_author_text"}` → chạy lại từ bước 5 với văn bản tác giả | Văn bản tác giả vẫn phải qua validator xác định |
| Chấp nhận kèm ghi chú | `POST /v1/candidates/{id}/accept {note, override_finding_ids}` | Chỉ bỏ qua được finding mức LLM (seam/review/validator LLM); validator **xác định** còn `error` → `WORK_BLOCKED` `STATE_INVALID` (không bao giờ commit thiếu state hợp lệ) |
| Settle lại từ Ch.K | `POST /v1/works/{id}/resync` (F11) hoặc `resume {action:"resettle"}` cho chương N | — |

Commit thành công từ các nút trên đặt `continuity_status=ok`.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `job.step` | Bắt đầu/kết thúc/lỗi mỗi bước | `{step, status:"started"\|"completed"\|"failed"\|"skipped", round?, max_rounds?, attempt, reason_code?}` |
| `token.delta` | Writer/repair stream (gộp 50–100 ms, chỉ gửi cho client đăng ký `works=`; không lưu lâu – Plan §23.1.C) | `{candidate_id, paragraph_id?, text, offset}` |
| `candidate.ready` | Candidate hoàn tất một lượt (draft hoặc repair) | `{candidate_id, chapter_no, kind, round, length_units, checks_summary:{blocker, major, minor}, seam?:"pass"\|"fail"}` |
| `finding.added` | Mỗi finding mới (check/validator/seam/review) | `{finding_id, kind, severity, source, paragraph_id, round}` |
| `chapter.committed` | Commit xong | `{chapter_id, chapter_no, revision_id, state_id, handoff_id}` |
| `work.continuity` | Đổi `continuity_status` | `{status, chapter_no, reason_code, blocked_candidate_id?}` |
| `job.state` | Đổi trạng thái job (`waiting_user`, `blocked`…) | theo F01 |

Bước job (tên dùng trong `job_steps.step` và FE): `gate`, `load`, `plan`, `compose`, `write`, `check`, `settle`, `validate`, `seam`, `review`, `repair`, `summarize_chapter`, `commit`, `summarize_hierarchy`, `outline_review`. Điểm resume: xem bảng ở ai.md.

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Truyện `blocked_needs_resync`/`stale_from` | Không tạo job | `WORK_BLOCKED` |
| Yêu cầu chương không phải chương kế tiếp | Từ chối, trả N đúng | `CHAPTER_RANGE_CONFLICT` |
| Truyện đang có job ghi | Xếp hàng `waiting_slot` | (thông tin) `WORK_BUSY_QUEUED` |
| Vault khóa / hết ngân sách / mất mạng / 429 | `waiting_slot` kèm lý do (Plan §23.2 #7–#8, §4.2) | `VAULT_LOCKED`, `BUDGET_EXCEEDED`, `PROVIDER_UNREACHABLE`, `PROVIDER_RATE_LIMIT` |
| Sai API key | Job `failed`, không retry | `PROVIDER_AUTH` |
| Tác giả bấm "Tạm dừng để sửa" chương N-1 (Plan §23.2 #3) | Dừng sau bước hiện tại, candidate N `superseded`, job `cancelled` | — |
| Hủy trong lúc commit | Commit kiểm tra cờ hủy trong transaction; đã commit thì giữ (xử lý bằng revision/restore) | — |
| App tắt giữa chừng | Job `interrupted`; resume từ checkpoint hợp lệ cuối (ai.md); partial hiển thị, không coi là chương | — |
| Chương 1 | Dùng state seed + handoff mở đầu (chương 0) | — |
| N vượt `target_chapters` | Cho phép nếu tác giả yêu cầu; plan `allowed_ending` theo cấu hình | — |

## Việc cần làm

- [ ] Migration bảng/cột ở trên; ORM, repository `handoffs`, `plans`, `measurements`, `outline_proposals`.
- [ ] `gate.py` + test từng điều kiện; `pinning.py`.
- [ ] Handler `chapter_write` với checkpoint/resume/hủy; `progress_adapter.py` gộp `token.delta`.
- [ ] `commit.py` idempotent, dùng F09 `commit_chapter_state`; test kill giữa transaction.
- [ ] Bước sau commit + áp đề xuất dàn ý theo chế độ.
- [ ] API continuity/handoff/plan/seam/metrics/outline proposals/resume actions.
- [ ] Ràng buộc accept-with-note (chặn khi validator xác định lỗi).
- [ ] `chapter_measurements` + endpoint chỉ số cho T05–T08, T14.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | `entry_gate`: từng điều kiện fail trả đúng mã | `be/tests/unit/longform/test_gate.py` |
| unit | Ánh xạ `PipelineResult` → trạng thái job + continuity | `be/tests/unit/longform/test_result_mapping.py` |
| integration | Chương mock thành công: một transaction, đủ 10 thành phần, event đúng thứ tự | `be/tests/integration/longform/test_write_chapter_success.py` |
| integration | Seam fail 3 lần → `waiting_user` + `blocked_needs_resync`, không có revision mới | `be/tests/integration/longform/test_write_chapter_blocked.py` |
| integration | Kill process ở từng bước → resume, không trùng chương, không commit thiếu state | `be/tests/integration/longform/test_write_chapter_resume.py` |
| integration | Accept kèm ghi chú bị chặn khi validator xác định lỗi | `be/tests/integration/longform/test_accept_with_note.py` |
| integration | Sửa handoff → plan N+1 lập lại (hash đổi) | `be/tests/integration/longform/test_handoff_edit_replan.py` |
| integration | Xét lại dàn ý ở chương 10: `auto` áp phần không khóa; `review_each` tạo pending | `be/tests/integration/longform/test_outline_review.py` |
| contract | Payload event F10 khớp envelope Plan §23.1.C | `be/tests/contract/test_events_chapter_pipeline.py` |

Luồng: [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md), [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md), [T15](../../tests/flows/T15-loi-provider.md), [T07](../../tests/flows/T07-auto-write-mot-truyen.md).

## Tên mới đề xuất

- Bảng `chapter_measurements`, `outline_proposals`; cột `chapter_handoffs.handoff_revision`, `tail_paragraph_ids`, `tail_tokens`, `tail_counted_for_model`, `source`, `note`, `is_current`; `chapter_plans.inputs`, `plan_json`, `status`, `edited_by_user`; `works.allow_early_ending`, `writing_config` (và `continuity_chapter_no`, `continuity_reason` nếu F05/F11 chưa chốt); `chapter_candidates.round`, `continuations`, `delta_json`, `summary_json`, `seam_json`, `base_state_id`, `plan_id`; `findings.round`, `needs_confirmation`, `override_note`.
- API: `GET /v1/works/{id}/continuity/metrics`, `GET|PUT /v1/chapters/{id}/plan`, `GET /v1/chapters/{id}/seam`, `GET /v1/works/{id}/outline-proposals`, `POST /v1/outline-proposals/{id}/apply|reject`; body `action` cho `POST /v1/jobs/{id}/resume`; `note`, `override_finding_ids` cho accept.
- Lý do chờ/chặn: `PREV_CHAPTER_DIRTY`, `REPAIR_EXHAUSTED`, `STATE_INVALID`, `OUTLINE_REVIEW`.
- Module `modules/longform/chapter_write/`, `PinnedConfig`, `GateResult`.
