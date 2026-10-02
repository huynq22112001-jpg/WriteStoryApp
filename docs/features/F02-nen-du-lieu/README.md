# F02 — Nền dữ liệu

Giai đoạn: R1. Trạng thái: planned.

## Mục tiêu

Dữ liệu của người dùng nằm an toàn trong `data/db/app.sqlite3`: tồn tại sau restart và crash, nâng cấp schema tự động có backup trước, nhiều truyện commit gần nhau không gây `database is locked`, tìm kiếm tiếng Việt có/không dấu (kể cả `đ`) hoạt động, file asset không bao giờ được đánh dấu xong khi chưa thật sự nằm trên đĩa. Sau khi mở lại app, tác vụ đang chạy dở được đánh dấu `interrupted` thay vì treo mãi ở `running`.

## Phạm vi

- Trong phạm vi:
  - SQLite WAL + pragma (`foreign_keys`, `busy_timeout`, `synchronous=FULL`), hai engine đọc/ghi, cấu hình transaction tường minh cho aiosqlite.
  - SQLAlchemy 2 async, `unit_of_work` (đọc/ghi), writer queue một task, outbox sự kiện cho F01.
  - Alembic: baseline, quy ước đặt tên, batch mode cho SQLite, chạy lúc khởi động với backup `VACUUM INTO` trước khi migrate, chặn DB mới hơn app.
  - Bảng hạ tầng: `settings`, `jobs`, `job_steps`, `job_events` (định nghĩa ở F01), `idempotency_records` (F01), `work_locks`, `assets`, `search_documents` + `search_fts`.
  - `work_locks` lease + heartbeat, hàng đợi khi bận (không fail-fast).
  - Hạ tầng FTS5: tokenizer `unicode61 remove_diacritics 2`, cột chuẩn hóa `đ→d` ở tầng app, trigram tùy chọn, `bm25()`, rebuild.
  - Asset: ghi file tạm → fsync → rename → commit metadata; dọn file mồ côi và `tmp/`.
  - Retention cơ bản (`job_events` 90 ngày, `idempotency_records` hết hạn, `tmp/`), `PRAGMA optimize`/checkpoint WAL khi tắt.
  - Reconcile lúc khởi động: job `running` → `interrupted`, xóa khóa cũ, registry để tính năng khác gắn thêm bước reconcile.
- Ngoài phạm vi:
  - Bảng nghiệp vụ (`works`, `chapters`, …) → tính năng sở hữu (F05, F07, F09…).
  - Ngữ nghĩa scheduler, resume job → F12. Nội dung đưa vào chỉ mục và API tìm kiếm → F09. Backup/restore người dùng → F13. Trang Lưu trữ, dọn dẹp theo dung lượng → F14.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F00 | Data-root tuyệt đối, bootstrap gọi hook `prepare_database`, báo tiến độ/lỗi migration cho Rust |
| F01 | Định nghĩa `job_events`, `idempotency_records`, `ErrorCode` (`DB_BUSY`), `EventBus` dùng outbox |

## Nguồn thiết kế

- Plan §2 (SQLite WAL, SQLAlchemy 2 async, aiosqlite, Alembic; FTS5), §4.1, §4.2 (khóa truyện, writer queue, `busy_timeout`), §4.3 (trạng thái job, reconcile, idempotency key), §4.4 (index theo work/chapter/status/revision), §5 (bảng, pragma, `synchronous=FULL`, asset temp+rename, FTS5, backup `VACUUM INTO`), §18 (migration theo giai đoạn), FL01 bước 3, §23.2 #10 (retention).
- Arch §5 (`infrastructure/db/engine.py`, `models/`, `repositories/`, `unit_of_work.py`, `fts.py`, `files/storage.py`, `jobs/recovery.py`, `jobs/locks.py`), §10 (ownership của data), §12 (transaction không bao quanh AI call).
- Review §5.4, §7 (WAL), §7.2 (AsyncSession, aiosqlite, backup), §7.3 (FTS5 tiếng Việt đã chạy thử).
- Mã feature Plan: NEW04 (SQLite canonical transaction, checkpoint bền).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Engine, pragma, UoW, writer queue, migration, bảng hạ tầng, khóa, FTS, asset, retention, reconcile |
| FE | [fe.md](./fe.md) | Rất ít: thẻ "Thông tin dữ liệu" trong Cài đặt → Dữ liệu và nút xây lại chỉ mục |
| AI | [ai.md](./ai.md) | Không áp dụng |

## Tiêu chí hoàn thành

- [ ] Tạo dữ liệu → tắt app → mở lại: dữ liệu còn nguyên; kill tiến trình backend giữa lúc ghi → mở lại không hỏng DB, transaction dở bị rollback.
- [ ] DB cũ có migration chờ → có file backup trước migrate trong `data/backups/`; migration lỗi → DB giữ revision cũ, app báo `MIGRATION_FAILED` (F00), không tạo DB mới ở chỗ khác (FL01).
- [ ] DB có schema mới hơn app → từ chối mở (`SCHEMA_TOO_NEW`).
- [ ] 5 tác vụ giả commit đồng thời liên tục trong 10 phút với một editor autosave song song → 0 lỗi `database is locked` (Plan §4.4, mục tiêu cần đo).
- [ ] Tìm "nguyen", "Nguyễn", "duong", "Đường", "oc" (trong "Ộc") đều ra kết quả đúng (Review §7.3).
- [ ] Asset: kill giữa lúc ghi → không có bản ghi `assets` trỏ tới file không tồn tại; file mồ côi được dọn ở lần khởi động sau.
- [ ] Khởi động lại sau crash: mọi job `running` thành `interrupted`, `work_locks` trống, FE nhận `backend.notice jobs_interrupted`.
- [ ] Không transaction nào bao quanh lời gọi AI (kiểm bằng test kiến trúc/lint rule).
- [ ] Các test luồng liên quan pass: [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md) (phần kill/interrupted), [T16](../../tests/flows/T16-xuat-va-sao-luu.md) (phần backup trước migrate, WAL snapshot); phần khởi động của [T01](../../tests/flows/T01-khoi-dong-va-data-root.md).

## Rủi ro và câu hỏi mở

- Cấu hình transaction của aiosqlite qua SQLAlchemy (tắt transaction ngầm của driver, tự phát `BEGIN`/`BEGIN IMMEDIATE`) phải thử thực tế ở R1 (Review §7.2); công thức trong be.md lấy theo tài liệu dialect SQLite của SQLAlchemy.
- Phiên bản SQLite đi kèm CPython 3.14 trên Windows/macOS (và trong bundle PyInstaller) quyết định có `contentless_delete`, tùy chọn `remove_diacritics` của tokenizer trigram hay không; be.md chọn cách không phụ thuộc các tính năng mới đó, trigram để tùy chọn.
- Plan §5 ưu tiên `VACUUM INTO` cho backup, nhưng FL25 bước 3 ghi "Backup dùng SQLite backup API". F02 dùng `VACUUM INTO` cho backup trước migrate; F13 cần thống nhất lại FL25.
- Plan §18 có `retrieval_documents/FTS` cho nhóm Materials; F02 đề xuất bảng projection chung `search_documents` + `search_fts`. Cần quyết định hợp nhất (một chỉ mục có `source_type`) hay tách khi tới R3.
- `jobs.work_id` chưa có khóa ngoại vì bảng `works` (F05) tạo sau; F05 thêm FK bằng batch migration hoặc giữ tham chiếu mềm — cần chốt cùng chính sách xóa tác phẩm (WRK09).
- Lease/heartbeat của `work_locks` (60 s/15 s) và `busy_timeout` 5.000 ms là giả định, chỉnh sau đo.
