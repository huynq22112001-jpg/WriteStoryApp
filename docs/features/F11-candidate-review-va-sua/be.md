# F11 — Backend

## Module và file

```text
be/src/writestory_be/modules/chapters/
  router.py        candidates, accept/reject, cấu trúc chương (insert/delete/reorder)
  schemas.py       AcceptRequest, ConflictDetail, ReviseScope, ChapterStructureRequest
  service.py       accept_candidate, reject_candidate, create_revise_job, structure ops
  domain.py        merge 3 bên theo paragraph_id, kiểm tra phạm vi, quy tắc trạng thái candidate
  paragraphs.py    apply_paragraph_ops (dùng chung với F10 repair; §23.1.B)
be/src/writestory_be/modules/longform/
  findings.py      tạo/gộp/resolve/dismiss findings, xác minh trích dẫn
  continuity.py    mark_stale(K), mark_blocked, clear; tính phạm vi resync
  resync_job.py    handler job resync K..N
  revise_job.py    handler job revise (gọi AI revise, lưu candidate)
  review_job.py    handler job review lại chương đã commit (tác vụ phụ, không khóa)
  router.py        /findings, /continuity, /resync
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `chapter_candidates` | `id`, `work_id`, `chapter_id`, `chapter_no`, `job_id`, `kind` (`draft`/`repair`/`revise`), `mode` (`spot_fix`/`polish`/`rewrite`/`rework`, null với draft), `base_revision_id` (null nếu chương chưa commit), `scope` JSON, `author_instruction`, `content_json` (Tiptap), `plain_text`, `ops` JSON, `status`, `check_summary` JSON, `proposed_delta` JSON, `length_syllables`, `accepted_paragraph_ids` JSON, `accepted_revision_id`, `superseded_by`, `created_at`, `ready_at`, `decided_at`, `expires_at` | idx (`chapter_id`, `status`), idx (`job_id`), idx (`status`, `expires_at`) | §5, §23.2 #1. `check_summary` = {blocker, major, minor, seam_ok, length_ok} |
| `findings` | `id`, `work_id`, `chapter_id`, `chapter_no`, `revision_id`, `candidate_id`, `job_id`, `source` (`check`/`validator`/`seam`/`review`/`user`), `kind` (`fact`/`timeline`/`name`/`address`/`seam`/`pov`/`slop`/`craft`), `severity` (`blocker`/`major`/`minor`), `message`, `evidence` JSON [{`paragraph_id`, `quote`}], `evidence_status` (`verified`/`unavailable`), `suggestion`, `refs` JSON (fact/hook/character id), `fingerprint`, `status` (`open`/`resolved`/`dismissed`), `resolution_note`, `resolved_by` (`user`/`revise`/`recheck`), `created_at`, `resolved_at` | idx (`work_id`, `status`, `severity`), idx (`chapter_id`, `status`), unique (`candidate_id`/`revision_id`, `fingerprint`) | §5, §23.2 #14 |
| `works` (thêm cột) | `continuity_status` (`ok`/`blocked_needs_resync`/`stale_from`), `continuity_chapter_no`, `continuity_reason`, `continuity_updated_at` | — | Biểu diễn `stale_from(K)` của Plan §4.3 |
| `chapters` (thêm cột) | `deleted_at` (trash), `structure_version` | — | Soft-delete cho EDT09 |
| `story_states`, `chapter_handoffs` (thêm cột) | `source_revision_id`, `superseded_at` | idx (`work_id`, `chapter_no`, `superseded_at`) | Resync ghi bản mới, giữ bản cũ để audit |

Migration: `be/migrations/versions/<rev>_f11_candidates_findings_continuity.py`. Backfill: `works.continuity_status = 'ok'` cho dữ liệu có sẵn; không cần di chuyển dữ liệu khác (R2 chưa có candidate cũ).

Trạng thái candidate (chỉ các chuyển hợp lệ, kiểm ở `domain.py`):

```text
streaming → ready | partial (cancel/crash/lỗi giữa stream) | superseded (vòng repair mới)
partial   → superseded | rejected
ready     → accepted | rejected | superseded (candidate khác cùng chương được nhận, hoặc base bị đổi khi "Tạm dừng để sửa")
accepted/rejected/superseded: kết thúc, không đổi nữa
```

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/chapters/{id}/candidates?status=` | — | `[{id, kind, mode, status, base_revision_id, check_summary, length_syllables, created_at}]` | `NOT_FOUND` |
| GET | `/v1/candidates/{id}` | — | candidate + `paragraphs[{paragraph_id, text, op}]` + `base_paragraphs[]` | `NOT_FOUND` |
| POST | `/v1/candidates/{id}/accept` | `{expected_revision_id, paragraph_ids?, resolutions?: {pid: {take: "candidate"\|"current"\|"manual", text?}}, note?, dismiss_finding_ids?}` | `{chapter_id, revision_id, candidate_status, continuity: {status, chapter_no}, followup_job_id?}` | `REVISION_CONFLICT` 409, `CANDIDATE_NOT_READY` 409, `CANDIDATE_CLOSED` 409, `CHAPTER_IS_BASE` 409, `WORK_BLOCKED` 409, `VALIDATION` 422 |
| POST | `/v1/candidates/{id}/reject` | `{reason?}` | `{status: "rejected"}` | `CANDIDATE_CLOSED` |
| POST | `/v1/jobs/{id}/accept` | như accept | như accept | Alias Plan §7: nhận candidate `ready` mới nhất của job |
| POST | `/v1/jobs` (`type: "revise"`) | `{type, work_id, chapter_id, base_revision_id, mode, scope, instruction, finding_ids?, idempotency_key}` | 202 `{job_id, status, queue_position, base_revision_id}` | `REVISION_CONFLICT`, `WORK_BLOCKED`, `VALIDATION` |
| POST | `/v1/jobs` (`type: "review"`) | `{type, work_id, chapter_id, revision_id, idempotency_key}` | 202 `{job_id}` | `REVISION_CONFLICT` |
| GET | `/v1/works/{id}/findings?status=&chapter=&severity=&source=&cursor=` | — | `{items[], next_cursor}` | — |
| POST | `/v1/chapters/{id}/findings` | `{kind, severity, message, evidence[]}` (nguồn `user`) | finding | `VALIDATION` |
| POST | `/v1/findings/{id}/resolve` | `{note?}` | finding | `NOT_FOUND` |
| POST | `/v1/findings/{id}/dismiss` | `{note}` (bắt buộc với `blocker`) | finding | `VALIDATION` |
| GET | `/v1/works/{id}/continuity` | — | `{status, chapter_no, reason, latest_handoff, open_blockers, resync_job?}` | — |
| POST | `/v1/works/{id}/resync` | `{from_chapter_no, to_chapter_no?, dry_run?}` | 202 `{job_id}` hoặc (`dry_run`) `{range, estimate}` | `STATE_SNAPSHOT_MISSING`, `CHAPTER_EMPTY`, `WORK_RUNNING`, `VALIDATION` |
| POST | `/v1/works/{id}/continuity/acknowledge` | `{from_chapter_no, confirm: true, note}` | `{status: "ok"}` | `VALIDATION` (Plan §6.2 "bỏ qua có xác nhận") |
| POST | `/v1/works/{id}/chapters` | `{after_chapter_no, title}` | chapter | `WORK_RUNNING` |
| DELETE | `/v1/chapters/{id}?expected_revision_id=` | — | `{deleted, continuity}` | `WORK_RUNNING`, `REVISION_CONFLICT` |
| POST | `/v1/works/{id}/chapters/reorder` | `{order: [chapter_id], expected_structure_version}` | `{structure_version, continuity}` | `WORK_RUNNING`, `REVISION_CONFLICT` |
| POST | `/v1/works/{id}/rollback` | `{from_chapter_no, confirm}` | 202 `{job_id}` | R3 (EDT13); MVP trả 501 |

Chi tiết `409 REVISION_CONFLICT` của accept:

```text
detail: {
  current_revision_id, candidate_base_revision_id,
  conflicts: [{paragraph_id, kind: both_modified | deleted_in_current | anchor_missing,
               base_text, current_text, candidate_text}],
  clean_paragraph_ids: [...]          # áp được không xung đột
}
action: "resolve_conflict"
```

## Logic xử lý

**Accept candidate** (`chapters/service.py::accept_candidate`):

1. Đọc candidate; `status != ready` → `CANDIDATE_NOT_READY`/`CANDIDATE_CLOSED`. Nếu chương là nền của job `write` đang chạy (chương N-1 khi viết N) → `CHAPTER_IS_BASE` (Plan §23.2 #3).
2. `chapter.current_revision_id != expected_revision_id` → 409 (client cũ). FE phải flush autosave trước khi gửi.
3. Working copy khác revision hiện tại → tạo revision `source=manual`, `reason=before_ai` (Plan §23.2 #2); revision đó thành `current`.
4. Merge 3 bên theo đoạn: `base = candidate.base_revision`, `current`, `ours = ops của candidate` lọc theo `paragraph_ids` (nếu có). Với mỗi op: đoạn không đổi giữa base và current → áp; đổi ở cả hai → conflict trừ khi có `resolutions[pid]`; `insert_after` mà anchor bị xóa ở current → `anchor_missing`.
5. Còn conflict → 409 kèm detail (revision bước 3 vẫn giữ, không mất dữ liệu).
6. Transaction (writer queue): revision mới `source=ai_accept` + `candidate_id`; con trỏ chương; candidate `accepted` + `accepted_paragraph_ids`; các candidate `ready` khác của chương → `superseded`; findings có `finding_ids` được revise nhắm tới và đoạn neo đã đổi → `resolved`, `resolved_by=revise`; FTS chương; `job_events`.
7. Hệ quả liền mạch (`continuity.py`), trong cùng transaction:
   - Candidate `draft` của chương chưa commit (chế độ `review_each`/`waiting_user`) → gọi `commit_chapter` của F10 với `proposed_delta`; nếu còn blocker chưa dismiss → `WORK_BLOCKED`.
   - Chương là chương committed mới nhất N → `stale_from(N)` + enqueue job `resync` N..N (settle lại + handoff(N) mới); trả `followup_job_id`.
   - Chương K < N → `stale_from(min(hiện có, K))`; auto-write của truyện dừng sau chương đang chạy (F12 đọc `continuity_status`).

**Revise** (job `revise`, Plan §6.3, FL06): request tạo revision `before_ai` nếu working copy bẩn → ghim `base_revision_id`; job vào hàng đợi truyện (job ghi theo Plan §4.2). Handler: dựng `ReviseInput` (ai.md) → stream candidate `kind=revise` → host áp ops, kiểm tra: op chỉ trên đoạn `editable`, đoạn ngoài phạm vi giống hệt base, vùng chọn trong một đoạn chỉ thay đúng `[start, end)`; chạy kiểm tra xác định (gói `vi`) tạo findings `source=check` gắn candidate → `ready`. Chương chưa commit đang `waiting_user`: candidate revise đi tiếp pipeline F10 từ bước Check.

**Resync** (job `resync`, Plan §6.2): cần `story_states(K-1)` còn hiệu lực (không có → `STATE_SNAPSHOT_MISSING`); mọi chương K..N phải có nội dung (`CHAPTER_EMPTY`).

```text
state = snapshot(K-1); handoff = handoff(K-1)
for k in K..N (theo chapter_no hiện tại):
    text = current_revision(k)                   # không viết lại văn bản
    delta, ending = AI.resettle(text, state, handoff)
    validate(delta)  ; seam(text.opening, handoff.ending_state) ; review-only
    if blocker chưa dismiss: findings + continuity=blocked_needs_resync(k); job → waiting_user; return
    commit(k): story_states(k) mới, superseded_at cho bản cũ, handoff(k), summary(k),
               facts/hooks/timeline projection, FTS; continuity = stale_from(k+1) hoặc ok khi k=N
    checkpoint(k); state, handoff = new
```

Mỗi chương một transaction ngắn; resume từ checkpoint `k+1`.

**Cấu trúc chương** (Plan §23.2 #4): từ chối `WORK_RUNNING` khi truyện có job ghi `running`/`waiting_slot` hoặc auto-write `active`. Khi được phép:

| Thao tác | Kết quả |
|---|---|
| Chèn sau chương J | Chương rỗng tại J+1, đánh số lại sau đó; `stale_from(J+1)` |
| Xóa chương mới nhất N | Confirm; `deleted_at`; snapshot/handoff N `superseded_at`; FTS xóa; tóm tắt N bỏ; continuity giữ nguyên (EDT09) |
| Xóa chương K < N | `deleted_at`; đánh số lại; `stale_from(K)` |
| Đổi thứ tự | K = vị trí nhỏ nhất thay đổi; `stale_from(K)` |

**Rework vs rollback/regenerate** (FL07): `rework` = revise cả chương, giữ chương sau, không động vào state cho tới khi accept. `rollback` (R3) = kiểm tra snapshot N-1 → confirm → archive chương N..cuối vào lịch sử (không xóa) → khôi phục state N-1 → enqueue `write` N. Hai action có job type khác nhau, không dùng chung endpoint.

Quy tắc transaction: không giữ transaction trong lúc gọi AI; mọi ghi qua writer queue F02; accept, resync từng chương và thao tác cấu trúc mỗi cái một transaction.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `candidate.ready` | Candidate chuyển `ready` | `{candidate_id, chapter_id, kind, check_summary}` |
| `candidate.updated` | accepted/rejected/superseded/partial | `{candidate_id, status}` |
| `finding.added` | Finding mới | `{finding_id, chapter_no, severity, kind}` |
| `finding.updated` | resolve/dismiss | `{finding_id, status}` |
| `work.continuity` | Đổi `continuity_status` | `{status, chapter_no, reason}` |
| `chapter.committed` | Accept/resync commit | `{chapter_id, revision_id, source}` |
| `job.step` | Tiến độ resync | `{stage: "resettle", chapter_no, done, total}` |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Hai tab nhận cùng candidate | Lần hai thấy `accepted` | `CANDIDATE_CLOSED` |
| Accept candidate khi working copy chưa flush | BE snapshot working copy trước (bước 3) rồi merge | — |
| AI trả op trên đoạn ngoài phạm vi | Bỏ op, ghi trace, finding `craft/minor` "AI vượt phạm vi" | — |
| Review job trả quote không có trong đoạn | `evidence_status = unavailable`, không xóa finding | — |
| Resync gặp chương rỗng (chèn) | Dừng trước khi chạy | `CHAPTER_EMPTY` |
| Sửa chương K khi đã `stale_from(J)` | `stale_from(min(J, K))` | — |
| Sửa chương khi `blocked_needs_resync` tại B | K < B → `stale_from(K)` thay thế (bao trùm B); K > B → giữ blocked | — |
| Dismiss blocker không ghi chú | Từ chối | `VALIDATION` |
| Cancel job revise giữa stream | Candidate `partial`, không thể accept | — |

## Việc cần làm

- [ ] Migration bảng/cột ở trên; enum kiểm bằng CHECK constraint.
- [ ] `domain.py`: state machine candidate + merge 3 bên thuần (không I/O).
- [ ] `paragraphs.py`: `apply_paragraph_ops` + kiểm tra phạm vi, sinh `paragraph_id` mới cho đoạn chèn.
- [x] Accept/reject API + alias `/v1/jobs/{id}/accept`; xung đột trả dữ liệu base/current/candidate.
- [ ] Hoàn thiện merge từng đoạn/resolution, insert-anchor và state machine thuần trong `domain.py`.
- [x] API findings list/resolve/dismiss/user-create; finding mới có fingerprint và event, finding xác định không dismiss được.
- [ ] Xác minh quote NFC và hoàn thiện fingerprint gộp trùng cho mọi nguồn.
- [x] `continuity.py` + `/continuity`, `/resync` dry-run và cập nhật stale/block state.
- [ ] Thêm `/continuity/acknowledge` và kiểm thử T10 tuần tự/crash.
- [x] Handler revise/resync theo executor port và khôi phục job bị interrupted.
- [ ] Đăng ký executor P221 mặc định, job review và tích hợp runner F12.
- [ ] Insert/delete/reorder + kiểm tra `WORK_RUNNING`.
- [ ] Dọn candidate `rejected`/`superseded`/`partial` sau 30 ngày (`expires_at`) qua cleanup F14.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Merge 3 bên: không xung đột, both_modified, anchor_missing, resolutions | `be/tests/unit/chapters/test_merge.py` |
| unit | State machine candidate, chuyển cấm | `be/tests/unit/chapters/test_candidate_state.py` |
| unit | `apply_paragraph_ops` giữ đoạn ngoài phạm vi, vùng chọn trong đoạn | `be/tests/unit/chapters/test_paragraph_ops.py` |
| unit | Quy tắc `stale_from` min, blocked + stale | `be/tests/unit/longform/test_continuity.py` |
| integration | Accept từng đoạn + 409 khi sửa tay song song (T11) | `be/tests/integration/test_candidate_accept.py` |
| integration | Resync K..N với mock provider, crash giữa chừng rồi resume (T10) | `be/tests/integration/test_resync.py` |
| integration | Chèn/xóa/đổi thứ tự khi đang chạy → `WORK_RUNNING` | `be/tests/integration/test_chapter_structure.py` |

## Tên mới đề xuất

- Bảng/cột: `chapter_candidates.{kind, mode, scope, ops, check_summary, proposed_delta, accepted_paragraph_ids, accepted_revision_id, superseded_by, expires_at}`; `findings.{evidence_status, refs, fingerprint, resolution_note, resolved_by}`; `works.{continuity_status, continuity_chapter_no, continuity_reason, continuity_updated_at}` (giá trị `stale_from` + số chương thay cho chuỗi `stale_from(K)`); `chapters.{deleted_at, structure_version}`; `story_states.superseded_at`, `story_states.source_revision_id`, `chapter_handoffs.superseded_at`.
- API: `GET /v1/candidates/{id}`, `POST /v1/chapters/{id}/findings`, `POST /v1/works/{id}/continuity/acknowledge`, `POST /v1/works/{id}/rollback` (R3), tham số `dry_run` của resync.
- Mã lỗi: `CANDIDATE_NOT_READY`, `CANDIDATE_CLOSED`, `CHAPTER_IS_BASE`, `WORK_RUNNING`, `STATE_SNAPSHOT_MISSING`, `CHAPTER_EMPTY`, `NOT_FOUND` (nếu F01 chưa có).
- Event: `candidate.updated`, `finding.updated`.
- Job type: `resync`, `review`, `revise` (đã có trong §7), `rollback` (R3). Mode revise: `spot_fix`, `polish`, `rewrite`, `rework`.
- File: `modules/chapters/paragraphs.py`, `modules/longform/{findings,continuity,resync_job,revise_job,review_job}.py`.
