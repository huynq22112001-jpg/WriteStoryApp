# T16 — Xuất và sao lưu

Tính năng: F13. Nguồn: Plan FL25, §5 (backup `VACUUM INTO`, WAL, asset ghi tạm rồi rename), §7 (`/exports`, `/backups`), §23.4 #6, §21 (Export/backup), §9 Giai đoạn 5; Review §7.2. Cấp test chính: integration, e2e-fe.

## Mục đích

Chứng minh export ra đúng revision đã commit với Unicode nguyên vẹn, backup tạo được snapshot nhất quán ngay cả khi nhiều truyện đang viết (bằng `VACUUM INTO` ra file tạm rồi rename), backup không lồng và không chứa key plaintext, và restore chỉ báo thành công khi đã thay dữ liệu đầy đủ, có bản lưu hiện trạng để quay lại.

## Tiền điều kiện và dữ liệu

- Data-root tạm có `tien_hiep_01_10ch` (10 chương, có 2 asset ảnh), `do_thi_01` (3 chương); ch.5 của `tien_hiep_01_10ch` có working copy chưa chụp revision (khác revision hiện tại).
- Vault đã tạo với key giả `sk-test-WSA-0123456789abcdef`.
- Mock provider cho kịch bản đang viết: `{latency_ms: 100, tokens_per_sec: 100, scripted_outputs: <bộ 20 chương như T07>}`, 3 truyện auto-write song song.
- Công cụ kiểm EPUB: `epubcheck` (CI) nếu có; nếu không, kiểm cấu trúc zip + `mimetype` + OPF.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T16-01 | thành công | `POST /v1/exports` `{work_id, format: txt, chapters: 1-10, include_titles: true}`; lặp với `md`, `epub`. | File ghi vào `data/tmp/` rồi rename vào `data/exports/<work-id>/`; nội dung = revision committed (ch.5 dùng revision, KHÔNG dùng working copy); thứ tự chương đúng; văn bản NFC, dấu tiếng Việt nguyên vẹn; có receipt ghi source revision + hash từng chương. | integration | `be/tests/integration/test_export_formats.py` |
| T16-02 | thành công | Mở EPUB bằng `epubcheck` và trình đọc. | 0 lỗi `epubcheck`; metadata `dc:language=vi`, tiêu đề, tác giả; font hiển thị tiếng Việt đúng. | integration, thủ công | `be/tests/integration/test_export_epub_valid.py` |
| T16-03 | biên | Export khoảng ch.3–7, không tiêu đề chương; tên truyện có dấu "Kiếm Hồn: Thượng/Hạ". | Chỉ 5 chương; tên file an toàn trên Windows/macOS (ký tự `:`/`/` được thay), giữ dấu tiếng Việt. | integration | `be/tests/integration/test_export_range_filename.py` |
| T16-04 | lỗi | Tiêm lỗi ghi file (đĩa đầy giả) giữa export. | Không có file dở trong `data/exports/`; file tạm bị dọn; lỗi trả rõ ràng; không ghi receipt. | integration | `be/tests/integration/test_export_disk_full.py` |
| T16-05 | thành công | `POST /v1/backups` khi app nhàn. | Tạo `data/backups/<ts>/` gồm `app.sqlite3` (qua `VACUUM INTO` ra file tạm rồi rename, file đích chưa tồn tại trước đó), manifest asset có checksum, schema version, manifest/checksum tổng; `PRAGMA integrity_check` của bản backup = `ok`. | integration | `be/tests/integration/test_backup_basic.py` |
| T16-06 | thành công | 3 truyện đang auto-write (commit liên tục); `POST /v1/backups` 5 lần cách nhau 3 s. | Mỗi backup hoàn tất (không bị khởi động lại vô hạn như Backup API từng bước); mỗi bản là snapshot nhất quán: với mọi chương có `chapter_revisions` trong backup thì có đủ `story_states`/`chapter_handoffs` cùng chương (không có commit nửa vời); commit của các truyện vẫn tiếp tục trong lúc backup, 0 lỗi `database is locked`; ghi thời gian writer bị chờ. | integration | `be/tests/integration/test_backup_during_writing.py` |
| T16-07 | biên | Đã có 3 bản trong `data/backups/`; tạo backup thứ 4 với giới hạn giữ 3. | Bản mới không chứa thư mục `backups/` (không lồng); bản cũ nhất bị xóa theo giới hạn; tổng số bản = 3. | integration | `be/tests/integration/test_backup_retention_no_nesting.py` |
| T16-08 | bảo mật | Backup không chọn kèm vault; rồi backup có kèm vault. | Không kèm: không có `secrets.enc`. Kèm: chỉ có `secrets.enc` đã mã hóa. Cả hai: grep `sk-test-WSA` trong thư mục backup = 0. | integration | `be/tests/integration/test_backup_no_plaintext_key.py` |
| T16-09 | thành công | Restore bản backup T16-05 sau khi đã viết thêm 2 chương. | Trước restore tự tạo backup hiện trạng; job đang chạy được dừng (`interrupted`) và writer đóng; dữ liệu thay bằng bản backup; FTS được rebuild; số chương, nội dung (hash) khớp bản backup; event `backend.notice` báo restore xong; các job sau restore không trỏ dữ liệu không tồn tại. | integration | `be/tests/integration/test_restore.py` |
| T16-10 | lỗi | Restore bản có checksum asset sai hoặc DB hỏng. | Validate thất bại trước khi thay dữ liệu; dữ liệu hiện tại không đổi (hash DB trước/sau bằng nhau); báo lỗi cụ thể, không báo đã restore. | integration | `be/tests/integration/test_restore_invalid.py` |
| T16-11 | phục hồi | Tiêm lỗi giữa bước thay dữ liệu khi restore (copy asset thứ 2 thất bại); và kill backend ở cùng điểm. | Tự quay về backup hiện trạng tạo ở đầu restore; dữ liệu giống trước restore; không trạng thái "restore một phần"; sau kill + khởi động lại, app phát hiện restore dở và hoàn tác. | integration | `be/tests/integration/test_restore_partial_failure.py` |
| T16-12 | biên | Restore bản backup có schema version cũ hơn head. | Migrate lên head sau khi thay; dữ liệu giữ nguyên; bản backup có schema mới hơn app hiện tại bị từ chối rõ ràng. | integration | `be/tests/integration/test_restore_schema_version.py` |
| T16-13 | lỗi | Ép `VACUUM INTO` vào đường dẫn đích đã tồn tại. | Không ghi đè: lỗi được bắt, dùng tên tạm mới hoặc báo lỗi; không có file backup hỏng nằm trong `data/backups/`. | unit, integration | `be/tests/unit/test_backup_target_exists.py` |
| T16-14 | hủy | Hủy export EPUB lớn (truyện 220 chương) đang chạy. | Không file dở trong `data/exports/`; file tạm bị dọn; không receipt. | integration | `be/tests/integration/test_export_cancel.py` |
| T16-15 | thành công | FE: hộp thoại export (định dạng, khoảng chương, metadata, có/không tiêu đề) và trang Dữ liệu (backup/restore). | Hộp thoại gửi đúng tham số; restore yêu cầu xác nhận và hiển thị bản sẽ thay thế; lỗi hiển thị theo `code`. | e2e-fe | `fe/tests/e2e/export_backup.spec.ts` |
| T16-16 | phục hồi | Copy cả thư mục data khi app đã đóng (kể cả `-wal` nếu còn) sang máy/OS khác và mở. | Mở được, dữ liệu đủ; vault mở bằng mật khẩu cũ (liên quan T02-14). | thủ công | `tests/desktop/data_folder_move.md` |

## Kiểm tra dữ liệu sau test

- File: `data/exports/<work-id>/` chỉ chứa file hoàn chỉnh; `data/backups/<ts>/` có DB, manifest asset + checksum, schema version; không thư mục backup nào chứa `backups/`; `data/tmp/` sạch.
- DB: receipt export ghi source revision/hash; bản backup qua `integrity_check`; sau restore FTS rebuild khớp số chương.
- Event: `backend.notice` cho backup/restore xong hoặc lỗi; `job.state` `interrupted` cho job bị dừng khi restore.

## Tiêu chí pass

- 5/5 backup trong lúc 3 truyện đang viết hoàn tất và nhất quán; 0 lỗi `database is locked`.
- 0 file export/backup dở trong thư mục đích qua mọi kịch bản lỗi/hủy.
- 0 lần báo "đã restore" khi dữ liệu chưa thay đầy đủ; mọi lỗi restore để dữ liệu hiện tại nguyên vẹn (so hash).
- 0 API key plaintext trong backup.
- Export dùng đúng revision committed: hash nội dung export = hash revision hiện tại của từng chương.

## Ghi chú thủ công

- Mở file TXT/MD bằng Notepad (Windows) và TextEdit (macOS) kiểm mã hóa UTF-8 và dấu; mở EPUB bằng Apple Books và một trình đọc trên Windows.

## Tên mới đề xuất

- `GET /v1/backups`, `POST /v1/backups/{id}/restore` (§7 chỉ có `POST /v1/backups`).
- Body `POST /v1/exports`: `{work_id, format: txt/md/epub, chapters, include_titles, metadata}`; dùng bảng `export_receipts`, `backup_manifests` (§18).
- Cấu hình `backup_retention_count`; tùy chọn `include_vault`.
