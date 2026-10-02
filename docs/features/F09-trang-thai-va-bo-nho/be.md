# F09 — Backend

BE sở hữu dữ liệu chuẩn: snapshot, sổ cái, tóm tắt, index, trace. AI (ai.md) cung cấp contract Pydantic, reducer và validator thuần; BE gọi chúng rồi ghi trong transaction ngắn qua writer queue (Plan §4.2, Arch §5).

## Module và file

```text
be/src/writestory_be/modules/longform/
  state/router.py        /v1/works/{id}/state*, /summaries, /chapters/{id}/memory, CRUD facts|hooks|timeline (dịch sang delta)
  state/schemas.py       StoryStateDTO (sinh từ contract AI), StateMetaDTO, UserDeltaRequest, SummaryDTO, MemoryDTO
  state/service.py       get_state, apply_user_delta, pending deltas, diff/changes
  state/domain.py        Quy tắc nguồn delta (pipeline|user), stale khi sửa chương cũ
  state/projector.py     LedgerProjector: delta → facts/hooks/timeline/story_events/address_rules/characters/locations
  search/router.py       /v1/works/{id}/search, /search/rebuild
  search/projector.py    SearchProjector: index/unindex chương, fact, hook, summary, nhân vật
  traces/router.py       /v1/chapters/{id}/trace
  traces/service.py      Lưu/thu gọn trace theo chính sách dung lượng
be/src/writestory_be/infrastructure/
  db/models/longform_state.py   ORM: story_states, facts, hooks, timeline, summaries, context_traces, state_pending_deltas
  db/repositories/state_repo.py, summary_repo.py, trace_repo.py
  db/fts.py              (F02) tạo bảng FTS5, truy vấn bm25, snippet theo văn bản gốc
  ai/context_adapter.py  Triển khai ContextPort của AI (đọc snapshot/handoff/summaries/search/đoạn văn)
be/src/writestory_be/jobs/handlers/search_rebuild.py
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `story_states` | `id`, `work_id`, `chapter_no` (0 = seed), `revision_id` (chapter_revisions, NULL khi 0), `schema_version`, `state_json`, `state_hash` (sha256 JSON chuẩn hóa), `delta_json` (delta đã áp, để audit), `parent_state_id`, `source` (`seed`\|`pipeline`\|`user_edit`\|`resync`), `is_current`, `job_id`, `created_at` | UNIQUE (`work_id`,`chapter_no`) WHERE `is_current`=1; index (`work_id`,`chapter_no` DESC) | Nguồn chuẩn của "state sau chương N" (Plan §5, §23.1.A). Bản cũ giữ lại (`is_current=0`) để audit/rollback |
| `chapters` (F07) | F07 đã có `state_applied`; F09 thêm `state_id` | — | `state_applied=true` ⇔ `story_states` hiện hành của chương trỏ đúng `current_revision_id`. Dùng cho cổng F10 và chỉ số Plan §9 |
| `facts` (F06 tạo) | Cột F06: `subject`, `predicate`, `object`, `valid_from_chapter`, `valid_until_chapter`, `source_chapter`, `evidence` JSON, `source` (`ai`\|`user`\|`settle`). F09 thêm: `subject_ref` (`character:<id>`\|`location:<id>`\|NULL), `is_secret`, `status` (`active`\|`closed`\|`retracted`), `created_state_id`, `closed_state_id` | thêm index (`work_id`,`status`) | Sổ cái (MEM01). Projection của snapshot, ghi cùng transaction |
| `hooks` (F06 tạo) | Cột F06: `title`, `description`, `status`, `opened_at_chapter`, `due_by_chapter`, `payoff_plan`, `priority`, `last_advanced_chapter`, `resolved_at_chapter`, `related_event_id`, `source`. F09 thêm: `history` JSON `[{chapter_no, op, note, evidence}]` | — | MEM02 |
| `timeline` (F06 tạo) | Cột F06: `chapter_no`, `story_time_label`, `story_time_order`, `description`, `is_flashback`, `source`. F09 thêm: `evidence` JSON | — | Một dòng mỗi `time.advance` (`story_time_order` = `StoryTime.ordinal`) |
| `story_events` (F06 tạo) | F09 cập nhật `status`, `done_in_chapter`, `moved_from_chapter`, `planned_chapter` | — | Op `event.*`; `locked` do F06 định nghĩa |
| `address_rules` (F06 tạo) | F09 chèn luật mới khi `address.change`: đóng luật cũ `until_chapter=N-1`, luật mới `from_chapter=N`, `change_reason` từ op, `source='ai'` | — | |
| `characters` (F06 tạo) | F09 chèn dòng mới khi `character.add` (`source='ai'`, `first_appearance_chapter=N`) | — | Địa điểm (`location.add`) chỉ nằm trong `StoryState.locations` – MVP chưa có bảng `locations` (F06) |
| `summaries` | `id`, `work_id`, `level` (`chapter`\|`arc`\|`synopsis`), `chapter_no`, `arc_key`, `from_chapter`, `to_chapter`, `text`, `key_points` JSON, `token_estimate`, `source_hash`, `model_id`, `prompt_version`, `is_current`, `stale`, `pinned_by_user`, `job_id`, `created_at` | UNIQUE hiện hành theo (`work_id`,`level`,`chapter_no`) cho chương, (`work_id`,`level`,`arc_key`) cho arc, (`work_id`,`level`) cho synopsis | Plan §23.3 #1 |
| `context_traces` | `id`, `work_id`, `chapter_no`, `job_id`, `job_step_id`, `step`, `round`, `model_id`, `effort`, `prompt_versions` JSON, `budget_tokens`, `estimated_input_tokens`, `counted_input_tokens`, `actual_input_tokens`, `cache_read_tokens`, `cache_write_tokens`, `output_tokens`, `count_method` (`exact`\|`estimate`), `items` JSON, `notes` JSON, `size_bytes`, `compacted`, `created_at` | index (`work_id`,`chapter_no`,`created_at`), (`job_id`) | Tên theo Plan §18; `items` theo `TraceItem` (ai.md) |
| `state_pending_deltas` | `id`, `work_id`, `base_chapter_no`, `ops` JSON, `note`, `status` (`pending`\|`applied`\|`rejected`), `result` JSON, `created_at` | index (`work_id`,`status`) | Sửa state khi truyện đang viết: áp ở bước load của chương kế tiếp ("áp từ chương kế tiếp", UI §5.4) |
| `search_documents` + `search_fts` + `search_trigram` (F02 tạo) | F09 đăng ký indexer qua `register_search_indexer(source_type, fn)` cho `source_type` ∈ `chapter_paragraph`, `fact`, `hook`, `summary`, `character`, `location` | — | F02 sở hữu bảng, trigger, `bm25`, rebuild; F09 quyết định nội dung index và thời điểm ghi |

Migration: `be/migrations/versions/<rev>_longform_state.py`. Không có dữ liệu cũ. Snapshot chương 0 do F06 tạo khi nhận nền truyện (FL03 bước 4) qua `StateRepository` của F09.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/works/{id}/state?chapter=N` | N mặc định = chương committed mới nhất | `{meta: StateMetaDTO{state_id, chapter_no, source, state_hash, revision_id, is_latest, created_at}, state: StoryStateDTO}` | `VALIDATION` (N > mới nhất), 404 |
| GET | `/v1/works/{id}/state/changes?from=A&to=B&entity=` | `entity` dạng `character:<id>`, `hook:<id>`… (tùy chọn) | `[{chapter_no, op, target, before, after, evidence}]` dựng từ `delta_json` | `VALIDATION` |
| POST | `/v1/works/{id}/state/deltas` | `{expected_state_hash, chapter_no, ops: [StateOp], note}` | Áp ngay: `{state_id, state_hash, findings: []}`; đang có job viết: `202 {pending_delta_id}` | `REVISION_CONFLICT` (hash lệch), `VALIDATION` (luật V-xx, kèm danh sách), `WORK_BLOCKED` |
| CRUD | `/v1/works/{id}/facts`, `/hooks`, `/timeline` | Như Plan §7; ghi được dịch thành `StateOp` nguồn `user` rồi đi qua `/state/deltas` | DTO bản ghi | như trên |
| GET | `/v1/works/{id}/summaries?level=&from=&to=` | — | `[SummaryDTO]` | — |
| PUT | `/v1/summaries/{id}` | `{expected_source_hash, text, pinned_by_user}` | `SummaryDTO` | `REVISION_CONFLICT` |
| GET | `/v1/chapters/{id}/memory` | — | `{facts_active, hooks_due, hooks_open, changes_in_chapter, present_characters}` cho tab Nhớ | 404 |
| GET | `/v1/works/{id}/search?q=&kinds=&chapter_from=&chapter_to=&limit=20&cursor=` | `kinds` ⊂ `chapter,fact,hook,summary,character,location` | `{items:[{kind, source_id, chapter_no, paragraph_id, revision_id, title, snippet:{text, highlights:[[s,e]]}, score, matched_via:"fts"\|"trigram"}], next_cursor}` | `VALIDATION` (q rỗng/ > 200 ký tự) |
| POST | `/v1/works/{id}/search/rebuild` | `{idempotency_key}` | `202 {job_id}` | `WORK_BUSY_QUEUED` |
| GET | `/v1/chapters/{id}/trace?job_id=&step=` | mặc định job commit gần nhất của chương | `{traces: [ContextTraceDTO]}` | 404 |

## Logic xử lý

**Áp delta pipeline (gọi từ commit F10, cùng transaction):**

1. Đọc snapshot hiện hành N-1; so `delta.base_state_hash` (V02). Lệch → abort transaction, F10 chạy lại settle trên base mới.
2. `validate_delta(state, delta, paragraphs)` (ai.md) → có lỗi `error` → abort (không bao giờ commit thiếu state hợp lệ, Plan §6.2).
3. Cấp ID thật cho ID tạm (`new:fact:1` → ULID), thay trong delta.
4. `new_state = apply_delta(state, delta)`; tính `state_hash`; chèn `story_states` (`is_current=1`, `source=pipeline`), hạ `is_current` bản cũ cùng chương nếu có (resync).
5. `LedgerProjector.apply`: `facts` (add/close), `hooks` (status, `last_advanced_chapter`, `resolved_at_chapter`, `history`), `timeline`, `story_events`, `address_rules`, `characters` (`character.add`); `location.add` chỉ đổi snapshot.
6. `SearchProjector` (qua `fts.upsert_document`/`delete_document` của F02): xóa tài liệu `chapter_paragraph` của chương N cũ (nếu resync), thêm đoạn của revision mới, fact/hook/summary thay đổi, nhân vật/địa điểm mới (vào `search_trigram` qua trigger F02).
7. `chapters.state_applied=true`, `state_id`.

**Áp delta của người dùng (`/state/deltas`):**

1. Không có job ghi đang chạy: chỉ cho `chapter_no` = chương mới nhất → bước 1–7 như trên với `source=user_edit`, bằng chứng `{kind:"user"}` được chấp nhận. `chapter_no` < mới nhất → áp vào snapshot đó và đặt `work.continuity_status = stale_from(chapter_no+1)` (F11 resync).
2. Có job ghi đang chạy: lưu `state_pending_deltas` → bước load của chương kế tiếp (F10) gọi `apply_pending_deltas` trên state mới nhất; lỗi validator → `rejected` + finding cho tác giả, truyện `waiting_user`.

**Tóm tắt phân tầng (nhịp theo Plan §23.3 #1):**

| Mức | Khi nào tạo | Nằm ở |
|---|---|---|
| Chương | Bước `summarize_chapter` của F10, trước commit | Cùng transaction commit |
| Arc | (a) arc đóng: mọi `story_events` của arc `done`/`dropped` hoặc tới chương cuối dự kiến của arc → bản cuối; (b) arc chưa đóng nhưng ≥ `arc_summary_every` chương (mặc định 10, khoảng 10–20) kể từ lần trước → bản "đang chạy" (`arc_key` giữ nguyên, thay `is_current`). Truyện không có arc trong dàn ý: mỗi `arc_summary_every` chương là một arc tự động `auto-<k>` | Bước `summarize_hierarchy` sau commit, vẫn giữ khóa truyện, trước khi scheduler nhận chương N+1 |
| Synopsis | Sau mỗi bản arc cuối (và sau arc tự động) | Cùng bước `summarize_hierarchy` |

Lỗi ở `summarize_hierarchy` không chặn truyện: đánh `stale=true`, ghi finding `minor`, thử lại ở chương sau; Composer dùng thêm tóm tắt chương nếu ngân sách cho phép và ghi chú vào trace. Sửa chương K (stale) → đánh `stale` mọi tóm tắt chương ≥ K và arc/synopsis bao phủ K; resync tạo lại. Tóm tắt `pinned_by_user` không bị ghi đè tự động; khi nguồn đổi chỉ đánh `stale` để tác giả quyết định.

**Tìm kiếm:** dùng `build_match_query` + `bm25(search_fts, 5.0, 1.0)` của F02 (trọng số tiêu đề > thân), lọc `work_id`/`source_type`/khoảng chương; thêm `search_trigram` (nếu bật) khi query có term ≥ 3 ký tự và ít kết quả; trộn, khử trùng theo (`source_id`,`paragraph_id`). Snippet: `body_norm` cùng độ dài code point với `body` (F02) nên vị trí khớp dùng trực tiếp để tô sáng văn bản gốc có dấu.

**Trace:** F10 gửi `ContextTrace` sau mỗi bước có gọi model; lưu nguồn, lớp, token, mục bị loại, không lưu toàn văn (chỉ preview ≤ 200 ký tự). Prompt đầy đủ chỉ ghi khi bật log debug AI (Plan §23.2 #11). Thu gọn theo dung lượng tối đa (Plan §23.2 #10): bỏ preview của trace cũ, giữ ID/token (`compacted=1`).

**ContextPort (`context_adapter.py`):** `get_state`, `get_handoff`, `get_summaries(upto, k_recent)`, `search(query, kinds, before_chapter, limit)`, `get_paragraphs(chapter_no, ids | tail)`, `get_bible(bible_revision)`, `get_pending_deltas`. Mỗi kết quả kèm `source_revision`. Transaction đọc đóng trước khi AI gọi model (Arch §5).

Quy tắc transaction: mọi ghi state/sổ cái/FTS/tóm tắt chương của một chương nằm trong **một** transaction commit của F10; FTS5 cùng file DB nên cùng transaction được.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `job.step` | `summarize_hierarchy`, `search_rebuild` bắt đầu/xong | `{step, status, levels?: ["arc","synopsis"]}` |
| `finding.added` | Delta người dùng bị từ chối khi áp pending; tóm tắt lỗi | `{finding_id, kind, severity}` |
| `work.continuity` | Sửa state chương cũ → `stale_from(K)` | `{status, chapter_no}` |

Sửa state trực tiếp (không job) trả kết quả trong response; FE tự invalidate query.

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Hai cửa sổ cùng sửa state | So `expected_state_hash` | `REVISION_CONFLICT` |
| Delta người dùng vi phạm luật | Trả danh sách vi phạm V-xx theo op | `VALIDATION` |
| Sửa state khi truyện `blocked_needs_resync` | Cho phép (là cách gỡ chặn), không tự bỏ chặn; F10/F11 quyết định | — |
| `base_state_hash` lệch lúc commit (người dùng sửa state chen giữa) | Abort, F10 settle lại trên base mới | — (nội bộ) |
| Tóm tắt arc lỗi provider | `stale`, không chặn | — |
| FTS hỏng/thiếu dòng | `search/rebuild` dựng lại từ revision hiện hành (MEM09) | — |
| Truyện 200+ chương | Snapshot vẫn đầy đủ; đo kích thước ở T14 trước khi đổi chiến lược | — |
| Chương 1 | Dùng snapshot chương 0 (seed) | — |

## Việc cần làm

- [ ] ORM + migration `story_states`, `summaries`, `context_traces`, `state_pending_deltas` và cột bổ sung trên bảng F06/F07.
- [ ] `state_repo` (snapshot hiện hành, lịch sử), `LedgerProjector`, `SearchProjector` (đăng ký indexer với F02).
- [ ] Hàm commit dùng chung cho F10: `commit_chapter_state(uow, delta, paragraphs, summary)`.
- [ ] `/state`, `/state/changes`, `/state/deltas`, CRUD facts/hooks/timeline dịch sang op.
- [ ] Pending deltas + hàm `apply_pending_deltas` cho F10.
- [ ] `summaries` repo + API; quy tắc `stale`/`pinned_by_user`.
- [ ] Search API + snippet có dấu + rebuild job.
- [ ] `context_traces` repo, API, chính sách thu gọn.
- [ ] `context_adapter.py` triển khai `ContextPort`.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Ánh xạ vị trí tô sáng trên văn bản có dấu | `be/tests/unit/search/test_highlight.py` |
| unit | CRUD fact → `StateOp` đúng | `be/tests/unit/longform/test_crud_to_ops.py` |
| integration | Commit delta: snapshot + sổ cái + FTS cùng transaction; lỗi giữa chừng → không còn gì | `be/tests/integration/longform/test_state_commit_atomic.py` |
| integration | Bất biến sổ cái = snapshot trên truyện mẫu 20 chương | `be/tests/integration/longform/test_ledger_invariant.py` |
| integration | Delta người dùng khi job chạy → pending → áp ở chương sau | `be/tests/integration/longform/test_pending_deltas.py` |
| integration | Tìm `nguyen`, `duong`, `Đường`, tên riêng 3 ký tự qua trigram | `be/tests/integration/search/test_search_vi.py` |
| integration | Nhịp tóm tắt arc/synopsis và fallback khi lỗi | `be/tests/integration/longform/test_summary_cadence.py` |
| contract | OpenAPI `StoryStateDTO` khớp JSON Schema của AI | `be/tests/contract/test_state_schema.py` |

Luồng: [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md), [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md), [T10](../../tests/flows/T10-sua-tay-va-resync.md).

## Tên mới đề xuất

- Bảng `state_pending_deltas`; cột của `summaries` và `context_traces` (Plan chỉ có tên bảng).
- Cột `chapters.state_id`; `story_states.state_hash`, `delta_json`, `parent_state_id`, `source`, `is_current`; `facts.subject_ref`, `is_secret`, `status`, `created_state_id`, `closed_state_id`; `hooks.history`; `timeline.evidence`; `summaries.arc_key`, `key_points`, `source_hash`, `stale`, `pinned_by_user`.
- `source_type` cho `search_documents` (F02): `chapter_paragraph`, `fact`, `hook`, `summary`, `character`, `location`.
- API: `GET /v1/works/{id}/state/changes`, `POST /v1/works/{id}/state/deltas`, `GET /v1/works/{id}/summaries`, `PUT /v1/summaries/{id}`, `GET /v1/chapters/{id}/memory`, `POST /v1/works/{id}/search/rebuild`.
- Bước job `summarize_chapter`, `summarize_hierarchy`; job type `search_rebuild`; cấu hình `arc_summary_every`.
- Module `modules/longform/state|search|traces`, `LedgerProjector`, `SearchProjector`.
