# F02 — Frontend

F02 là hạ tầng dữ liệu phía backend; phần giao diện **rất nhỏ** và không có màn hình riêng. Những gì người dùng thấy liên quan tới dữ liệu được các tính năng khác sở hữu:

- Màn lỗi migration, `SCHEMA_TOO_NEW`, `DB_MISSING` lúc khởi động → F00 (`StartupErrorScreen`).
- Tác vụ bị gián đoạn sau crash và nút tiếp tục → F12 (Phòng viết) và F14 (trung tâm thông báo).
- Dung lượng DB/asset/log và dọn dẹp → F14 (trang Lưu trữ). Backup/restore → F13.
- Ô tìm kiếm có nguồn chương/đoạn → F09.

F02 chỉ thêm một thẻ thông tin trong Cài đặt → Dữ liệu và một toast khi vừa nâng cấp dữ liệu.

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/settings/data` | Mục "Dữ liệu" (UI §5.6.3) — F02 đóng góp thẻ `DataInfoCard` | Các phần khác của trang do F00 (data-root), F13 (backup) bổ sung |

## Component

```text
fe/src/features/settings/
  components/DataInfoCard.tsx     Đường dẫn data-root, phiên bản schema, SQLite, kích thước DB/WAL, chỉ mục tìm kiếm
  api/systemInfo.ts               useSystemInfo(), useRebuildSearchIndex()
fe/src/app/
  noticeHandlers.ts               Toast cho backend.notice migration_done / search_rebuild_* (đăng ký vào event bus F01)
```

| Component | Trách nhiệm |
|---|---|
| `DataInfoCard` | Hiển thị `data_root` (nút sao chép; nút "Mở thư mục" gọi command F00 nếu được thêm, nếu không chỉ sao chép), `schema_revision` (cảnh báo nếu khác `schema_head` — không nên xảy ra), `sqlite_version`, `db_size_bytes`, `wal_size_bytes` định dạng KB/MB, số tài liệu chỉ mục. Nút "Xây lại chỉ mục tìm kiếm" → xác nhận → `POST /v1/system/search-index/rebuild`; khi `search.rebuilding=true` nút bị khóa kèm spinner |
| `noticeHandlers` | `migration_done` → toast "Đã nâng cấp dữ liệu (bản sao lưu trước nâng cấp: …)"; `search_rebuild_done` → toast thành công và invalidate `['system','info']`; `search_rebuild_failed` → toast lỗi kèm nút thử lại |

## State và dữ liệu

- TanStack Query keys: `['system', 'info']` (staleTime 30 giây).
- Zustand store: không có.
- API dùng: `GET /v1/system/info`, `POST /v1/system/search-index/rebuild` (gửi `Idempotency-Key`).
- Event SSE dùng (`/v1/events`): `backend.notice` với `kind ∈ migration_done | search_rebuild_done | search_rebuild_failed | jobs_interrupted` (`jobs_interrupted` chỉ chuyển cho F12/F14 xử lý, F02 không hiển thị).

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton 5 dòng trong thẻ |
| Rỗng | Không áp dụng (luôn có dữ liệu khi backend ready) |
| Lỗi (`code`) | `ErrorState` (F01) trong thẻ; `DB_BUSY` → nút thử lại |
| Thành công | Bảng thông tin; toast khi rebuild xong |

## Tương tác, phím tắt, khả năng tiếp cận

- Thẻ dùng danh sách mô tả (`<dl>`) để trình đọc màn hình đọc cặp nhãn–giá trị.
- Nút xây lại chỉ mục có hộp thoại xác nhận nói rõ: không mất dữ liệu, tìm kiếm có thể thiếu kết quả trong lúc xây.
- Không có phím tắt.

## Chuỗi giao diện (i18n)

Namespace `settings`, ví dụ khóa: `settings.data.info.title`, `settings.data.info.dataRoot`, `settings.data.info.schema`, `settings.data.info.sqlite`, `settings.data.info.dbSize`, `settings.data.info.walSize`, `settings.data.info.searchDocs`, `settings.data.rebuildIndex`, `settings.data.rebuildIndex.confirm`; namespace `notices`: `notices.migrationDone`, `notices.searchRebuildDone`, `notices.searchRebuildFailed`. MVP chỉ có `vi`.

## Việc cần làm

- [ ] `api/systemInfo.ts` dùng generated types.
- [ ] `DataInfoCard` trong mục Dữ liệu của Cài đặt.
- [ ] `noticeHandlers.ts` đăng ký với event bus F01.
- [ ] Khóa i18n.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `DataInfoCard` hiển thị số liệu định dạng đúng; nút rebuild khóa khi `rebuilding=true`; xác nhận rồi gọi API có `Idempotency-Key` | `fe/src/features/settings/components/DataInfoCard.test.tsx` |
| unit | `noticeHandlers` hiện toast đúng loại và invalidate `['system','info']` | `fe/src/app/noticeHandlers.test.ts` |
| e2e (mock backend) | Mock phát `backend.notice migration_done` sau khi ready → thấy toast | `fe/tests/e2e/data-notices.spec.ts` |

## Tên mới đề xuất

- Route section `/settings/data` (UI §5.6 có mục "Dữ liệu" nhưng chưa đặt slug).
- `DataInfoCard.tsx`, `fe/src/features/settings/api/systemInfo.ts` (`useSystemInfo`, `useRebuildSearchIndex`), `fe/src/app/noticeHandlers.ts`.
- Query key `['system', 'info']`; namespace i18n `notices`.
