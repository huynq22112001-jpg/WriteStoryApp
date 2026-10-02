# F13 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/works/$workId` (menu ⋯ của workspace, Ctrl+K "Xuất truyện") | `ExportDialog` (Plan §23.4 #6, UI §5.8) | Hộp thoại, không phải route riêng |
| `/settings/data` | Dữ liệu: data-root, backup/restore (UI §5.6.3) | Section `data` của `/settings/$section` |
| `/settings/data?tab=exports` | Lịch sử export mọi truyện | Danh sách receipt, mở thư mục |

## Component

```text
fe/src/features/export/
  components/ExportDialog.tsx, ExportHistoryList.tsx, ChapterRangeInput.tsx
  api/exports.ts
  index.ts
fe/src/features/backup/
  pages/DataSettingsPage.tsx
  components/BackupList.tsx, CreateBackupButton.tsx, RestoreDialog.tsx,
             MaintenanceOverlay.tsx
  api/backups.ts
  index.ts
```

| Component | Trách nhiệm |
|---|---|
| `ExportDialog` | Định dạng TXT/Markdown/EPUB; khoảng chương (mặc định toàn bộ đã commit); có/không tiêu đề chương; metadata (tên, tác giả, mô tả, bật/tắt); cảnh báo "Ch.12 có thay đổi chưa tạo phiên bản – bản xuất dùng phiên bản đã lưu" kèm nút "Tạo phiên bản ngay" (snapshot F07); [Xuất] |
| `ChapterRangeInput` | Hai ô số + chọn nhanh "Toàn bộ / Quyển hiện tại / 10 chương cuối"; validate bằng zod |
| `ExportHistoryList` | Receipt: định dạng, khoảng chương, thời điểm, kích thước, badge "đã cũ" khi `stale`; [Mở thư mục] [Xóa] |
| `DataSettingsPage` | Đường dẫn data-root (chỉ đọc; macOS đổi data-root thuộc F00), danh sách backup, nút tạo, nhập file backup từ ngoài |
| `CreateBackupButton` | Tùy chọn "Kèm vault đã mã hóa", nhãn; theo dõi tiến độ qua `job.step` |
| `BackupList` | Thời điểm, loại (thủ công/trước khôi phục/trước nâng cấp), kích thước, schema version, ghim 📌, [Xác minh] [Lưu bản sao ra ngoài] [Khôi phục] [Xóa] |
| `RestoreDialog` | Bước 1 xác minh (gọi `verify`, hiện kết quả); bước 2 cảnh báo: "Các truyện đang viết sẽ dừng. Dữ liệu hiện tại sẽ được sao lưu trước."; tùy chọn khôi phục vault; gõ xác nhận; bước 3 tiến độ |
| `MaintenanceOverlay` | Toàn màn khi `backend.notice maintenance_on`: "Đang khôi phục dữ liệu…"; khi `restored` → `queryClient.clear()` rồi tải lại app |

Mở thư mục / chọn file đi qua `shared/desktop/bridge.ts`: Tauri dialog plugin (`open`, `save`) và opener plugin (reveal), có mock cho web-dev; FE ghép `data-root` + `file_relpath` để reveal. Không đọc/ghi file trực tiếp từ FE.

## State và dữ liệu

- TanStack Query keys: `['exports', workId]`, `['exports', 'all']`, `['backups']`, `['chapters', workId]` (lấy khoảng chương), `['workingCopyStatus', workId]` (F07, cảnh báo chưa lưu).
- Zustand: không cần; trạng thái bảo trì giữ trong `features/jobs` store toàn cục (`maintenance: boolean`).
- API dùng: `POST /v1/exports`, `GET /v1/works/{id}/exports`, `DELETE /v1/exports/{id}`, `GET/POST /v1/backups`, `PATCH/DELETE /v1/backups/{id}`, `POST /v1/backups/{id}/verify`, `POST /v1/backups/{id}/copy-to`, `POST /v1/backups/restore`.
- Event SSE dùng (`/v1/events`): `job.state`/`job.step` cho job export/backup/restore; `backend.notice` (`maintenance_on|off`, `restored`).

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton danh sách |
| Rỗng | Backup: "Chưa có bản sao lưu. Nên sao lưu thường xuyên và giữ một bản ngoài máy." + [Tạo bản sao lưu]; Export: "Chưa xuất lần nào" |
| Đang chạy | Thanh tiến độ theo `stage` (snapshot/assets/package…); nút hủy cho export |
| Lỗi `VALIDATION` | Lỗi tại ô khoảng chương |
| Lỗi `BACKUP_INVALID` | "Bản sao lưu hỏng hoặc không đúng định dạng" + chi tiết `problems[]` |
| Lỗi `BACKUP_INCOMPATIBLE` | "Bản sao lưu từ phiên bản app mới hơn – hãy cập nhật app" |
| Lỗi `MAINTENANCE` | "Đang khôi phục dữ liệu, thử lại sau" |
| Lỗi `STORAGE_FULL` | "Ổ đĩa đầy" + [Mở trang Lưu trữ] (F14) |
| Thành công export | Toast sonner "Đã xuất 120 chương (EPUB, 1,2 MB)" + [Mở thư mục] |
| Thành công restore | App tải lại, toast "Đã khôi phục từ bản 02/10/2026 14:30; bản trước khôi phục đã được lưu" |

## Tương tác, phím tắt, khả năng tiếp cận

- Ctrl+K có lệnh "Xuất truyện…", "Tạo bản sao lưu".
- `RestoreDialog` không đóng bằng Esc khi đang chạy; focus trap của Base UI; nút nguy hiểm màu đỏ có chữ, không chỉ màu.
- Kích thước hiển thị theo `Intl.NumberFormat('vi')` (ví dụ "1,2 MB").

## Chuỗi giao diện (i18n)

Namespace `export`, `backup`. Ví dụ khóa: `export.format.epub`, `export.range.all`, `export.unsaved_warning`, `export.stale_badge`, `backup.create`, `backup.include_vault`, `backup.kind.pre_restore`, `backup.restore.confirm_type`, `backup.error.BACKUP_INCOMPATIBLE`. MVP chỉ có `vi`.

## Việc cần làm

- [ ] `ExportDialog` + `ChapterRangeInput` + cảnh báo working copy.
- [ ] `ExportHistoryList` + reveal qua bridge.
- [ ] `DataSettingsPage`, `BackupList`, `CreateBackupButton`.
- [ ] `RestoreDialog` 3 bước + chọn file ngoài bằng dialog plugin.
- [ ] `MaintenanceOverlay` + xóa cache query khi restore xong.
- [ ] Mock bridge cho web-dev/Playwright.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | Validate khoảng chương, cảnh báo working copy | `fe/src/features/export/components/ExportDialog.test.tsx` |
| component | Restore cần xác nhận, không đóng khi đang chạy | `fe/src/features/backup/components/RestoreDialog.test.tsx` |
| e2e (mock backend) | Export EPUB → receipt → sửa chương → badge "đã cũ" (T16) | `fe/tests/e2e/export.spec.ts` |
| e2e (mock backend) | Backup khi đang viết; restore → overlay → reload (T16) | `fe/tests/e2e/backup-restore.spec.ts` |

## Tên mới đề xuất

- Route section `/settings/data` và tham số `?tab=exports`.
- Feature folder `fe/src/features/export/`, `fe/src/features/backup/` (Arch §9 chỉ nêu `storage`, `logs`… cho OPS).
- Store field `maintenance` trong `features/jobs`.
- Namespace i18n `export`, `backup`.
