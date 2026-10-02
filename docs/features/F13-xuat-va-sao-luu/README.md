# F13 — Xuất và sao lưu

Giai đoạn: R2. Trạng thái: planned.

## Mục tiêu

Tác giả xuất truyện ra TXT, Markdown hoặc EPUB theo khoảng chương, biết chắc file xuất đúng phiên bản nào; sao lưu toàn bộ dữ liệu app một cách nhất quán ngay cả khi nhiều truyện đang viết; khôi phục từ bản sao lưu mà không mất dữ liệu hiện tại nếu khôi phục thất bại.

## Phạm vi

- Trong phạm vi:
  - Export TXT/Markdown/EPUB: khoảng chương, metadata, có/không tiêu đề chương, chuẩn hóa NFC, ghi file tạm rồi rename vào `data/exports/<work-id>/`, export receipt có source revision/hash (Plan §5, §9 Giai đoạn 5, FL25 bước 1–2, Plan §23.4 #6).
  - Backup toàn bộ data-root: `VACUUM INTO` ra file tạm + rename, manifest asset có checksum, schema version, tùy chọn kèm vault mã hóa, không lồng backup, giới hạn số bản giữ (Plan §5, FL25 bước 3).
  - Restore: validate schema/checksum, backup hiện trạng trước, đóng writer, thay dữ liệu, rebuild FTS (FL25 bước 4).
  - FE: hộp thoại export, trang Dữ liệu (backup/restore) trong Cài đặt (UI §5.6.3, §5.8).
- Ngoài phạm vi:
  - Import truyện/InkOS migration (FL25 bước 5, FL10 – R3/R7).
  - Backup/restore riêng từng tác phẩm (WRK09) – MVP chỉ backup cả data-root; tách tác phẩm để sau.
  - Bìa EPUB (IMG, R4); export JSON/Ink/HTML (R5–R6).
  - Backup tự động theo lịch (R7); backup trước migration thuộc F02 nhưng dùng chung routine của F13.
  - Trang Lưu trữ/dọn dẹp (F14).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F02 | Engine SQLite, writer queue, Alembic head, FTS rebuild, bảng `assets` có checksum |
| F07 | `chapter_revisions` (Tiptap JSON + plain text), `current_revision_id`, working copy để cảnh báo chưa lưu |
| F03 | Vault `secrets.enc` (đưa vào backup tùy chọn; khóa/mở sau restore) |
| F12 | Tạm dừng scheduler/đợi job dừng khi restore (chế độ bảo trì) |
| F01 | Job/event `job.step` cho tiến độ, mã lỗi |

## Nguồn thiết kế

- Plan §3.1 (thư mục data), §5 (backup bằng `VACUUM INTO`, Markdown/TXT/EPUB là dữ liệu xuất, asset ghi tạm + rename), §7 (`POST /v1/exports`, `POST /v1/backups`), §9 Giai đoạn 1 và 5, §18 (`export_receipts`, `backup_manifests`, `data/exports/<work-id>/`), §21 dòng "Export/backup, FL25", §23.4 #6.
- FL25; FL01 bước 3 (backup trước migrate).
- Arch §5 (`infrastructure/files/backup.py`, `export.py`), §10.
- UI §5.6 (mục Dữ liệu), §5.8 (hộp thoại export).
- Review §7.2 (Backup API khởi động lại khi có ghi xen giữa; `VACUUM INTO` nhất quán).
- Mã Plan §15: OPS07, WRK09 (một phần), EDT12 (export đúng revision ghim, R3 phần stale).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | `export_receipts`, `backup_manifests`; job export/backup/restore; định dạng TXT/MD/EPUB; chế độ bảo trì khi restore |
| FE | [fe.md](./fe.md) | `ExportDialog`, lịch sử export + cảnh báo đã cũ, trang Dữ liệu: tạo/xác minh/ghim/xóa/khôi phục backup |
| AI | [ai.md](./ai.md) | Không áp dụng |

## Tiêu chí hoàn thành

- [ ] File xuất luôn khớp đúng các revision ghi trong receipt (hash nội dung từng chương khớp).
- [ ] Văn bản tiếng Việt NFC xuất rồi đọc lại giữ đúng nội dung (Plan §9 Giai đoạn 2 "Unicode xuất/nhập lại"); EPUB qua epubcheck không lỗi (khi có epubcheck trong CI).
- [ ] Không có file xuất dở dang trong `data/exports/` khi export lỗi/hủy.
- [ ] Backup trong lúc 3 truyện đang auto-write thành công, DB backup qua `PRAGMA integrity_check`, không gây `database is locked`.
- [ ] `data/backups/` không bao giờ nằm trong backup; số bản tự động giữ không vượt giới hạn.
- [ ] Restore lỗi giữa chừng → dữ liệu hiện tại được trả lại nguyên vẹn; restore thành công → FTS dùng được, job cũ `interrupted`.
- [ ] Các test luồng liên quan pass: [T16](../../tests/flows/T16-xuat-va-sao-luu.md), [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md) (phần đóng writer).

## Rủi ro và câu hỏi mở

- `VACUUM INTO` giữ một read transaction dài với DB lớn → WAL có thể phình tạm thời do checkpoint không hoàn tất; cần đo ở R2 với corpus 10.000 chương (Plan §4.4).
- EPUB: tự viết bằng `zipfile` hay dùng thư viện (ví dụ ebooklib) – chưa chốt; ưu tiên ít phụ thuộc. Nhúng font Noto Serif (OFL) làm EPUB to hơn; mặc định không nhúng (giả định).
- Restore bản backup từ schema mới hơn app hiện tại: từ chối (không hạ cấp schema, Plan §10 "Rollback DB schema cần chính sách riêng").
- Vault trong backup có thể dùng mật khẩu khác vault hiện tại; sau restore vault ở trạng thái khóa.
- FL25 nói "SQLite backup API" còn Plan §5 chọn `VACUUM INTO`; F13 dùng `VACUUM INTO` (xem báo cáo mâu thuẫn).
