# F07 — Backend

## Module và file

```text
be/src/writestory_be/modules/chapters/
  router.py        /v1/works/{id}/chapters*, /v1/chapters/{id}*, working-copy, snapshot, revisions, diff, restore
  schemas.py       ChapterOut, ChapterListItem, WorkingCopyIn/Out, SnapshotIn, RevisionOut, RevisionMeta, DiffOut, EditLock
  service.py       save_working_copy, snapshot, snapshot_if_dirty, replace_content, restore, create/delete/reorder
  domain.py        Thuần: project_doc() → paragraphs/plain_text/hash, validate_doc(), new_paragraph_id(),
                   align_paragraphs() (diff theo đoạn), needs_revision(), count_syllables_fallback()
  ports.py         ContinuityPort (F11: mark_stale), ActiveJobPort (F12: job đang dùng chương làm nền)
be/src/writestory_be/infrastructure/db/models/chapters.py
be/migrations/versions/<rev>_f07_chapters_revisions_working_copy.py
```

`domain.py` không import FastAPI/SQLAlchemy (Arch §5). F11 dùng `new_paragraph_id()`, `project_doc()` và `service.snapshot_if_dirty()`.

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `chapters` | `id` TEXT PK, `work_id` FK, `chapter_no` INT, `title`, `status` (`draft`\|`drafting`\|`checking`\|`revising`\|`waiting_user`\|`committed`), `state_applied` BOOL=0, `current_revision_id` NULL FK, `revision_count` INT=0, `syllable_count` INT=0, `char_count` INT=0, `created_at`, `updated_at`, `deleted_at` NULL | UNIQUE(`work_id`,`chapter_no`) WHERE `deleted_at IS NULL`; INDEX(`work_id`,`chapter_no`) | Plan §5 "chapters: pointer tới revision hiện tại". `status` pipeline do F10 ghi (Review §4.4); chương người viết tay = `draft` tới khi commit |
| `chapter_revisions` | `id` TEXT PK, `chapter_id` FK, `revision_no` INT, `parent_revision_id` NULL, `source` (`manual`\|`agent`\|`revise`\|`restore`\|`import`), `reason` (`leave_chapter`\|`idle`\|`manual_snapshot`\|`before_ai_accept`\|`after_ai_accept`\|`before_restore`\|`restore`\|`full_replace`\|`pipeline_commit`\|`import`), `doc_json` (Tiptap JSON), `plain_text`, `paragraphs_json` (`[{id, type, level?, text}]`), `content_hash`, `syllable_count`, `char_count`, `job_id` NULL, `candidate_id` NULL, `restored_from_revision_id` NULL, `created_at` | UNIQUE(`chapter_id`,`revision_no`); INDEX(`chapter_id`,`created_at`) | Plan §5: Tiptap JSON + plain text projection + nguồn sửa + timestamp. **Bất biến** sau khi ghi |
| `chapter_working_copy` | `chapter_id` PK FK, `base_revision_id` NULL, `doc_json`, `content_hash`, `has_changes` BOOL, `client_session_id`, `client_seq` INT, `updated_at` | — | Plan §23.2 #2: một bản/chương, ghi đè, kèm base revision |

Migration mới. FTS cho nội dung chương (F09) đọc `chapter_revisions.plain_text` của revision hiện tại; F07 không quản lý FTS.

**Projection và `paragraph_id`** (Plan §23.1.B):

- Đoạn = node khối cấp cao `paragraph`, `heading`, `horizontalRule` (ngắt cảnh) mang `attrs.id` do Tiptap UniqueID sinh. `paragraphs_json[].id` chính là `paragraph_id`.
- Định dạng ID: 8 ký tự `[a-z0-9]` ngẫu nhiên (giả định đủ để va chạm hiếm trong một chương; luôn kiểm tra trùng). AI nhận dạng `[p:<id>] nội dung…`.
- `plain_text` = các `text` nối bằng `\n\n`; ngắt cảnh thành `* * *`. Bỏ mark (bold/italic) trong projection.
- `content_hash` = SHA-256 của `paragraphs_json` dạng JSON chuẩn (khóa sắp xếp, NFC) – dùng so sánh "có thay đổi so với base".

## API

Mã HTTP giả định (F01): `REVISION_CONFLICT` 409, `VALIDATION` 422, `NOT_FOUND` 404, `CHAPTER_READ_ONLY` 423, `WORK_BUSY_QUEUED` 409 (chèn/xóa/sắp xếp khi truyện đang chạy).

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/works/{id}/chapters` | `?cursor=&limit=` (≤ 500) | `{items: [ChapterListItem {id, chapter_no, title, status, syllable_count, current_revision_no, has_working_changes, updated_at}], next_cursor}` | `NOT_FOUND` |
| POST | `/v1/works/{id}/chapters` | `{title?, after_chapter_no?}` (không có = thêm cuối) | `201 ChapterOut` | `WORK_BUSY_QUEUED` (chèn giữa khi đang chạy), `VALIDATION` |
| DELETE | `/v1/chapters/{id}` | `?expected_revision=` | `204` (xóa mềm) | `WORK_BUSY_QUEUED`, `REVISION_CONFLICT`, `CHAPTER_READ_ONLY` |
| POST | `/v1/works/{id}/chapters/reorder` | `{order: [chapter_id…], expected_work_revision}` | `{items}` | `WORK_BUSY_QUEUED`, `VALIDATION` |
| GET | `/v1/chapters/{id}` | — | `ChapterOut {…, current_revision: {id, revision_no, source, doc_json}, edit_lock: EditLock\|null}` | `NOT_FOUND` |
| PUT | `/v1/chapters/{id}` | `{expected_revision, title?, doc?}` – `doc` tạo revision `source=manual`, `reason=full_replace` | `ChapterOut` | `REVISION_CONFLICT`, `CHAPTER_READ_ONLY`, `VALIDATION` |
| GET | `/v1/chapters/{id}/working-copy` | — | `{base_revision_id, doc_json, has_changes, updated_at}` hoặc `204` nếu chưa có | `NOT_FOUND` |
| PUT | `/v1/chapters/{id}/working-copy` | `{base_revision_id, doc, client_session_id, client_seq}` | `{saved_at, has_changes, content_hash, stale_write: bool}` | `REVISION_CONFLICT` (`detail.current_revision_id`), `CHAPTER_READ_ONLY` (`detail.job_id`, `detail.writing_chapter_no`), `VALIDATION` (`detail.duplicate_ids`, quá cỡ) |
| POST | `/v1/chapters/{id}/snapshot` | `{expected_revision, reason: manual_snapshot\|leave_chapter\|idle}` | `{created: bool, revision?: RevisionMeta}` | `REVISION_CONFLICT`, `CHAPTER_READ_ONLY` |
| GET | `/v1/chapters/{id}/revisions` | `?cursor=&limit=` | `{items: [RevisionMeta {id, revision_no, source, reason, syllable_count, created_at, job_id?}], next_cursor}` | `NOT_FOUND` |
| GET | `/v1/chapters/{id}/revisions/{rev}` | — | `RevisionOut` (có `doc_json`, `paragraphs_json`) | `NOT_FOUND` |
| GET | `/v1/chapters/{id}/revisions/{a}/diff/{b}` | `?include_equal=false` | `DiffOut {a: RevisionMeta, b: RevisionMeta, paragraphs: [{op: equal\|changed\|added\|removed, paragraph_id, a_index?, b_index?, a_text?, b_text?}]}`; `{b}` nhận thêm giá trị `working` | `NOT_FOUND` |
| POST | `/v1/chapters/{id}/revisions/{rev}/restore` | `{expected_revision}` | `{revision: RevisionMeta, stale_from?: int}` | `REVISION_CONFLICT`, `CHAPTER_READ_ONLY` |

`EditLock = {kind: "used_as_base", job_id, writing_chapter_no, job_state, pause_requested: bool}`.

## Logic xử lý

**Lưu working copy** (autosave, Plan §23.2 #2):

1. `validate_doc`: schema Tiptap hợp lệ, chỉ node/mark cho phép (fe.md), mọi khối cấp cao có `attrs.id` đúng định dạng, không trùng (trùng → 422 `detail.duplicate_ids`, FE sinh lại), kích thước ≤ 2 MB (giả định).
2. Chuẩn hóa NFC mọi text node (lưới an toàn; FE đã chuẩn hóa).
3. Kiểm khóa chỉ đọc (dưới). Kiểm `base_revision_id == chapters.current_revision_id`, sai → 409 kèm `current_revision_id`.
4. Cùng `client_session_id` mà `client_seq ≤` giá trị đã lưu → bỏ qua, trả `stale_write=true` (request đến trễ).
5. UPSERT working copy, `has_changes = content_hash ≠ hash(base revision)`. Không tạo revision, không đổi `chapters.updated_at` cho thư viện.

**Tạo revision** chỉ ở các mốc (Plan §23.2 #2):

| Mốc | Ai gọi | `reason` |
|---|---|---|
| Rời chương (đổi chương, đóng tab/cửa sổ) | FE → `snapshot` | `leave_chapter` |
| Nhàn ≥ 2 phút có thay đổi | FE → `snapshot` | `idle` |
| Ctrl+S | FE → `snapshot` | `manual_snapshot` |
| Trước/sau nhận AI | F11 gọi `service.snapshot_if_dirty()` rồi tạo revision `agent`/`revise` | `before_ai_accept` / `after_ai_accept` |
| Trước restore | `restore` tự gọi | `before_restore` |
| Pipeline commit chương | F10 | `pipeline_commit` |

`snapshot`: nếu working copy không tồn tại hoặc `has_changes=false` → `{created:false}`. Ngược lại trong một transaction: kiểm `expected_revision`, INSERT revision (`revision_no = max+1`, `parent_revision_id` = current), cập nhật `chapters.current_revision_id`, `revision_count`, `syllable_count`, `char_count`; đặt working copy `base_revision_id` = revision mới, `has_changes=false`. Sau commit, nếu chương `committed` và `chapter_no` < chương committed mới nhất → `ContinuityPort.mark_stale(work_id, chapter_no)` (F11, Plan §6.2 `stale_from(K)`).

**Restore** (EDT08, FL07 bước 4): kiểm khóa + `expected_revision` → `snapshot_if_dirty(before_restore)` → INSERT revision mới `source=restore`, `reason=restore`, `doc_json` chép từ `{rev}`, `restored_from_revision_id` → cập nhật pointer, reset working copy → `mark_stale` như trên. Không xóa hay sửa revision nào.

**Diff theo đoạn** (`align_paragraphs`): lấy `paragraphs_json` hai bản (hoặc working copy khi `b=working`). Duyệt theo thứ tự của `b`: ID có ở cả hai → `equal` nếu text giống, ngược lại `changed`; ID chỉ ở `b` → `added`; ID chỉ ở `a` → `removed`, chèn sau đoạn đứng trước nó trong `a` đã xuất hiện. `include_equal=false` bỏ `a_text/b_text` của đoạn `equal` để giảm payload. Diff mức từ làm ở FE Worker.

**Khóa "chương đang làm nền"** (Plan §23.2 #3): `ActiveJobPort.base_lock(chapter_id)` trả lock khi có job viết/revise/resync của cùng work cho chương `N = chapter_no + 1` ở trạng thái `running` hoặc `waiting_slot` sau khi đã bắt đầu (đã đọc nền). Khi lock: `PUT working-copy`, `snapshot`, `PUT` có `doc`, `restore`, `DELETE` → 423 `CHAPTER_READ_ONLY`. Đổi tiêu đề vẫn cho. "Tạm dừng để sửa" là `POST /v1/works/{id}/autowrite/pause` (F12) với `{reason: "edit_base", chapter_id}`: F12 dừng sau bước hiện tại và hủy candidate N vì base sẽ đổi; khi job hết `running` → lock tự mất. Job ở `waiting_user`: không khóa; `GET /chapters/{id}` trả `warnings: ["candidate_will_be_superseded"]`.

**Chèn/xóa/sắp xếp** (Plan §23.2 #4): truyện có job ghi đang chạy/chờ → `WORK_BUSY_QUEUED` cho chèn giữa, xóa (trừ chương cuối chưa committed), reorder. Khi dừng: đánh số lại `chapter_no` trong một transaction, rồi `mark_stale(work_id, K)` với K nhỏ nhất bị ảnh hưởng. Xóa = `deleted_at` (trash), revision giữ nguyên.

Quy tắc transaction: mọi ghi qua writer queue; transaction ngắn; không giữ transaction trong lúc chờ client.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| — | F07 không phát event mới; revision do người dùng tạo được FE cập nhật cục bộ | — |

F07 tiêu thụ (qua FE): `job.state` (bật/tắt khóa chỉ đọc), `chapter.committed` (F10 tạo revision mới → editor đang mở phải tải lại base), `work.continuity`.

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| AI vừa commit revision mới trong khi người dùng gõ | PUT working copy với base cũ → 409; FE giữ buffer, mở so sánh | `REVISION_CONFLICT` |
| Hai request autosave đến lệch thứ tự | `client_seq` loại bản cũ | — (`stale_write`) |
| Working copy có base khác revision hiện tại khi mở chương (AI nhận khi app đóng) | `GET working-copy` trả `base_revision_id`; FE so với `current_revision_id`, hiện banner chọn | — |
| Doc trùng `paragraph_id` (paste từ chính chương) | 422 `detail.duplicate_ids` | `VALIDATION` |
| Doc rỗng | Hợp lệ (một đoạn rỗng có ID) | — |
| Restore về chính revision hiện tại | `{created:false}` không tạo bản trùng | — |
| Chương đã xóa mềm | 404 cho mọi thao tác ghi | `NOT_FOUND` |
| Ghi (working copy hoặc snapshot) khi chương vừa bị khóa làm nền | 423; working copy cũng bị khóa nên FE giữ thay đổi trong RAM và đề nghị "Tạm dừng để sửa" hoặc sao chép thay đổi | `CHAPTER_READ_ONLY` |

## Việc cần làm

- [ ] Migration 3 bảng + index; ORM; repository.
- [ ] `domain.project_doc`, `validate_doc`, `new_paragraph_id`, `align_paragraphs`, `count_syllables_fallback` (NFC, tách khoảng trắng, bỏ token chỉ có dấu câu – Plan §6.6; thay bằng F08).
- [ ] Service working copy (base, `client_seq`), snapshot, `snapshot_if_dirty`, restore, replace.
- [ ] Chapters CRUD/reorder + kiểm truyện đang chạy.
- [ ] Ports `ContinuityPort` (stub no-op tới F11), `ActiveJobPort` (stub không khóa tới F12).
- [ ] API + schema + OpenAPI; ví dụ payload trong `contracts/examples/`.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | `project_doc`: heading/ngắt cảnh/mark, NFC, hash ổn định | `be/tests/unit/chapters/test_projection.py` |
| unit | `align_paragraphs`: equal/changed/added/removed, vị trí đoạn bị xóa | `be/tests/unit/chapters/test_align_paragraphs.py` |
| unit | `validate_doc`: ID trùng, ID sai định dạng, node lạ | `be/tests/unit/chapters/test_validate_doc.py` |
| integration | 100 lần PUT working copy → 0 revision; snapshot tạo 1; snapshot lần 2 không đổi → `created=false` | `be/tests/integration/chapters/test_working_copy_revisions.py` |
| integration | Base lệch → 409; `client_seq` cũ → `stale_write` | `be/tests/integration/chapters/test_conflicts.py` |
| integration | Restore tạo revision mới, giữ lịch sử; chương cũ → gọi `mark_stale` | `be/tests/integration/chapters/test_restore.py` |
| integration | Khóa làm nền: job N running → 423; job dừng → ghi được | `be/tests/integration/chapters/test_base_lock.py` |
| integration | Kill process sau PUT working copy → mở lại có nội dung | `tests/integration/test_editor_crash_recovery.py` |

Luồng: [T12](../../tests/flows/T12-editor-autosave-ime.md), [T10](../../tests/flows/T10-sua-tay-va-resync.md), [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md).

## Tên mới đề xuất

- Mã lỗi: `CHAPTER_READ_ONLY` (423), `NOT_FOUND` (nếu F01 chưa có).
- API: `GET /v1/chapters/{id}/revisions/{rev}`; giá trị `working` cho `{b}` của diff; query `?include_equal=`; body pause `{reason: "edit_base", chapter_id}` cho `POST /v1/works/{id}/autowrite/pause` (F12).
- Cột `chapters`: `status` (giá trị nêu trên), `state_applied`, `revision_count`, `syllable_count`, `char_count`, `deleted_at`.
- Cột `chapter_revisions`: `revision_no`, `parent_revision_id`, `source` (`manual|agent|revise|restore|import`), `reason` (danh sách trên), `doc_json`, `paragraphs_json`, `content_hash`, `syllable_count`, `char_count`, `job_id`, `candidate_id`, `restored_from_revision_id`.
- Cột `chapter_working_copy`: `base_revision_id`, `doc_json`, `content_hash`, `has_changes`, `client_session_id`, `client_seq`.
- Code: `EditLock`, `project_doc`, `validate_doc`, `new_paragraph_id`, `align_paragraphs`, `snapshot_if_dirty`, `count_syllables_fallback`, `ContinuityPort.mark_stale`, `ActiveJobPort.base_lock`; định dạng `paragraph_id` 8 ký tự `[a-z0-9]`.
