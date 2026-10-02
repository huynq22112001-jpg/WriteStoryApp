# F13 — Backend

## Module và file

```text
be/src/writestory_be/modules/operations/
  export/   router.py schemas.py service.py (pin revisions, tạo job, receipt, stale)
  backup/   router.py schemas.py service.py (tạo/xác minh/ghim/xóa/khôi phục, retention)
be/src/writestory_be/infrastructure/files/
  export.py          Writer TXT / Markdown / EPUB (thuần, nhận dữ liệu đã ghim)
  backup.py          VACUUM INTO, manifest, zip, verify, swap khi restore
  atomic.py          ghi file tạm trong data/tmp + fsync + os.replace
be/src/writestory_be/jobs/maintenance.py   Chế độ bảo trì: dừng scheduler, đóng writer, dispose engine
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `export_receipts` | `id`, `work_id`, `job_id`, `format` (`txt`/`md`/`epub`), `chapter_from`, `chapter_to`, `options` JSON (tiêu đề, metadata, line ending), `chapters` JSON [{`chapter_id`, `chapter_no`, `revision_id`, `content_sha256`}], `source_hash` (sha256 của chuỗi hash chương), `file_relpath`, `file_size`, `file_sha256`, `status` (`succeeded`/`failed`), `error_code`, `created_at` | idx (`work_id`, `created_at`) | Plan §18, FL25 bước 2 |
| `backup_manifests` | `id`, `job_id`, `kind` (`manual`/`pre_restore`/`pre_migration`), `file_relpath`, `file_size`, `file_sha256`, `schema_version`, `app_version`, `include_vault`, `db_sha256`, `asset_count`, `asset_bytes`, `pinned`, `label`, `status` (`succeeded`/`failed`/`missing`), `restored_from_id`, `created_at` | idx (`kind`, `created_at`) | Plan §18 |
| `settings` (khóa) | `backup.retention_count` = 10 (giả định), `backup.include_vault_default` = false, `export.txt_line_ending` = `lf`, `export.txt_bom` = false | — | — |

Migration: `be/migrations/versions/<rev>_f13_exports_backups.py`. Không backfill.

Manifest trong file backup (`manifest.json`, format version 1):

```text
{format_version: 1, app_version, schema_version, data_id, created_at, include_vault,
 db: {path: "db/app.sqlite3", size, sha256},
 files: [{path: "assets/<work-id>/...", size, sha256}, ...],      # assets/, methods/, imports/
 excluded: ["backups/", "exports/", "logs/", "cache/", "tmp/"]}
```

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| POST | `/v1/exports` | `{work_id, format, chapter_from, chapter_to, include_titles, include_metadata, metadata?: {title, author, description}, idempotency_key}` | 202 `{job_id, receipt_id}` | `VALIDATION` (khoảng rỗng/ngược), `NOT_FOUND` |
| GET | `/v1/works/{id}/exports` | — | `[{receipt…, stale: bool, file_exists: bool}]` | — |
| GET | `/v1/exports/{id}` | — | receipt + `stale_chapters[]` | `NOT_FOUND` |
| DELETE | `/v1/exports/{id}` | — | 204 (xóa file, giữ receipt `deleted`) | `NOT_FOUND` |
| POST | `/v1/backups` | `{include_vault, label?, idempotency_key}` | 202 `{job_id}` | `MAINTENANCE` |
| GET | `/v1/backups` | — | `[{backup_manifests…, file_exists}]` | — |
| PATCH | `/v1/backups/{id}` | `{pinned?, label?}` | manifest | `NOT_FOUND` |
| DELETE | `/v1/backups/{id}` | — | 204 | `VALIDATION` (đang dùng bởi restore) |
| POST | `/v1/backups/{id}/verify` | — | 202 `{job_id}` → kết quả `{ok, problems[]}` | `NOT_FOUND` |
| POST | `/v1/backups/{id}/copy-to` | `{dest_path}` (từ hộp thoại lưu của Tauri) | 202 `{job_id}` | `VALIDATION` (đích nằm trong data-root) |
| POST | `/v1/backups/restore` | `{backup_id? \| external_path?, restore_vault, confirm: true}` | 202 `{job_id}` | `BACKUP_INVALID` 422, `BACKUP_INCOMPATIBLE` 409, `MAINTENANCE` 409 |

Export và backup là job (Plan §4.3: API trả job ID ngay), không cần `work_locks`; restore là job bảo trì toàn app.

## Logic xử lý

**Export** (FL25 bước 1–2):

1. Trong một read transaction: lấy chương `chapter_from..chapter_to` chưa `deleted_at`, `current_revision_id`, plain text + Tiptap JSON; tính `content_sha256` theo plain text NFC. Chương chưa commit (không có revision) bị bỏ qua và liệt kê trong receipt `options.skipped`. Working copy chưa tạo revision **không** được xuất (FE cảnh báo trước).
2. Persist receipt `status=pending` với danh sách revision đã ghim, rồi đóng transaction.
3. `infrastructure/files/export.py` sinh nội dung (chuẩn hóa NFC lần nữa khi ghi):
   - **TXT**: UTF-8 (BOM tùy chọn), đầu file tiêu đề + metadata nếu bật; mỗi chương `Chương {n}: {tiêu đề}` (nếu bật), đoạn cách nhau một dòng trống; line ending theo cài đặt.
   - **Markdown**: front matter YAML (title, author, language `vi`, ngày xuất) nếu bật metadata; `# Tiêu đề truyện`, `## Chương n: …`; bold/italic Tiptap → `**`/`*`; escape ký tự đầu dòng dễ thành cú pháp (`#`, `>`, `-`, `*`, `1.`).
   - **EPUB 3**: `mimetype` là mục đầu tiên, không nén; `META-INF/container.xml`; `OEBPS/content.opf` (`dc:title`, `dc:language`=`vi`, `dc:identifier` = `urn:uuid:<work-id>` cố định, `dc:creator`, `dcterms:modified`); `nav.xhtml` + `toc.ncx` (tương thích đọc EPUB 2); một XHTML/chương, escape XML, `xml:lang="vi"`; CSS dùng font serif hệ thống, không nhúng font mặc định.
4. Ghi vào `data/tmp/export-<receipt-id>.part`, fsync, `os.replace` sang `data/exports/<work-id>/<slug>_ch<from>-<to>_<YYYYMMDD-HHmmss>.<ext>` (cùng filesystem; `slug` bỏ dấu + `đ→d`, giới hạn 60 ký tự). Tính `file_sha256`; receipt `succeeded`.
5. Lỗi/hủy: xóa `.part`, receipt `failed` + `error_code`; không bao giờ để file dở trong `exports/`.

`stale` của receipt = có chương mà `current_revision_id` khác revision đã ghim (EDT12, R3 hiển thị chi tiết).

**Backup** (Plan §5, FL25 bước 3):

1. Tạo `data/tmp/backup-<id>/` (đích `VACUUM INTO` phải chưa tồn tại).
2. Mở connection đọc riêng (không qua writer queue): `VACUUM INTO 'data/tmp/backup-<id>/app.sqlite3'`. Đây là snapshot nhất quán, không chặn writer ở WAL; không dùng Backup API từng bước vì khởi động lại khi có ghi xen giữa (Review §7.2).
3. `PRAGMA integrity_check` trên bản sao; lỗi → job `failed`.
4. Asset: duyệt bảng `assets` (nguồn chuẩn), copy từng file `assets/`, `methods/`, `imports/` vào staging; checksum phải khớp `assets.checksum`; lệch → đọc lại một lần, vẫn lệch → `failed` (file đang bị thay). File mồ côi không có trong DB bị bỏ qua.
5. Vault: chỉ khi `include_vault` – copy nguyên `secrets.enc` (đã mã hóa; không bao giờ xuất plaintext).
6. Ghi `manifest.json`; nén zip (ZIP64) vào `data/tmp/<name>.zip.part` → `os.replace` sang `data/backups/writestory-backup-<YYYYMMDD-HHmmss>.zip`; xóa staging.
7. Insert `backup_manifests`; áp retention: giữ `backup.retention_count` bản mới nhất không `pinned`, xóa file + đánh dấu bản cũ hơn. Bản `pre_restore` cũng tính vào retention nhưng luôn giữ bản mới nhất.

Không lồng: thư mục `backups/`, `exports/`, `logs/`, `cache/`, `tmp/` không bao giờ được duyệt (danh sách cho phép, không phải danh sách loại trừ).

**Restore** (FL25 bước 4):

1. Validate (chưa đụng dữ liệu): mở zip, đọc manifest, `format_version` hỗ trợ; `schema_version` > head hiện tại → `BACKUP_INCOMPATIBLE`; sha256 DB và mọi file khớp; giải nén vào `data/tmp/restore-<id>/new/`; `PRAGMA integrity_check` → lỗi thì `BACKUP_INVALID`.
2. Backup hiện trạng (`kind=pre_restore`) bằng routine trên; thất bại → dừng restore.
3. Vào chế độ bảo trì (`jobs/maintenance.py`): scheduler ngừng admit; yêu cầu cancel mọi job ở ranh giới bước, đợi tối đa 30 s (giả định) rồi hủy cứng; API ghi trả `503 MAINTENANCE`; dừng writer queue; `PRAGMA wal_checkpoint(TRUNCATE)`; dispose engine (đóng mọi connection).
4. Swap bằng rename cùng filesystem: `db/app.sqlite3` (và `-wal`/`-shm` nếu còn) → `data/tmp/restore-<id>/old/`; DB mới → `db/`; tương tự `assets/`, `methods/`, `imports/`; vault chỉ khi `restore_vault`.
5. Mở lại engine; nếu `schema_version` cũ hơn → chạy Alembic tới head; rebuild FTS (projection, Plan §5); reconcile: job `running`/`queued` → `interrupted`, `work_locks` xóa, batch auto-write `paused`; ghi `backup_manifests` mới trong DB đã khôi phục với `restored_from_id`.
6. Thoát bảo trì; phát `backend.notice {kind: "restored"}` để FE nạp lại toàn bộ.
7. Lỗi ở bước 4–5 → rename ngược `old/` về chỗ cũ, mở lại engine cũ, báo `failed`; không bao giờ báo đã restore khi chỉ copy được một phần (FL25). Thư mục `old/` giữ tới lần dọn `tmp` kế tiếp (F14).

Quy tắc transaction: export chỉ có một read transaction ngắn ở bước 1; backup không mở write transaction trên DB nguồn; restore thay file khi không còn connection nào.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `job.state` | Job export/backup/restore đổi trạng thái | `{job_id, type, status, error_code?}` |
| `job.step` | Tiến độ | `{stage: "snapshot" \| "assets" \| "package" \| "validate" \| "swap" \| "fts", done, total}` |
| `backend.notice` | Bắt đầu/kết thúc bảo trì, restore xong | `{kind: "maintenance_on" \| "maintenance_off" \| "restored"}` |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Khoảng chương không có chương committed | Từ chối khi tạo | `VALIDATION` |
| Ổ đầy khi ghi file tạm | Xóa `.part`, job `failed` | `STORAGE_FULL` |
| Tên tác phẩm chứa ký tự cấm trên Windows | Slug an toàn; giữ tên đầy đủ trong metadata | — |
| Backup khi đang restore | Từ chối | `MAINTENANCE` |
| File backup trong danh sách nhưng đã bị xóa tay | `status=missing`, ẩn nút khôi phục | — |
| Zip từ nguồn ngoài có đường dẫn `../` | Từ chối (chống zip-slip) | `BACKUP_INVALID` |
| Tắt app giữa swap | Lần khởi động sau phát hiện `data/tmp/restore-*/` có `old/` mà DB thiếu → khôi phục `old/` trước khi migrate (F00/F02 gọi hook) | — |

## Việc cần làm

- [ ] Migration `export_receipts`, `backup_manifests`.
- [ ] `atomic.py` (tạm + fsync + replace) dùng chung.
- [ ] Writer TXT, Markdown, EPUB + escape.
- [ ] Export service + receipt + stale.
- [ ] Backup: VACUUM INTO, integrity check, asset checksum, manifest, zip, retention.
- [ ] Restore: validate, pre_restore, chế độ bảo trì, swap, rollback, FTS rebuild, reconcile.
- [ ] Hook khởi động phục hồi swap dở.
- [ ] `copy-to` ra đường dẫn người dùng chọn.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | TXT/MD: NFC, tiêu đề, escape Markdown | `be/tests/unit/files/test_export_text.py` |
| unit | EPUB: `mimetype` đầu và không nén, OPF hợp lệ, XHTML escape | `be/tests/unit/files/test_export_epub.py` |
| unit | Manifest + chặn zip-slip + so checksum | `be/tests/unit/files/test_backup_manifest.py` |
| integration | Backup khi 3 truyện mock đang commit; DB backup integrity ok (T16) | `be/tests/integration/test_backup_during_write.py` |
| integration | Restore thành công + FTS tìm được; restore lỗi ở bước swap → dữ liệu cũ nguyên vẹn | `be/tests/integration/test_restore.py` |
| integration | Không backup lồng; retention xóa đúng bản | `be/tests/integration/test_backup_retention.py` |
| integration | Export → sửa chương → receipt `stale` | `be/tests/integration/test_export_receipt.py` |

## Tên mới đề xuất

- Cột: `export_receipts.{format, chapter_from, chapter_to, options, chapters, source_hash, file_relpath, file_size, file_sha256, status, error_code}`; `backup_manifests.{kind, file_relpath, file_size, file_sha256, schema_version, app_version, include_vault, db_sha256, asset_count, asset_bytes, pinned, label, status, restored_from_id}`.
- Khóa settings: `backup.retention_count`, `backup.include_vault_default`, `export.txt_line_ending`, `export.txt_bom`.
- API: `GET /v1/works/{id}/exports`, `GET|DELETE /v1/exports/{id}`, `GET /v1/backups`, `PATCH|DELETE /v1/backups/{id}`, `POST /v1/backups/{id}/verify`, `POST /v1/backups/{id}/copy-to`, `POST /v1/backups/restore`.
- Mã lỗi: `BACKUP_INVALID`, `BACKUP_INCOMPATIBLE`, `MAINTENANCE`, `STORAGE_FULL`.
- File: `infrastructure/files/atomic.py`, `jobs/maintenance.py`; module `modules/operations/{export,backup}`.
