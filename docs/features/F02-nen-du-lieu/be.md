# F02 — Backend

## Module và file

```text
be/
  alembic.ini
  migrations/
    env.py                         Engine sync (pysqlite) riêng cho migration; render_as_batch=True; include_object loại FTS
    versions/0001_baseline.py      settings, jobs, job_steps, job_events, idempotency_records, work_locks, assets
    versions/0002_search.py        search_documents, search_fts (+ trigger), search_trigram (tùy chọn, tạo sau)
  src/writestory_be/
    infrastructure/db/
      engine.py                    create_engines(data_root) → write_engine, read_engine; pragma; BEGIN tường minh
      base.py                      DeclarativeBase + MetaData(naming_convention=…)
      models/system.py             ORM: Setting, Job, JobStep, JobEvent, IdempotencyRecord, WorkLock, Asset, SearchDocument
      writer.py                    WriterQueue: một task asyncio, một connection ghi
      unit_of_work.py              UnitOfWork.read(), UnitOfWork.write(fn), WriteContext (add_event, after_commit)
      guards.py                    contextvar in_write_txn; assert_not_in_write_txn() cho adapter AI/HTTP
      migrations.py                prepare_database(): kiểm tra revision, backup VACUUM INTO, upgrade, đánh dấu marker
      fts.py                       normalize_for_search(), build_match_query(), upsert/delete document, rebuild
      retention.py                 Dọn theo lô: job_events, idempotency_records, backup trước migrate, tmp
      repositories/settings.py     get/set có expected_revision
      repositories/jobs.py         Tạo/đổi trạng thái job (dùng bởi F12), truy vấn theo status/work
    infrastructure/files/storage.py   put_asset(), resolve(), verify(), orphan sweep
    jobs/locks.py                  WorkLockManager: acquire/heartbeat/release/assert_held
    jobs/recovery.py               Registry reconciler + reconciler lõi
    modules/system/router.py       GET /v1/system/info, POST /v1/system/search-index/rebuild (cùng module với F00)
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `settings` | `key TEXT`, `value_json TEXT NOT NULL`, `revision INTEGER NOT NULL DEFAULT 1`, `updated_at TEXT` | PK `key` | KV toàn app (UI prefs, onboarding, đồng thời…). Không chứa secret |
| `jobs` | `id TEXT`, `idempotency_key TEXT NULL`, `type TEXT`, `work_id TEXT NULL`, `status TEXT`, `wait_reason TEXT NULL`, `priority INTEGER DEFAULT 0`, `queue_position INTEGER NULL`, `input_json TEXT`, `base_revision_id TEXT NULL`, `stage TEXT NULL`, `progress_json TEXT NULL`, `checkpoint_json TEXT NULL`, `pinned_json TEXT NULL`, `attempt INTEGER DEFAULT 0`, `cancel_requested_at TEXT NULL`, `error_code TEXT NULL`, `error_json TEXT NULL`, `usage_json TEXT NULL`, `created_at`, `updated_at`, `started_at NULL`, `finished_at NULL`, `interrupted_at NULL`, `revision INTEGER DEFAULT 1` | PK `id`; UNIQUE `idempotency_key`; CHECK `status IN ('queued','waiting_slot','running','waiting_user','blocked','succeeded','failed','cancelled','interrupted')`; `ix_jobs_status`, `ix_jobs_work_id_status`, `ix_jobs_work_id_queue_position` | Trường theo Plan §4.3; F12 có thể thêm cột bằng migration riêng. `work_id` chưa có FK (README) |
| `job_steps` | `id TEXT`, `job_id TEXT`, `step TEXT`, `attempt INTEGER`, `round INTEGER NULL`, `status TEXT`, `input_hash TEXT NULL`, `output_hash TEXT NULL`, `checkpoint_json TEXT NULL`, `prompt_id`, `prompt_version`, `model_id`, `effort` (đều NULL được), `usage_json NULL`, `error_code NULL`, `started_at`, `finished_at NULL` | PK `id`; FK `job_id → jobs.id ON DELETE CASCADE`; UNIQUE `(job_id, step, attempt, round)`; `ix_job_steps_job_id_started_at` | Contract JobStep Plan §17 |
| `job_events`, `idempotency_records` | Theo [F01 be.md](../F01-hop-dong-api-va-su-kien/be.md#dữ-liệu-và-migration) | — | Tạo trong `0001_baseline` |
| `work_locks` | `work_id TEXT`, `job_id TEXT NOT NULL`, `owner_id TEXT NOT NULL`, `acquired_at`, `heartbeat_at`, `lease_expires_at` | PK `work_id`; `ix_work_locks_lease_expires_at` | `owner_id` = ID phiên backend (UUIDv7 sinh mỗi lần khởi động) |
| `assets` | `id TEXT`, `work_id TEXT NULL`, `kind TEXT`, `rel_path TEXT NOT NULL`, `sha256 TEXT NOT NULL`, `size_bytes INTEGER`, `mime_type TEXT`, `original_name TEXT NULL`, `status TEXT DEFAULT 'ready'`, `created_at` | PK `id`; UNIQUE `rel_path`; `ix_assets_work_id`, `ix_assets_sha256`; CHECK `status IN ('ready','missing','deleted')` | `rel_path` tương đối data-root, dấu `/` (Plan §3.1 di chuyển được) |
| `search_documents` | `id INTEGER PRIMARY KEY`, `work_id TEXT NULL`, `source_type TEXT`, `source_id TEXT`, `paragraph_id TEXT NULL`, `chapter_no INTEGER NULL`, `source_revision_id TEXT NULL`, `language TEXT DEFAULT 'vi'`, `title TEXT NULL`, `title_norm TEXT NULL`, `body TEXT`, `body_norm TEXT`, `updated_at` | UNIQUE index biểu thức `(source_type, source_id, ifnull(paragraph_id,''))`; `ix_search_documents_work_id_source_type` | Projection rebuild được (Plan §5); giữ nguồn chương/đoạn |
| `search_fts` (FTS5) | `title_norm`, `body_norm` | `content='search_documents'`, `content_rowid='id'`, `tokenize="unicode61 remove_diacritics 2"`; trigger AFTER INSERT/DELETE/UPDATE trên `search_documents` theo mẫu external content của FTS5 | Không tự chứa văn bản |
| `search_trigram` (FTS5, tùy chọn) | `title_norm` | `tokenize='trigram'`, external content; trigger có `WHEN source_type IN ('character','location')` | Chỉ tạo khi setting `search.trigram_enabled=true`; chuỗi < 3 ký tự không khớp |

Migration: `0001_baseline.py`, `0002_search.py` (FTS và trigger viết bằng `op.execute` SQL thô). Không có dữ liệu cũ. Quy tắc cho mọi migration của dự án: không sửa migration đã phát hành; thay đổi cột trên SQLite dùng `op.batch_alter_table`; migration dữ liệu phải chạy lại được an toàn; sau migration có đụng FK chạy `PRAGMA foreign_key_check`.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/system/info` | — | `{data_root, data_id, schema_revision, schema_head, sqlite_version, db_size_bytes, wal_size_bytes, search: {tokenizer, index_version, trigram_enabled, document_count, rebuilding: bool}}` | `UNAUTHORIZED` |
| POST | `/v1/system/search-index/rebuild` | Header `Idempotency-Key`; body `{}` | 202 `{status: "started" \| "already_running"}` | `UNAUTHORIZED`, `IDEMPOTENCY_CONFLICT` |

Các module khác dùng F02 qua Python (`UnitOfWork`, `WorkLockManager`, `storage.put_asset`, `fts.*`, `register_reconciler`), không qua HTTP.

## Logic xử lý

### A. Engine và transaction (Plan §5, Review §7.2)

1. URL tạo bằng `URL.create("sqlite+aiosqlite", database=str(abs_db_path))` (đường dẫn Unicode/khoảng trắng an toàn).
2. Sự kiện `connect` trên `engine.sync_engine`: `dbapi_connection.isolation_level = None` (tắt transaction ngầm của driver), rồi `PRAGMA foreign_keys=ON`, `PRAGMA busy_timeout=5000`, `PRAGMA synchronous=FULL`. `PRAGMA journal_mode=WAL` chạy một lần khi tạo DB (bền trong file). Read engine thêm `PRAGMA query_only=ON`.
3. Sự kiện `begin`: write engine phát `BEGIN IMMEDIATE` (giành quyền ghi ngay, không nâng cấp khóa giữa chừng); read engine phát `BEGIN` (đọc snapshot nhất quán nhiều câu lệnh).
4. `write_engine`: `pool_size=1, max_overflow=0` — chỉ `WriterQueue` dùng. `read_engine`: `pool_size=4` (giả định). Mỗi đơn vị công việc một `AsyncSession` riêng, không chia sẻ giữa task (Arch §5).
5. `UnitOfWork.read()`: `async with` session đọc; phải đóng **trước** mọi lời gọi mạng/AI.
6. `UnitOfWork.write(fn, timeout_s=10)`: đóng gói `fn(ctx: WriteContext)` thành lệnh đưa vào `WriterQueue` (maxsize 256, giả định) và chờ `Future`.
7. `WriterQueue` (một task): lấy lệnh → session trên connection ghi → đặt contextvar `in_write_txn` → `await fn(ctx)` → insert `ctx.events` vào `job_events` (outbox, F01) → `commit` → chạy `after_commit` callbacks và `EventBus.broadcast` → trả kết quả. Lỗi → `rollback`, trả exception cho người gọi, không broadcast. Lệnh chờ quá `timeout_s` trong hàng → `AppError(DB_BUSY)`. Lệnh chạy > 200 ms → log cảnh báo kèm tên lệnh.
8. `fn` chỉ được làm việc với session (không HTTP, không AI, không sleep). `guards.assert_not_in_write_txn()` được gọi ở phía BE trước mỗi lời gọi ra ngoài: wrapper provider trong `infrastructure/ai/factory.py` (F04) và client HTTP dùng chung — vi phạm raise ngay trong test/dev. Package AI không import guard này (AI không import BE).
9. Commit chương, state, job, FTS trong cùng một `write` khi phù hợp (Plan §5, §6.2 bước 11).

### B. Migration lúc khởi động (`migrations.prepare_database`, gọi từ F00 bootstrap)

1. Marker `.writestory-data.json` (F00) có `db_initialized=true` mà thiếu `db/app.sqlite3` → `fatal DB_MISSING` (không tự tạo, FL01).
2. Chưa có DB → tạo file, `journal_mode=WAL`, `alembic upgrade head`, đặt `db_initialized=true`.
3. Có DB → đọc revision hiện tại. Revision không có trong script directory của app → `fatal SCHEMA_TOO_NEW` (app cũ hơn dữ liệu). Bằng head → bỏ qua.
4. Có migration chờ → báo `progress stage=migrating` → backup `VACUUM INTO 'backups/pre-migrate/<ts>_<from>_to_<head>.sqlite3.tmp'` rồi rename bỏ `.tmp` (file đích phải chưa tồn tại, Plan §5) → `upgrade head` với `transaction_per_migration=True`.
5. Lỗi → `fatal MIGRATION_FAILED`, `detail = {from_revision, failed_revision, backup_path, error}`; DB ở revision cuối cùng thành công. Thành công → sau khi ready phát `backend.notice {kind:"migration_done", detail:{from, to, backup_path}}`.
6. Giữ 3 bản backup trước migrate gần nhất (giả định); bản cũ hơn do retention xóa.
7. Bản frozen: `script_location` lấy từ resource đã đóng gói (F00 be.md mục F); không đọc `alembic.ini` từ cwd.

### C. Khóa truyện (`jobs/locks.py`, Plan §4.2)

1. `acquire(work_id, job_id)` trong một `write`: xóa dòng có `lease_expires_at < now`; nếu không còn dòng → insert (`lease = now + 60 s`) → `True`; dòng của chính `job_id` → gia hạn → `True`; dòng của job khác → `False`.
2. `False` không phải lỗi: người gọi (scheduler F12) đặt job `waiting_slot`, `wait_reason = 'WORK_BUSY_QUEUED'`, rồi chờ `asyncio.Event` theo `work_id` được set khi `release()`; dự phòng kiểm lại mỗi 30 giây.
3. Heartbeat 15 giây/khóa: cập nhật `heartbeat_at`, `lease_expires_at`. Không thấy dòng của mình → phát tín hiệu `LockLost` cho job (job phải dừng trước commit).
4. `assert_held(ctx, work_id, job_id)` gọi **bên trong** transaction commit của job (fencing): khóa không còn thuộc job → rollback, job `interrupted`.
5. Đọc dữ liệu và sửa tay trên UI không lấy khóa (dùng `expected_revision`).
6. Lúc khởi động xóa mọi dòng `work_locks` (khóa `db/.backend.lock` của F00 bảo đảm chỉ một backend).

### D. FTS tiếng Việt (Plan §5, Review §7.3)

1. `normalize_for_search(text, language)`: gọi `search_normalizer` của gói ngôn ngữ (F08) khi có; mặc định cho `vi`: `unicodedata.normalize("NFC", text)` rồi thay `đ→d`, `Đ→D`. Các dấu khác do tokenizer `remove_diacritics 2` xử lý; chữ hoa/thường do `unicode61` gập.
2. Vì đầu vào đã NFC và `đ→d` là thay 1 ký tự bằng 1 ký tự, `body_norm` có **cùng độ dài code point** với `body` → vị trí khớp trên cột chuẩn hóa dùng trực tiếp để tô sáng văn bản gốc có dấu.
3. `build_match_query(user_query)`: chuẩn hóa như trên, tách từ theo khoảng trắng, bỏ ký tự cú pháp FTS, bọc từng từ trong ngoặc kép (`"nguyen" "van"` = AND); tùy chọn thêm `*` cho từ cuối (tìm khi đang gõ). Không đưa cú pháp FTS thô của người dùng vào `MATCH`.
4. Xếp hạng: `bm25(search_fts, 5.0, 1.0)` (trọng số tiêu đề/thân là giả định), `ORDER BY` tăng dần (nhỏ hơn là khớp hơn).
5. Ghi chỉ mục: `fts.upsert_document(ctx, …)`/`delete_document` chỉ chạm `search_documents`; trigger cập nhật `search_fts`. Gọi trong cùng `write` với thay đổi nguồn.
6. Rebuild: `INSERT INTO search_fts(search_fts) VALUES('rebuild')` (dựng lại từ `search_documents`). Dựng lại `search_documents` từ dữ liệu gốc dùng registry `register_search_indexer(source_type, fn)` do F09 đăng ký. Setting `search.index_version` < `FTS_INDEX_VERSION` của app → tự rebuild nền sau khi ready.
7. Trigram: chỉ khi bật; dùng cho tên riêng/chuỗi con (Plan §5).

### E. Asset (`files/storage.py`, Plan §5)

1. `put_asset(ctx_factory, stream, work_id, kind, mime, original_name)`: ghi `tmp/<uuid>.part` theo khối, tính sha256 khi ghi, `flush + os.fsync`; đóng file.
2. Đích `assets/<work_id|_shared>/<sha256[:2]>/<sha256><ext>`; đã tồn tại cùng hash → xóa file tạm (khử trùng lặp). Chưa có → `os.replace` (cùng filesystem vì đều trong data-root), fsync thư mục cha trên macOS.
3. Sau khi file đã nằm đúng chỗ mới `uow.write` insert `assets` (`status='ready'`). Lỗi ở bước DB → file thành mồ côi, được dọn sau.
4. Dọn mồ côi (nền, sau ready + mỗi 24 giờ): file trong `assets/` không có `rel_path` nào và cũ hơn 24 giờ → xóa; dòng `ready` mà file thiếu → `missing`.
5. `resolve(rel_path)` từ chối đường dẫn thoát khỏi data-root (`..`, tuyệt đối).

### F. Reconcile và retention

1. `jobs/recovery.py`: `register_reconciler(name, fn, order)`; `run_startup_reconcile()` chạy trong `prepare_database` sau migration (báo `progress stage=reconciling`).
2. Reconciler lõi: (a) `jobs.status='running'` → `interrupted`, `interrupted_at=now`, giữ `stage`/`checkpoint_json`; `job_steps.status='running'` → `interrupted`; (b) xóa mọi `work_locks`; (c) xóa toàn bộ `tmp/*` (không tiến trình nào đang dùng). `queued`/`waiting_slot` giữ nguyên để F12 xếp lại.
3. Reconciler của tính năng khác đăng ký thêm (ví dụ F11: candidate `streaming` → `partial`).
4. Sau ready: phát `backend.notice {kind:"jobs_interrupted", detail:{count, job_ids (≤ 50)}}` nếu `count > 0`.
5. `retention.py`: 60 giây sau ready rồi mỗi 24 giờ; xóa theo lô 1.000 dòng mỗi `write`: `job_events` có `ts` cũ hơn 90 ngày, `idempotency_records` hết hạn, backup trước migrate ngoài 3 bản mới nhất. Sau đó `PRAGMA wal_checkpoint(PASSIVE)`.
6. Shutdown (F00 gọi): dừng nhận lệnh mới vào writer queue, xử lý hết lệnh đang chờ (tối đa deadline), `PRAGMA optimize`, `PRAGMA wal_checkpoint(TRUNCATE)` best-effort, đóng engine. Không xóa `-wal`/`-shm` thủ công.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `backend.notice` | Sau ready nếu có job bị gián đoạn | `{kind: "jobs_interrupted", detail: {count, job_ids}}` |
| `backend.notice` | Sau ready nếu vừa migrate | `{kind: "migration_done", detail: {from, to, backup_path}}` |
| `backend.notice` | Rebuild chỉ mục xong/lỗi | `{kind: "search_rebuild_done" \| "search_rebuild_failed", detail: {document_count, error?}}` |

Rebuild ở R1 chạy như tác vụ nền nội bộ (không bền); khi supervisor F12 có, chuyển thành job type `search_reindex`.

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Writer queue đầy/chờ quá hạn | Trả lỗi có thể thử lại | `DB_BUSY` (503) |
| `SQLITE_BUSY` dù có `busy_timeout` (công cụ ngoài mở DB) | Log, trả `DB_BUSY` | `DB_BUSY` |
| Đĩa đầy khi commit | Rollback; `INTERNAL` + `detail.reason="disk_full"`; banner gợi ý dọn dữ liệu (F14) | `INTERNAL` |
| Kill tiến trình giữa transaction | SQLite rollback qua WAL ở lần mở sau; job `interrupted` | — |
| Migration lỗi / DB mới hơn app / DB mất | Xem mục B | `MIGRATION_FAILED`, `SCHEMA_TOO_NEW`, `DB_MISSING` |
| Truy vấn tìm kiếm chỉ có ký tự đặc biệt/rỗng | Trả danh sách rỗng, không lỗi FTS | — |
| `expected_revision` lệch khi `set` setting | 409 | `REVISION_CONFLICT` |
| Hash asset khác sau khi ghi (đọc lại kiểm) | Xóa file tạm, lỗi | `INTERNAL` |
| Đường dẫn asset thoát data-root | Từ chối | `VALIDATION` |
| Mất khóa truyện giữa job (lease hết do treo) | Fencing trong commit → rollback, job `interrupted` | — |

## Việc cần làm

- [ ] `engine.py` với pragma, `isolation_level=None`, sự kiện `begin`; test xác nhận pragma trên mọi connection.
- [ ] `base.py` naming convention; `models/system.py`.
- [ ] `writer.py`, `unit_of_work.py`, `guards.py`.
- [ ] `migrations/env.py` (batch mode, loại FTS khỏi autogenerate), `0001_baseline.py`, `0002_search.py`.
- [ ] `migrations.prepare_database()` + mã `fatal` cho F00.
- [ ] `jobs/locks.py` (acquire/heartbeat/release/assert_held).
- [ ] `fts.py` + bộ test tiếng Việt Review §7.3.
- [ ] `files/storage.py` + dọn mồ côi.
- [ ] `jobs/recovery.py`, `retention.py`; hook shutdown.
- [ ] `repositories/settings.py`, `repositories/jobs.py`.
- [ ] `GET /v1/system/info`, `POST /v1/system/search-index/rebuild`.
- [ ] Đo ở R1 (ghi ADR): thời gian commit p50/p95 khi 5 writer song song, kích thước WAL, thời gian `VACUUM INTO` với DB thử nghiệm.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | `normalize_for_search`: NFC, `đ→d`, giữ độ dài; `build_match_query` thoát cú pháp | `be/tests/unit/db/test_fts_normalize.py` |
| integration | FTS: "nguyen"/"Nguyễn"/"duong"/"Đường"/"oc"/"Ộc" tìm thấy; `bm25` ưu tiên tiêu đề; rebuild cho cùng kết quả | `be/tests/integration/db/test_fts_vietnamese.py` |
| integration | Pragma (`journal_mode=wal`, `foreign_keys=1`, `synchronous=2`, `busy_timeout`) trên cả hai engine; read engine không ghi được | `be/tests/integration/db/test_engine_pragmas.py` |
| integration | Writer queue: lệnh tuần tự, lỗi rollback không phát event, quá hạn → `DB_BUSY`, `assert_not_in_write_txn` bắt vi phạm | `be/tests/integration/db/test_writer_queue.py` |
| integration | 5 task commit liên tục + reader song song, 0 lỗi `database is locked` (chạy rút gọn trong CI, bản dài đánh dấu `slow`) | `be/tests/integration/db/test_concurrent_commits.py` |
| integration | Migration: DB mới; DB cũ có migration chờ → có backup; migration lỗi giả → `MIGRATION_FAILED` + revision cũ; revision lạ → `SCHEMA_TOO_NEW`; marker có mà DB mất → `DB_MISSING` | `be/tests/integration/db/test_migrations.py` |
| integration | Khóa: acquire/queue/release, lease hết hạn, heartbeat mất → `LockLost`, fencing rollback | `be/tests/integration/jobs/test_work_locks.py` |
| integration | Asset: ghi thành công, trùng hash, lỗi DB sau rename → mồ côi được dọn, đường dẫn `..` bị từ chối | `be/tests/integration/files/test_storage.py` |
| integration | Reconcile: job `running` → `interrupted`, khóa bị xóa, `tmp/` sạch, notice phát sau ready | `be/tests/integration/jobs/test_recovery.py` |
| integration | Kill tiến trình con đang commit (subprocess) → mở lại DB toàn vẹn (`PRAGMA integrity_check = ok`) | `tests/integration/test_crash_during_commit.py` |

## Tên mới đề xuất

- Bảng: `search_documents`, `search_fts`, `search_trigram`; cột chi tiết của `settings`, `jobs` (gồm `wait_reason`, `pinned_json`, `interrupted_at`, `revision`), `job_steps`, `work_locks` (`owner_id`, `lease_expires_at`), `assets` (`rel_path`, `sha256`, `status`) — Plan §5 chỉ nêu tên bảng.
- Migration: `0001_baseline.py`, `0002_search.py`. Thư mục backup `data/backups/pre-migrate/`.
- File: `infrastructure/db/base.py`, `models/system.py`, `writer.py`, `guards.py`, `migrations.py`, `retention.py`, `repositories/settings.py`, `repositories/jobs.py`.
- Kiểu/hàm: `UnitOfWork`, `WriteContext` (`add_event`, `after_commit`), `WriterQueue`, `assert_not_in_write_txn`, `prepare_database`, `WorkLockManager`, `LockLost`, `register_reconciler`, `run_startup_reconcile`, `register_search_indexer`, `normalize_for_search`, `build_match_query`, `put_asset`, `FTS_INDEX_VERSION`.
- API: `GET /v1/system/info`, `POST /v1/system/search-index/rebuild`.
- Setting key: `search.index_version`, `search.trigram_enabled`.
- `backend.notice` kind: `search_rebuild_done`, `search_rebuild_failed`; job type tương lai `search_reindex`.
