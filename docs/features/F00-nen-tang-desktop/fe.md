# F00 — Frontend (cầu nối bootstrap và màn trạng thái backend)

FE chưa được gọi API nào trước khi Rust báo `phase=ready`. Mọi màn ở đây là "cổng" bọc toàn bộ app (Plan §23.4 #2, UI §5.8).

## Route và màn hình

Các màn dưới đây **không** là route TanStack Router: `BootGate` render chúng thay cho `<RouterProvider>` khi chưa `ready`, nên URL hash không đổi và khi backend sẵn sàng lại thì quay về đúng route cũ.

| Phase (`BootState.phase`) | Màn hình | Ghi chú |
|---|---|---|
| `resolving_data_root`, `starting_backend` | `StartingScreen` | Logo, "Đang khởi động…", dòng phụ theo `progress.stage` ("Đang nâng cấp dữ liệu…", "Đang kiểm tra tác vụ dở dang…") |
| `needs_data_root`, `data_root_error` | `DataRootScreen` | Chọn thư mục, gợi ý mặc định, lỗi cụ thể theo `error.code` |
| `translocated` (macOS) | `TranslocatedScreen` | Hướng dẫn kéo app vào Applications rồi mở lại; nút Thoát |
| `locked_by_other_instance` | `StartupErrorScreen` biến thể "data đang được dùng" | Nút Thoát |
| `startup_failed`, `protocol_mismatch` | `StartupErrorScreen` | Mã lỗi, thông điệp, nút "Mở thư mục log", "Thử lại", "Thoát" |
| `backend_crashed` | `BackendCrashedScreen` | "Backend dừng bất ngờ", mã thoát, 20 dòng stderr cuối (thu gọn), nút "Khởi động lại" |
| `shutting_down` | `StartingScreen` biến thể "Đang đóng…" | — |
| `ready` | App bình thường + `ConnectionBanner` khi SSE mất kết nối | Banner nằm trên header |

## Component

```text
fe/src/shared/desktop/
  bridge.ts               getBootState, onBootState, pickDataRootFolder, confirmDataRoot,
                          getBackendSession, restartBackend, openLogsFolder, quitApp
  bridge.mock.ts          Bản giả cho web-dev/Playwright (không có Tauri)
  types.ts                BootState, BackendSession (khớp struct Rust)
fe/src/app/boot/
  BootGate.tsx            Chọn màn theo phase; cung cấp BackendSession cho shared/api/client
  useBootState.ts         Hook: get_boot_state lần đầu + lắng nghe event boot:state
  StartingScreen.tsx
  DataRootScreen.tsx
  TranslocatedScreen.tsx
  StartupErrorScreen.tsx
  BackendCrashedScreen.tsx
  ConnectionBanner.tsx    Đọc trạng thái kết nối từ event bus (features/jobs, F01)
fe/src/shared/i18n/vi/boot.json
```

| Component | Trách nhiệm |
|---|---|
| `bridge.ts` | Bọc `@tauri-apps/api/core` `invoke` và `@tauri-apps/api/event` `listen`. Phát hiện môi trường: có `window.__TAURI_INTERNALS__` → Tauri; không có → `bridge.mock.ts` (đọc `VITE_DEV_BACKEND_URL`, `VITE_DEV_BACKEND_TOKEN`, chỉ khi `import.meta.env.DEV`). Không lưu token vào `localStorage`/`sessionStorage` |
| `BootGate` | Khi `phase=ready`: gọi `getBackendSession()` một lần, đặt vào `shared/api/client` (`setSession`), khởi động event bus F01, render router. Khi phase rời `ready` (crash/restart): `clearSession()`, dừng event bus, hủy query đang chạy (`queryClient.cancelQueries()`), render màn tương ứng. Khi quay lại `ready` với session mới: `queryClient.invalidateQueries()` |
| `DataRootScreen` | Hiển thị đường dẫn gợi ý (từ `BootState.data_root`), nút "Chọn thư mục khác…" (`pickDataRootFolder`), nút "Dùng thư mục này" (`confirmDataRoot`). Lỗi `DATA_ROOT_CLOUD_SYNC` → hộp thoại xác nhận rồi gọi lại với `accept_cloud_sync_warning=true`. Ghi chú: dữ liệu sẽ nằm toàn bộ trong thư mục này; không dùng ổ mạng/thư mục đồng bộ |
| `BackendCrashedScreen` | Nút "Khởi động lại" gọi `restartBackend()`, khóa nút trong khi chờ; hiển thị `restart_count`; nếu crash lại ≥ 3 lần trong phiên → nhấn mạnh "Mở thư mục log" |
| `ConnectionBanner` | Trạng thái `reconnecting` > 2 giây → banner vàng "Mất kết nối tới backend, đang nối lại…" kèm số lần thử; `open` lại → ẩn banner, toast nhẹ "Đã kết nối lại". Không hiện khi `BootGate` đang ở màn crash (tránh trùng thông báo) |

## State và dữ liệu

- TanStack Query keys: không có (F00 không gọi API nghiệp vụ). `/v1/health` do Rust gọi.
- Zustand store: `useBootStore` trong `app/boot` giữ `bootState`, `session` (chỉ trong RAM).
- API dùng: Tauri commands ở [be.md](./be.md#api); sau `ready` mọi HTTP đi qua `shared/api/client.ts` (F01).
- Event SSE dùng (`/v1/events`): `ConnectionBanner` chỉ đọc trạng thái kết nối (`connecting | open | reconnecting`) do event bus F01 cung cấp; `backend.notice` kind `shutting_down` → hiện `StartingScreen` biến thể "Đang đóng…" nếu Rust chưa kịp đổi phase.
- Status bar (UI §4) đọc `useBootStore` + trạng thái kết nối: "backend ✓" khi `ready` và SSE `open`; "backend ⚠" khi reconnecting.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | `StartingScreen` với spinner và dòng tiến độ; quá 15 giây hiện thêm "Lần đầu hoặc sau nâng cấp có thể lâu hơn" (giả định ngưỡng hiển thị, không phải mục tiêu hiệu năng) |
| Rỗng | Không áp dụng |
| Lỗi (`code`) | `DATA_ROOT_*` → `DataRootScreen` với thông điệp riêng; `MIGRATION_FAILED` → `StartupErrorScreen` kèm đường dẫn backup trước migrate (`error.detail.backup_path`); `SCHEMA_TOO_NEW` → "Dữ liệu được tạo bởi phiên bản mới hơn, hãy cập nhật app"; `DB_MISSING` → hai nút "Khôi phục từ backup…" (F13, ẩn nếu chưa có) và "Tạo dữ liệu mới" (xác nhận gõ lại); `BACKEND_EXITED` → `BackendCrashedScreen` |
| Thành công | Router render bình thường; status bar "backend ✓" |

## Tương tác, phím tắt, khả năng tiếp cận

- Màn trạng thái dùng `role="status"` + `aria-live="polite"` cho dòng tiến độ; màn lỗi dùng `role="alert"`.
- Focus tự đặt vào nút hành động chính (Chọn thư mục / Khởi động lại / Thử lại).
- Trạng thái không chỉ dùng màu: icon + chữ (✓ / ⚠ / ⛔) như UI §8.
- Không có phím tắt riêng; Esc không đóng màn lỗi (không có gì phía sau).
- Đường dẫn dài hiển thị đầy đủ, xuống dòng mềm, có nút sao chép.

## Chuỗi giao diện (i18n)

Namespace `boot`, ví dụ khóa: `boot.starting.title`, `boot.starting.stage.migrating`, `boot.starting.stage.reconciling`, `boot.dataRoot.title`, `boot.dataRoot.suggested`, `boot.dataRoot.choose`, `boot.dataRoot.useThis`, `boot.dataRoot.error.DATA_ROOT_UNWRITABLE`, `boot.dataRoot.error.DATA_ROOT_NETWORK`, `boot.dataRoot.cloudSyncConfirm`, `boot.translocated.body`, `boot.crashed.title`, `boot.crashed.restart`, `boot.error.openLogs`, `boot.banner.reconnecting`, `boot.banner.reconnected`. MVP chỉ có `vi`. Màn boot được render trước khi backend sẵn sàng nên resource `boot` phải được bundle tĩnh, không tải lười.

## Việc cần làm

- [ ] `shared/desktop/types.ts` khớp struct `BootState`/`BackendSession` của Rust (viết tay, có test so khớp với fixture JSON do Rust xuất).
- [ ] `bridge.ts` + `bridge.mock.ts` (web-dev, Playwright).
- [ ] `useBootState` + `useBootStore`; xử lý event đến trước khi `get_boot_state` trả về (lấy bản có thứ tự mới hơn).
- [ ] `BootGate` nối `shared/api/client.setSession` và vòng đời event bus F01.
- [ ] Năm màn trạng thái + `ConnectionBanner`.
- [ ] Status bar hiển thị trạng thái backend (component do `app/layouts` sở hữu, F00 cung cấp hook `useBackendHealth`).
- [ ] Resource i18n `boot` tĩnh.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `BootGate` chọn đúng màn theo từng phase; chuyển `ready → backend_crashed → ready` gọi `clearSession`/`setSession` và invalidate query | `fe/src/app/boot/BootGate.test.tsx` |
| component | `DataRootScreen`: lỗi cloud sync → hộp thoại xác nhận → gọi lại với cờ | `fe/src/app/boot/DataRootScreen.test.tsx` |
| component | `ConnectionBanner` chỉ hiện sau 2 giây reconnecting, ẩn khi open | `fe/src/app/boot/ConnectionBanner.test.tsx` |
| unit | `bridge.ts` chọn mock khi không có Tauri; không ghi token vào storage | `fe/src/shared/desktop/bridge.test.ts` |
| e2e (mock backend) | Mock bridge phát chuỗi phase starting → ready → crashed → restart → ready; app trở lại route cũ | `fe/tests/e2e/boot-lifecycle.spec.ts` |
| desktop | Bản đóng gói: thấy `StartingScreen` rồi Thư viện; kill backend → màn crash → khởi động lại | `tests/desktop/smoke_lifecycle.py` (dùng chung với be.md) |

## Tên mới đề xuất

- Thư mục `fe/src/app/boot/` và các file `BootGate.tsx`, `useBootState.ts`, `StartingScreen.tsx`, `DataRootScreen.tsx`, `TranslocatedScreen.tsx`, `StartupErrorScreen.tsx`, `BackendCrashedScreen.tsx`, `ConnectionBanner.tsx`.
- `fe/src/shared/desktop/bridge.mock.ts`, `fe/src/shared/desktop/types.ts`; store `useBootStore`; hook `useBackendHealth`.
- Hàm `setSession`/`clearSession` của `shared/api/client.ts` (F01 triển khai).
- Biến môi trường dev `VITE_DEV_BACKEND_URL`, `VITE_DEV_BACKEND_TOKEN`.
- Namespace i18n `boot`.
