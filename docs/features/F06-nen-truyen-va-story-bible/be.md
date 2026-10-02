# F06 — Backend

## Module và file

```text
be/src/writestory_be/modules/longform/
  router_foundation.py   GET /v1/works/{id}/foundation, PUT /v1/works/{id}/foundation/{section}
  router_bible.py        CRUD characters | address-rules | story-events | hooks | facts | timeline; bible summary/revisions
  schemas.py             FoundationView, *In/*Out cho từng thực thể, BibleSummary, BibleRevisionStatus
  service_foundation.py  Tạo job foundation, ghép candidate theo phần, accept theo giai đoạn, readiness
  service_bible.py       CRUD + đánh dấu bible_dirty + pin_for_chapter()
  domain.py              Thuần: validate_event_dag(), check_address_overlap(), hook_overdue(), alias_conflicts(),
                         map_temp_ids(), build_layer2_snapshot()
  state_seed.py          rebuild_state_seed(): dựng StoryState chương 0 từ bảng (schema F09)
be/src/writestory_be/jobs/handlers/foundation.py   Handler job type "foundation": gọi ai.workflows.longform.foundation
be/src/writestory_be/infrastructure/db/models/longform.py
be/migrations/versions/<rev>_f06_foundation_bible.py
```

`FoundationReadinessPort` (khai báo ở F05) do `service_foundation` triển khai. `pin_for_chapter()` được F10 gọi khi job chương bắt đầu.

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `works` (thêm cột) | `foundation_status` (`none`\|`generating`\|`candidate`\|`accepted`\|`failed`) = `none`, `foundation_stages` JSON `{}` (`{frame, address_rules, event_outline}` → `accepted_at`), `bible_dirty` BOOL=0, `bible_revision_no` INT=0 | — | Backfill: tác phẩm cũ (nếu có) = `none` |
| `outlines` | `id`, `work_id` FK, `kind` (`story_frame`\|`volume_map`\|`opening`), `content_json`, `content_md`, `source` (`ai`\|`user`), `job_id` NULL, `revision`, `updated_at` | UNIQUE(`work_id`,`kind`) | Plan §5 "outlines". `opening` = quan hệ ban đầu, địa điểm, tình huống mở đầu (dùng cho state seed) |
| `author_controls` | `id`, `work_id`, `kind` (`book_rules`\|`author_intent`\|`current_focus`), `content_md`, `content_json` NULL, `revision`, `updated_at` | UNIQUE(`work_id`,`kind`) | Plan §18; book rules có cả văn bản đọc được và schema (EDT06) |
| `characters` | `id`, `work_id`, `name`, `name_search`, `aliases` JSON `[{text, kind: han_viet\|thuan_viet\|nickname\|title\|unaccented, search, shared}]`, `allow_mixed_naming` BOOL=0, `role_kind` (`protagonist`\|`deuteragonist`\|`antagonist`\|`supporting`\|`minor`), `is_main` BOOL, `description`, `personality`, `goals`, `background`, `first_appearance_chapter` NULL, `archived` BOOL=0, `source`, `revision`, `created_at`, `updated_at` | INDEX(`work_id`,`name_search`) | Plan §5 "characters"; `aliases[].search` = fold (NFC, bỏ dấu, `đ→d`) cho kiểm tra tên riêng (Plan §6.6) |
| `address_rules` | `id`, `work_id`, `speaker_id` FK characters, `listener_id` FK characters, `self_term`, `address_term`, `from_chapter`=1, `until_chapter` NULL, `phase_label` NULL, `change_reason` NULL, `note` NULL, `source`, `revision`, `updated_at` | CHECK `speaker_id <> listener_id`; INDEX(`work_id`,`speaker_id`,`listener_id`) | Plan §5 "address_rules" (người nói → người nghe → từ xưng/gọi theo giai đoạn) |
| `story_events` | `id`, `work_id`, `seq`, `summary`, `detail` NULL, `planned_chapter`, `status` (`planned`\|`done`\|`moved`\|`dropped`), `depends_on` JSON `[]`, `storyline` NULL, `volume_no` NULL, `locked` BOOL=0, `done_in_chapter` NULL, `moved_from_chapter` NULL, `source`, `revision`, `updated_at` | INDEX(`work_id`,`planned_chapter`), INDEX(`work_id`,`status`) | Plan §5, Review §4.6. `locked` = sự kiện tác giả khóa (Plan §23.3 #6) |
| `hooks` | `id`, `work_id`, `title`, `description`, `status` (`open`\|`progressing`\|`deferred`\|`resolved`\|`superseded`), `opened_at_chapter`, `due_by_chapter` NULL, `payoff_plan`, `priority` (1–3, 1 cao nhất), `last_advanced_chapter` NULL, `resolved_at_chapter` NULL, `related_event_id` NULL, `source`, `revision`, `updated_at` | INDEX(`work_id`,`status`,`due_by_chapter`) | Plan §5 (`due_by_chapter`, `payoff_plan`, `priority`), MEM02 |
| `facts` | `id`, `work_id`, `subject`, `predicate`, `object`, `valid_from_chapter`, `valid_until_chapter` NULL, `source_chapter` NULL, `evidence` JSON NULL (`{chapter_no, paragraph_id, quote}`), `source` (`ai`\|`user`\|`settle`), `revision`, `updated_at` | INDEX(`work_id`,`subject`) | MEM01 |
| `timeline` | `id`, `work_id`, `chapter_no`, `story_time_label`, `story_time_order` REAL, `description`, `is_flashback` BOOL=0, `source`, `revision`, `updated_at` | INDEX(`work_id`,`chapter_no`) | Plan §5 "timeline" |
| `bible_revisions` | `id`, `work_id`, `revision_no`, `snapshot_json`, `snapshot_hash`, `changed_entities` JSON, `created_at` | UNIQUE(`work_id`,`revision_no`) | Bản chụp lớp 2 prompt (Plan §6.4) mà job chương ghim |

`story_states` (snapshot) thuộc F09; F06 chỉ ghi dòng `chapter_no = 0` qua `StateRepository` của F09. Mọi văn bản lưu NFC.

## API

Mã HTTP giả định (F01): `VALIDATION` 422, `NOT_FOUND` 404, `REVISION_CONFLICT` 409. Mọi PATCH/DELETE yêu cầu `expected_revision` của dòng.

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| POST | `/v1/jobs` | `{type: "foundation", work_id, idempotency_key, input: {stage: frame\|address_rules\|event_outline, parts?: [str], base_job_id?, instruction?}}` | `202 {job_id}` (trùng job đang chạy cùng `work_id`+`stage` → trả job đó) | `VALIDATION` (`detail.missing=["frame"]` khi chưa nhận frame), `VAULT_LOCKED` → job `waiting_slot` (không lỗi HTTP) |
| POST | `/v1/jobs/{id}/accept` | `{expected_work_revision, output: FrameOutput\|AddressRulesOutput\|EventOutlineOutput}` (bản tác giả đã sửa) | `{work: WorkOut, foundation_status, state_seed_rebuilt: bool}` | `REVISION_CONFLICT`, `VALIDATION` (`detail.errors[]` theo đường dẫn JSON), `WORK_BLOCKED` (đã có chương committed – dùng CRUD) |
| POST | `/v1/jobs/{id}/resume`, `/cancel` | — | Plan §7 (F12) | F12 |
| GET | `/v1/works/{id}/foundation` | — | `{foundation_status, stages: {frame\|address_rules\|event_outline: {accepted_at, candidate?: {job_id, job_state, parts_done[], parts_missing[], output_partial}}}, outlines, author_controls}` | `NOT_FOUND` |
| PUT | `/v1/works/{id}/foundation/{section}` | `section ∈ story_frame\|volume_map\|book_rules\|author_intent\|current_focus`; `{expected_revision, content_md, content_json?}` | dòng đã cập nhật | `REVISION_CONFLICT`, `VALIDATION` |
| GET/POST | `/v1/works/{id}/characters` | GET `?include_archived=`; POST `CharacterIn` | list / `201` | `VALIDATION` (`detail.alias_conflicts`) |
| PATCH/DELETE | `/v1/works/{id}/characters/{character_id}` | PATCH `{expected_revision, …, allow_shared_alias?}` | dòng / `204` hoặc `200 {archived: true}` | `REVISION_CONFLICT`, `VALIDATION` |
| GET | `/v1/works/{id}/characters/{character_id}/history` | `?from_chapter=&to_chapter=` | `[{chapter_no?, kind: state_change\|author_edit, changes, bible_revision_no?}]` | `NOT_FOUND` |
| GET/POST, PATCH/DELETE `/{rule_id}` | `/v1/works/{id}/address-rules` | GET `?speaker_id=&listener_id=&chapter=` | list / dòng | `VALIDATION` (`detail.overlap_with`) |
| GET/POST, PATCH/DELETE `/{event_id}` | `/v1/works/{id}/story-events` | GET `?status=&from_chapter=&to_chapter=` | list (kèm `blocked_by` tính sẵn) | `VALIDATION` (`detail.cycle`, `detail.dependency_order`) |
| GET/POST, PATCH/DELETE `/{hook_id}` | `/v1/works/{id}/hooks` | GET `?status=&overdue=true` | list kèm `overdue`, `due_in` | `VALIDATION` |
| GET/POST, PATCH/DELETE `/{fact_id}` | `/v1/works/{id}/facts` | GET `?subject=&valid_at=N` | list | `VALIDATION` |
| GET/POST, PATCH/DELETE `/{entry_id}` | `/v1/works/{id}/timeline` | GET `?from_chapter=&to_chapter=` | list | `VALIDATION` |
| GET | `/v1/works/{id}/bible/summary` | — | `{characters, hooks_open, hooks_overdue, events: {planned, done, moved, dropped}, facts, latest_committed_chapter}` | `NOT_FOUND` |
| GET | `/v1/works/{id}/bible-revisions` | `?limit=` | `{bible_dirty, latest_revision_no, running_job_pinned_revision_no?, items: [{revision_no, changed_entities, created_at}]}` | `NOT_FOUND` |
| GET | `/v1/works/{id}/state?chapter=N` | — | `StoryState` (F09 triển khai) | `NOT_FOUND` (N chưa commit) |

## Logic xử lý

**Job foundation** (FL03):

1. `POST /v1/jobs` kiểm tra điều kiện giai đoạn (frame trước; address_rules/event_outline cần frame đã nhận), đặt `foundation_status=generating`, persist job (F12) với `input` + `ModelSelection` vai trò `planner` đã ghim (F04).
2. Handler dựng `FoundationInput` từ DB (brief, thể loại, style profile, `target_chapters`, phần đã nhận), đóng transaction đọc, gọi `ai.workflows.longform.foundation.run_stage()` với `ProgressSink` lưu checkpoint **theo phần** (`frame_core`, `cast`; `address_rules`; `events_v{n}`, `hooks`).
3. AI trả output đã validate schema; handler chạy `domain` kiểm tra xác định (DAG, chương trong khoảng, xưng hô tham chiếu nhân vật tồn tại, trùng bí danh) và gắn `warnings` vào candidate (không tự sửa).
4. Job → `waiting_user`, `foundation_status=candidate`. Lỗi/hủy → `failed`/`interrupted`, work vẫn `draft`, phần đã xong vẫn đọc được qua `GET /foundation` (`parts_done`).
5. "Tạo lại phần X": job mới với `parts=[X]`, `base_job_id`; handler lấy các phần khác từ checkpoint job cũ, chỉ gọi AI cho X.

**Accept** (`POST /v1/jobs/{id}/accept`, một transaction qua writer queue):

1. Kiểm `expected_work_revision`; chỉ cho khi work chưa có chương committed (sau đó sửa bằng CRUD).
2. Validate lại `output` (Pydantic + `domain`); lỗi → 422 kèm đường dẫn.
3. `map_temp_ids`: ánh xạ `temp_id` → ID thật. Giai đoạn `frame`: thay `outlines` (`story_frame`, `volume_map`, `opening`), `author_controls`, `characters` (`source=ai`; xóa nhân vật `source=ai` cũ của lần nhận trước nếu chưa có tham chiếu). `address_rules`: thay toàn bộ quy tắc `source=ai`, giữ quy tắc `source=user`. `event_outline`: thay `story_events` + `hooks` `source=ai` chưa bị tác giả sửa.
4. Cập nhật `foundation_stages[stage]`; đủ 3 giai đoạn → `foundation_status=accepted`.
5. `state_seed.rebuild_state_seed()`: StoryState chương 0 = `characters` (status `alive`, vị trí/điều kiện từ `opening`), `relationships` và `locations` từ `opening`, `hooks` (status, `due_by`), `events` (`planned`), `story_time` từ tình huống mở đầu. Snapshot chương 0 được dựng lại ở mỗi lần accept khi chưa có chương committed; sau chương 1 committed thì bất biến.
6. Đặt `bible_dirty=1`.

**Story Bible và revision** (Plan §6.4, UI §5.4):

- Mọi ghi vào bảng thuộc lớp 2 (`outlines` story_frame/volume_map, `author_controls` book_rules/author_intent, `characters`, `address_rules`, `style_profile` của F05) đặt `works.bible_dirty=1`. Không phát sinh revision ngay.
- `pin_for_chapter(work_id)` (F10 gọi đầu job chương): nếu `bible_dirty` hoặc chưa có revision → `build_layer2_snapshot()` (thứ tự ổn định, JSON sắp khóa) → nếu hash trùng revision cuối thì dùng lại, ngược lại INSERT `bible_revisions` (`changed_entities` = diff với bản trước) → `bible_dirty=0`. Trả `{revision_no, snapshot_json}` để job ghim. Job đang chạy giữ revision đã ghim → sửa trong lúc chạy chỉ áp từ chương kế tiếp.
- `story_events`, `hooks`, `facts`, `timeline`, `current_focus` là lớp 3: F10 đọc trạng thái hiện hành ở bước Load đầu mỗi chương, nên sửa cũng áp từ chương kế tiếp. Sửa tay `facts`/`hooks` được F09 gộp vào snapshot khi commit chương kế tiếp (snapshot cũ không bị sửa).

**Quy tắc kiểm tra** (`domain.py`):

- `validate_event_dag`: không chu trình (DFS); mọi `depends_on` tồn tại cùng work; `planned_chapter(dep) ≤ planned_chapter(event)`; `1 ≤ planned_chapter ≤ target_chapters`. Đổi `planned_chapter` của sự kiện `planned` có chương dự kiến ≤ chương committed mới nhất → tự đặt `status=moved`, `moved_from_chapter`.
- `check_address_overlap`: cùng (`speaker_id`,`listener_id`) không được có khoảng `[from_chapter, until_chapter]` chồng nhau; `self_term`/`address_term` không rỗng sau NFC.
- `alias_conflicts`: `search` của tên/bí danh trùng với nhân vật khác → lỗi trừ khi `allow_shared_alias` (đánh dấu `shared`).
- `hook_overdue`: `status ∉ {resolved, superseded}` và `due_by_chapter` khác NULL và `latest_committed_chapter ≥ due_by_chapter`. `due_in = due_by_chapter − latest_committed_chapter`.
- Xóa nhân vật: đã xuất hiện trong snapshot chương ≥ 1 → chỉ `archived=1`; ngược lại xóa và xóa `address_rules` liên quan.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `job.queued`, `job.state` | Tạo job foundation; đổi trạng thái (`running`, `waiting_user` = có candidate, `failed`, `interrupted`) | `{job_id, work_id, type: "foundation", stage, state}` |
| `job.step` | Xong một phần | `{job_id, stage, part, parts_done, parts_total}` |
| `usage.updated` | Sau mỗi lần gọi model | theo F14 |

Không thêm event mới cho CRUD Story Bible (FE tự invalidate sau mutation).

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Accept giai đoạn khi work đã có chương committed | Từ chối, hướng dẫn sửa qua Story Bible | `WORK_BLOCKED` |
| Accept bản đã sửa tạo chu trình sự kiện | 422 với `detail.cycle=[ids]` | `VALIDATION` |
| Quy tắc xưng hô tham chiếu nhân vật bị xóa trong bản sửa | 422 với đường dẫn | `VALIDATION` |
| Hai lần accept song song | `expected_work_revision` | `REVISION_CONFLICT` |
| `target_chapters` giảm làm sự kiện vượt khoảng | Cảnh báo ở `GET story-events` (`out_of_range`), không tự xóa | — |
| Hook `due_by_chapter < opened_at_chapter` | Từ chối | `VALIDATION` |
| `chapter` của `/state` lớn hơn chương committed mới nhất | 404 | `NOT_FOUND` |
| Job foundation bị cancel sau khi xong vài phần | Giữ checkpoint; candidate một phần không accept được (thiếu phần) | `VALIDATION` khi accept |

## Việc cần làm

- [ ] Migration các bảng + cột `works`.
- [ ] `domain.py` (DAG, overlap, alias, overdue, map temp id, snapshot lớp 2) – thuần, có test.
- [ ] Handler job `foundation` + checkpoint theo phần + "tạo lại phần".
- [ ] Accept theo giai đoạn + `rebuild_state_seed` (theo schema F09).
- [ ] CRUD 6 nhóm thực thể + `history`, `bible/summary`, `bible-revisions`.
- [ ] `pin_for_chapter()` cho F10; đặt `bible_dirty` trong mọi ghi lớp 2 (kể cả style profile của F05).
- [ ] `FoundationReadinessPort` cho F05 (foundation `accepted`, có snapshot chương 0, ≥ 1 sự kiện).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | DAG: chu trình, phụ thuộc thiếu, thứ tự chương, `moved` tự động | `be/tests/unit/longform/test_event_dag.py` |
| unit | Xưng hô chồng khoảng; bí danh trùng sau fold ("Lâm Phong"/"Lam Phong") | `be/tests/unit/longform/test_address_alias.py` |
| unit | `hook_overdue`, `due_in` ở biên | `be/tests/unit/longform/test_hook_overdue.py` |
| unit | `build_layer2_snapshot` ổn định (cùng dữ liệu → cùng hash) | `be/tests/unit/longform/test_layer2_snapshot.py` |
| integration | Job foundation mock provider 3 giai đoạn → accept → state seed chương 0 → work ready | `be/tests/integration/longform/test_foundation_flow.py` |
| integration | Kill giữa phần `cast` → resume chỉ gọi AI cho phần thiếu (đếm lời gọi mock) | `be/tests/integration/longform/test_foundation_recover.py` |
| integration | Sửa nhân vật khi job chương đang chạy → job giữ revision cũ, job sau dùng revision mới | `be/tests/integration/longform/test_bible_pin.py` |

Luồng: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md), [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md).

## Tên mới đề xuất

- Bảng: `bible_revisions` (`revision_no`, `snapshot_json`, `snapshot_hash`, `changed_entities`).
- Cột `works`: `foundation_status`, `foundation_stages`, `bible_dirty`, `bible_revision_no`.
- Cột/giá trị: `outlines.kind` (`story_frame|volume_map|opening`), `outlines.content_json|content_md|source|job_id`; `author_controls.kind` (`book_rules|author_intent|current_focus`); `characters.name_search|aliases[].kind|aliases[].search|aliases[].shared|allow_mixed_naming|role_kind|is_main|archived|first_appearance_chapter`; `address_rules.speaker_id|listener_id|self_term|address_term|from_chapter|until_chapter|phase_label|change_reason`; `story_events.seq|detail|storyline|volume_no|locked|done_in_chapter|moved_from_chapter`; `hooks.title|opened_at_chapter|last_advanced_chapter|resolved_at_chapter|related_event_id`; `facts.valid_from_chapter|valid_until_chapter|source_chapter|evidence`; `timeline.story_time_label|story_time_order|is_flashback`; cột chung `source` (`ai|user|settle`), `revision`.
- API: `GET /v1/works/{id}/foundation`, `PUT /v1/works/{id}/foundation/{section}`, đường dẫn phần tử `/v1/works/{id}/<collection>/{item_id}`, `GET /v1/works/{id}/characters/{character_id}/history`, `GET /v1/works/{id}/bible/summary`, `GET /v1/works/{id}/bible-revisions`; job `type: "foundation"` với `input.stage|parts|base_job_id`.
- Code: `pin_for_chapter`, `rebuild_state_seed`, `build_layer2_snapshot`, `validate_event_dag`, `check_address_overlap`, `alias_conflicts`, `hook_overdue`, `map_temp_ids`, `jobs/handlers/foundation.py`.
