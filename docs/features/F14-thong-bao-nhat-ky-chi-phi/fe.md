# F14 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/logs?tab=cost\|requests\|events\|system` | Nhật ký và chi phí (UI §4 ribbon 📜) | Mặc định `cost` |
| `/settings/storage` | Lưu trữ (Plan §23.4 #10, UI §5.8) | Section mới của `/settings/$section` |
| `/settings/notifications` | Thông báo + giữ máy thức + log debug AI | Section mới |
| Header (mọi route) | Chuông trung tâm thông báo + "$ hôm nay" (UI §4) | Popover |

## Component

```text
fe/src/features/notifications/
  components/NotificationBell.tsx, NotificationCenter.tsx, NotificationItem.tsx,
             NotificationSettingsSection.tsx
  hooks/useNativeNotifications.ts
  api/notifications.ts
fe/src/features/logs/
  pages/LogsPage.tsx
  components/CostOverview.tsx, CostByHourChart.tsx, CostBreakdownTable.tsx,
             RequestsTable.tsx, JobEventsList.tsx, SystemLogViewer.tsx, AiDebugLogViewer.tsx
  api/usage.ts, logs.ts
fe/src/features/storage/
  pages/StoragePage.tsx
  components/StorageBreakdown.tsx, CleanupDialog.tsx
  api/storage.ts
fe/src/features/jobs/hooks/useKeepAwake.ts
fe/src/shared/desktop/bridge.ts         sendNotification, setKeepAwake (có mock web-dev)
desktop/src-tauri/src/power.rs           command set_keep_awake
```

| Component | Trách nhiệm |
|---|---|
| `NotificationBell` | Icon chuông + số chưa đọc (`aria-label="Thông báo, 3 chưa đọc"`) |
| `NotificationCenter` | Danh sách ảo hóa; bấm mục → điều hướng `target_route` (ví dụ Review/Diff chương bị chặn) và đánh dấu đã đọc; "Đánh dấu tất cả đã đọc" |
| `useNativeNotifications` | Nhận `notification.created`; nếu `native` và cửa sổ không focus → `isPermissionGranted`/`requestPermission`/`sendNotification` (plugin notification) → báo `POST …/native`; cửa sổ đang focus → toast sonner thay vì native (giả định UX); lúc reconnect gửi bù các mục `pending` |
| `CostOverview` | Thẻ số: chi phí hôm nay / 7 ngày, token vào/ra, tỷ lệ cache hit, số request chưa có giá (link tới Cài đặt Mô hình AI để điền giá) |
| `CostByHourChart` | Recharts (lazy) cột chi phí theo giờ hoặc ngày; chọn khoảng; dùng chung với `CostChart` của Phòng viết qua public export |
| `CostBreakdownTable` | Theo truyện / model / provider |
| `RequestsTable` | `usage_records` ảo hóa (TanStack Virtual): thời điểm, truyện, vai trò, model, token, cache, chi phí, `stop_reason`, lỗi; lọc theo truyện/job |
| `JobEventsList` | `job_events` theo truyện/job, react-virtuoso |
| `SystemLogViewer` | Log backend/desktop, lọc mức; chỉ đọc |
| `AiDebugLogViewer` | Hiện khi log debug bật: danh sách file theo job, xem JSON đã che |
| `StorageBreakdown` | Thanh/bảng dung lượng theo loại + dung lượng trống của ổ; bảng DB (ghi "ước lượng" khi `estimated`) |
| `CleanupDialog` | Chọn mục dọn → `dry_run` hiện dung lượng giải phóng → xác nhận; ghi chú "Phiên bản đã lưu không bao giờ bị xóa" |
| `NotificationSettingsSection` | Bật/tắt native và từng loại; "Giữ máy thức khi đang viết"; "Ghi log yêu cầu AI để gỡ lỗi" kèm cảnh báo chứa bản thảo |

Rust `power.rs` (Plan §23.2 #9): command `set_keep_awake(enabled: bool)`.

- Windows: một thread chuyên trách gọi `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` khi bật và `SetThreadExecutionState(ES_CONTINUOUS)` khi tắt (trạng thái gắn với thread gọi nên không gọi từ thread tạm). Không dùng `ES_DISPLAY_REQUIRED` để màn hình vẫn tắt được.
- macOS: `IOPMAssertionCreateWithName(kIOPMAssertionTypePreventUserIdleSystemSleep, kIOPMAssertionLevelOn, "WriteStoryApp đang viết truyện", &id)`; tắt bằng `IOPMAssertionRelease(id)`.
- Nhả assertion trong `RunEvent::Exit`; command idempotent; khai báo trong `capabilities/`.

`useKeepAwake`: khi `power.keep_awake_while_writing` bật và `queue.summary.running > 0` → `setKeepAwake(true)`; về 0 → `false` sau 30 giây (giả định, tránh bật/tắt liên tục giữa hai chương).

## State và dữ liệu

- TanStack Query keys: `['notifications', {unread}]`, `['usage', 'summary', range, groupBy, workId]`, `['usage', 'records', filters]`, `['logs', source, level]`, `['logs', 'ai', jobId]`, `['storage']`, `['settings', 'notifications']`.
- Zustand: `notificationsStore.unreadCount` cập nhật từ event để header không refetch liên tục.
- API dùng: notifications, `/v1/usage/summary`, `/v1/usage/records`, `/v1/providers/{id}/usage`, `/v1/logs`, `/v1/logs/ai…`, `/v1/storage`, `/v1/storage/cleanup`, `/v1/settings/notifications`.
- Event SSE dùng (`/v1/events`): `notification.created`, `usage.updated` (header "$ hôm nay", invalidate summary hôm nay), `queue.changed` (keep-awake), `backend.notice`.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton thẻ số/biểu đồ/bảng |
| Rỗng | Thông báo: "Không có thông báo"; Chi phí: "Chưa có yêu cầu AI nào" |
| Model chưa có giá | Chi phí hiện "—" + nhãn "chưa có giá" (không hiện $0) |
| Quyền thông báo bị từ chối | Banner trong Cài đặt: "Hệ điều hành đang chặn thông báo" + hướng dẫn |
| Lỗi `MAINTENANCE` | "Đang khôi phục dữ liệu, thử dọn dẹp sau" |
| Thành công dọn dẹp | Toast "Đã giải phóng 1,4 GB" |

## Tương tác, phím tắt, khả năng tiếp cận

- Chuông mở bằng Enter/Space; danh sách có `role="list"`, mục chưa đọc có chữ "Chưa đọc" (không chỉ chấm màu).
- Biểu đồ có bảng số liệu thay thế cho trình đọc màn hình (`CostBreakdownTable`).
- Số tiền định dạng `Intl.NumberFormat('vi', {style: 'currency', currency: 'USD'})`.

## Chuỗi giao diện (i18n)

Namespace `notifications`, `logs`, `storage`. Ví dụ khóa: `notifications.type.chapter_blocked.title`, `notifications.type.batch_completed.body`, `notifications.permission_denied`, `logs.tab.cost`, `logs.cache_hit_ratio`, `logs.unpriced`, `storage.category.backups`, `storage.cleanup.never_revisions`, `settings.keep_awake`, `settings.ai_debug_log.warning`. MVP chỉ có `vi`.

## Việc cần làm

- [ ] `bridge.ts`: `sendNotification`, `setKeepAwake` + mock.
- [ ] Rust `power.rs` (Windows/macOS) + capability.
- [ ] Trung tâm thông báo + `useNativeNotifications` + gửi bù.
- [ ] `LogsPage` 4 tab, biểu đồ lazy, bảng ảo hóa.
- [ ] `StoragePage` + `CleanupDialog` (dry-run trước).
- [ ] `NotificationSettingsSection`.
- [ ] Header "$ hôm nay" từ `usage.updated`.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | Bấm thông báo điều hướng đúng route và đánh dấu đã đọc | `fe/src/features/notifications/components/NotificationCenter.test.tsx` |
| unit | `useNativeNotifications`: focus → toast; không focus → native; quyền bị từ chối → `skipped` | `fe/src/features/notifications/hooks/useNativeNotifications.test.ts` |
| unit | `useKeepAwake` bật/tắt có độ trễ 30 s | `fe/src/features/jobs/hooks/useKeepAwake.test.ts` |
| component | `CleanupDialog` gọi dry-run trước khi xóa | `fe/src/features/storage/components/CleanupDialog.test.tsx` |
| e2e (mock backend) | Chương bị chặn → chuông tăng → bấm mở Review (T17) | `fe/tests/e2e/notifications.spec.ts` |
| desktop | Giữ máy thức khi 1 truyện chạy (kiểm `powercfg /requests` trên Windows, `pmset -g assertions` trên macOS) | `tests/desktop/keep_awake.md` (thủ công) |

## Tên mới đề xuất

- Route section `/settings/storage`, `/settings/notifications`; query `?tab=` của `/logs`.
- Feature folder `notifications`, `logs`, `storage` (đã có trong Arch §4/§9); hook `useKeepAwake`, `useNativeNotifications`.
- Rust `desktop/src-tauri/src/power.rs`, command `set_keep_awake`; bridge `setKeepAwake`, `sendNotification`.
- Namespace i18n `notifications`, `logs`, `storage`.
