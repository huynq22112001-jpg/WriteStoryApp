# F05 — Backend

## Module và file

```text
be/src/writestory_be/modules/works/
  router.py          /v1/works*, /v1/works/{id}/style-profile, /v1/languages*
  schemas.py         WorkCreate, WorkPatch, WorkOut, WorkListItem, WorkListQuery, StyleProfileIn/Out, GenrePresetOut
  service.py         Tạo nháp, sửa, chuyển trạng thái, xóa mềm, danh sách thư viện, style profile
  domain.py          Thuần: compute_library_badge(), validate_ready_transition(), validate_length_range()
  ports.py           WorkRepository, JobSummaryPort (F12 triển khai), FoundationReadinessPort (F06 triển khai)
be/src/writestory_be/core/text_fold.py      Bản tối giản R1: NFC + bỏ dấu + đ→d cho cột tìm kiếm (thay bằng LanguagePack.search_normalizer của F08)
be/src/writestory_be/infrastructure/db/models/works.py
be/migrations/versions/<rev>_f05_works_style_profile.py
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `projects` | `id` PK, `name`, `created_at` | — | Migration tạo một dòng mặc định (Plan §5) |
| `works` | `id` TEXT PK, `project_id` FK, `title`, `title_search` (đã fold), `language` = `vi`, `genre` (khóa preset) NULL, `genre_label_custom` NULL, `status` (`draft`\|`ready`\|`archived`), `brief` TEXT NULL, `target_chapters` INT NULL, `chapter_length_min` INT=2500, `chapter_length_max` INT=3500, `autowrite_mode_default` (`auto`\|`review_each`\|`review_every_k`), `review_every_k` INT NULL, `max_repair_rounds` INT NULL, `budget_daily_usd` REAL NULL, `budget_daily_tokens` INT NULL, `continuity_status` (`ok`\|`blocked_needs_resync`\|`stale_from`) = `ok`, `continuity_chapter_no, continuity_reason` INT NULL, `cover_asset_id` NULL FK `assets`, `wizard_step` TEXT NULL, `wizard_completed_steps` JSON `[]`, `last_opened_at` NULL, `revision` INT, `created_at`, `updated_at`, `deleted_at` NULL | CHECK `language='vi'` (MVP; nới khi có gói mới); CHECK `chapter_length_min < chapter_length_max`; CHECK `continuity_chapter_no, continuity_reason IS NOT NULL` ⇔ `continuity_status='stale_from'`; INDEX(`deleted_at`,`updated_at`), INDEX(`status`), INDEX(`genre`), INDEX(`last_opened_at`) | Plan §5 "works"; `continuity_status` theo Plan §4.3 (F11 ghi). NULL ở ngân sách/K/vòng sửa = dùng mặc định app |
| `style_profile` | `id` PK, `work_id` UNIQUE FK CASCADE, `vocab_register` (`han_viet`\|`balanced`\|`thuan_viet`), `dialogue_style` (`dash`\|`quotes`), `dialogue_dash_char` (`–`\|`—`) NULL, `tone_mark_style` (`old`\|`new`), `punctuation_rules` JSON, `banned_phrases` JSON `[]`, `voice` TEXT NULL, `voice_samples` JSON `[]` (tối đa 2), `revision` INT, `updated_at` | — | Plan §5 "style_profile", §6.6. `tone_mark_style`: `old` = `hoà`, `thuý`; `new` = `hòa`, `thúy`. `voice_samples` phục vụ Plan §23.3 #7 |

Migration mới, không có dữ liệu cũ. Cột `works.foundation_status` do migration của F06 thêm. Văn bản lưu NFC.

## API

Mã HTTP giả định (chốt ở F01): `VALIDATION` 422, `NOT_FOUND` 404, `REVISION_CONFLICT` 409, `WORK_ACTIVE_JOB` 409.

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/works` | `?q=&genre=&status=&continuity=&sort=updated\|opened\|title&cursor=&limit=` (≤ 200, mặc định 100) | `{items: [WorkListItem], next_cursor}` | `VALIDATION` |
| POST | `/v1/works` | `{title, language: "vi", genre?, genre_label_custom?, wizard_step?: "basics"}` | `201 WorkOut` (`status=draft`) + tạo `style_profile` theo preset thể loại | `VALIDATION` (language ≠ `vi`, title rỗng/ > 200 ký tự) |
| GET | `/v1/works/{id}` | — | `WorkOut` (gồm `style_profile`, `wizard_step`, `wizard_completed_steps`, `foundation_status` khi F06 có) | `NOT_FOUND` |
| PATCH | `/v1/works/{id}` | `{expected_revision, title?, genre?, brief?, target_chapters?, chapter_length_min?, chapter_length_max?, autowrite_mode_default?, review_every_k?, max_repair_rounds?, budget_daily_usd?, budget_daily_tokens?, cover_asset_id?, wizard_step?, wizard_completed_steps?, status?: ready\|archived\|draft}` | `WorkOut` | `NOT_FOUND`, `REVISION_CONFLICT`, `VALIDATION` (`detail.missing` khi chuyển `ready` thiếu điều kiện) |
| DELETE | `/v1/works/{id}` | — | `204` (đặt `deleted_at`) | `NOT_FOUND`, `WORK_ACTIVE_JOB` |
| POST | `/v1/works/{id}/open` | — | `204` (cập nhật `last_opened_at`) | `NOT_FOUND` |
| GET | `/v1/works/{id}/style-profile` | — | `StyleProfileOut` | `NOT_FOUND` |
| PUT | `/v1/works/{id}/style-profile` | `{expected_revision, vocab_register, dialogue_style, dialogue_dash_char?, tone_mark_style, punctuation_rules, banned_phrases, voice?, voice_samples}` | `StyleProfileOut` | `REVISION_CONFLICT`, `VALIDATION` (> 2 đoạn mẫu, đoạn mẫu > 2.000 ký tự – giả định) |
| GET | `/v1/languages` | — | `[{code: "vi", label: "Tiếng Việt", enabled: true}]` | — |
| GET | `/v1/languages/{code}/genres` | — | `[GenrePresetOut {key, label, description, defaults: {vocab_register, dialogue_style, tone_mark_style, chapter_length_min, chapter_length_max}}]` | `NOT_FOUND` |

`WorkListItem`: `id, title, genre, genre_label, status, continuity_status, continuity_chapter_no, continuity_reason, committed_chapters, target_chapters, job?: {state, waiting_reason, queue_position, chapter_no, step}, badge: {kind, label_key, params}, cost_total_usd?, cover_url?, last_opened_at, updated_at`. Không trả `brief`, không nạp nội dung chương (Plan §4.4).

## Logic xử lý

1. **Tạo nháp (wizard bước 1):** validate → INSERT `works` (`status=draft`, `wizard_step=basics`) + INSERT `style_profile` lấy `defaults` của preset thể loại (không có preset → `balanced`, `dash`, `–`, `new`) trong cùng transaction.
2. **Lưu từng bước:** FE gọi PATCH với các trường của bước + `wizard_step` (bước kế tiếp) + `wizard_completed_steps`. Giá trị bước: `basics`, `brief`, `foundation`, `address_rules`, `event_outline`, `writing_config`, `review`. BE chỉ validate kiểu dữ liệu; không ép thứ tự bước (người dùng quay lại bước trước được).
3. **Chuyển `draft → ready`** (`domain.validate_ready_transition`): yêu cầu `title`, `genre` hoặc `genre_label_custom`, `brief` không rỗng, `target_chapters ≥ 1`, khoảng độ dài hợp lệ, và `FoundationReadinessPort.is_ready(work_id)` (F06: nền truyện đã nhận, có state seed chương 0, có ≥ 1 `story_events`). Thiếu → 422 `VALIDATION` `detail.missing=[...]`. Thành công → `wizard_step=NULL`.
4. **Ready → draft** không cho phép khi đã có chương committed.
5. **Danh sách thư viện:** truy vấn `works` (không `deleted_at`), `committed_chapters` = `MAX(chapter_no)` của chương `committed` (F07/F10; trước khi có thì 0) bằng một subquery gom nhóm, `job` lấy từ `JobSummaryPort.summaries(work_ids)` (một truy vấn cho cả trang). Tìm kiếm: `title_search LIKE %fold(q)%` (≤ vài trăm tác phẩm nên không cần FTS; giả định).
6. **Badge** (`domain.compute_library_badge`), ưu tiên từ trên xuống:

| # | Điều kiện | `kind` | Nhãn (vi) |
|---|---|---|---|
| 1 | `continuity_status = blocked_needs_resync` hoặc job `blocked` | `blocked` | ⛔ Bị chặn, cần resync |
| 2 | job `running` | `running` | ▶ Đang viết Ch.{n} |
| 3 | job `waiting_user` | `waiting_user` | ✋ Chờ duyệt Ch.{n} |
| 4 | job `waiting_slot` | `waiting_slot` | ⏳ Chờ slot #{pos} ({reason}) |
| 5 | job `queued` | `queued` | ⏳ Trong hàng đợi |
| 6 | job `interrupted` | `interrupted` | ⏸ Bị gián đoạn |
| 7 | job `failed` gần nhất chưa xử lý | `failed` | ✕ Lỗi |
| 8 | `continuity_status = stale_from` | `stale` | ⚠ Cần settle lại từ Ch.{k} |
| 9 | `status = draft` | `draft` | ✎ Bản nháp – bước {step} |
| 10 | `target_chapters` và `committed_chapters ≥ target_chapters` | `done` | ✓ Xong |
| 11 | còn lại | `ready` | Sẵn sàng |

7. **Xóa mềm:** từ chối khi `JobSummaryPort` báo job ở `queued|waiting_slot|running|waiting_user`. Purge thật (xóa dữ liệu chương, asset) là thao tác riêng sau backup (F13/F14).
8. **Style profile sửa khi truyện đang chạy:** tăng `revision`, đánh dấu Story Bible "dirty" để áp từ chương kế tiếp (cơ chế `bible_revisions` ở [F06 be.md](../F06-nen-truyen-va-story-bible/be.md)); không ảnh hưởng chương đang viết.

Quy tắc transaction: mọi ghi đi qua writer queue (F02), transaction ngắn; PATCH kiểm `expected_revision` trong cùng transaction.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| — | F05 không tạo job; không phát event mới | — |

FE cập nhật thư viện bằng các event sẵn có: `job.state`, `queue.changed`, `work.continuity`, `chapter.committed` (Plan §23.1.C).

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Tiêu đề trùng tác phẩm khác | Cho phép (chỉ cảnh báo phía FE) | — |
| Tiêu đề có ký tự tổ hợp NFD (dán từ macOS) | Chuẩn hóa NFC trước khi lưu và fold | — |
| Đổi `target_chapters` nhỏ hơn số chương đã commit | Từ chối | `VALIDATION` |
| Đổi `genre` khi đã `ready` | Cho phép; không tự đổi style profile; ghi chú áp từ chương kế tiếp | — |
| `review_every_k` thiếu khi `autowrite_mode_default=review_every_k` | Từ chối | `VALIDATION` |
| Cursor sai/hết hạn | Từ chối | `VALIDATION` |
| Preset thể loại không tồn tại trong gói `vi` | Lưu `genre=NULL`, dùng `genre_label_custom` | `VALIDATION` nếu cả hai rỗng khi chuyển `ready` |
| Xóa khi đang auto-write | Từ chối, gợi ý dừng auto-write trước | `WORK_ACTIVE_JOB` |

## Việc cần làm

- [ ] Migration `projects` (dòng mặc định), `works`, `style_profile` + index.
- [ ] `core/text_fold.py` (NFC → bỏ dấu → `đ→d`) và cột `title_search`.
- [ ] Repository + service + router; schema Pydantic; OpenAPI.
- [ ] `compute_library_badge` thuần + `JobSummaryPort` (stub trả rỗng tới khi có F12).
- [ ] `FoundationReadinessPort` (stub trả `false` + `missing=["foundation"]` tới khi có F06).
- [ ] Đọc `genres.json` của gói `vi` qua `importlib.resources` (Arch §6).
- [ ] Phân trang cursor theo (`updated_at`, `id`).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Bảng ưu tiên badge (11 trường hợp + kết hợp) | `be/tests/unit/works/test_library_badge.py` |
| unit | `validate_ready_transition`: thiếu từng điều kiện → `detail.missing` đúng | `be/tests/unit/works/test_ready_transition.py` |
| unit | `text_fold`: "Nguyễn"→"nguyen", "Đường"→"duong", NFD → NFC | `be/tests/unit/core/test_text_fold.py` |
| integration | Tạo nháp → PATCH từng bước → restart app → GET trả đúng `wizard_step` | `be/tests/integration/works/test_wizard_draft.py` |
| integration | Danh sách 200 tác phẩm, cursor, lọc, tìm không dấu | `be/tests/integration/works/test_library_list.py` |
| integration | Xóa khi có job running → `WORK_ACTIVE_JOB` | `be/tests/integration/works/test_delete_work.py` |
| contract | Snapshot OpenAPI module works | `be/tests/contract/test_openapi_works.py` |

Luồng: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md).

## Tên mới đề xuất

- API: `POST /v1/works/{id}/open`, `DELETE /v1/works/{id}`, `GET /v1/languages`, `GET /v1/languages/{code}/genres`; query `?q=&genre=&status=&continuity=&sort=&cursor=&limit=` cho `GET /v1/works`.
- Mã lỗi: `WORK_ACTIVE_JOB`, `NOT_FOUND` (nếu F01 chưa có).
- Cột `works`: `project_id`, `title_search`, `genre_label_custom`, `status` (`draft|ready|archived`), `brief`, `target_chapters`, `chapter_length_min`, `chapter_length_max`, `autowrite_mode_default`, `review_every_k`, `max_repair_rounds`, `budget_daily_usd`, `budget_daily_tokens`, `continuity_status`, `continuity_chapter_no, continuity_reason`, `cover_asset_id`, `wizard_step`, `wizard_completed_steps`, `last_opened_at`, `revision`, `deleted_at`.
- Cột `style_profile`: `vocab_register`, `dialogue_style`, `dialogue_dash_char`, `tone_mark_style`, `punctuation_rules`, `banned_phrases`, `voice`, `voice_samples`, `revision`.
- Code: `WorkListItem`, `compute_library_badge`, `validate_ready_transition`, `JobSummaryPort`, `FoundationReadinessPort`, `core/text_fold.py`.
