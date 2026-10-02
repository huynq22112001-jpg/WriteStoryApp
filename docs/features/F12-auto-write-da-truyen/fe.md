# F12 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/writing-room` | Phòng viết (UI §5.3) | Ctrl+Shift+W; bấm "● N truyện đang chạy" ở header |
| `/works/$workId` (thanh mode) | Nút "Auto-write: [▶ 10 chương ▾] [auto ▾]" (UI §5.2) | Mở `AutowriteDialog` |
| `/settings/concurrency` | Đồng thời & ngân sách (UI §5.6.3) | Số truyện song song, ngân sách $/ngày, theo truyện, timezone |
| Header + status bar (mọi route) | "● N truyện đang chạy", "$ hôm nay"; "provider: 2/4 slot" (UI §4) | Lấy từ `queue.changed`/`provider.status` |

## Component

```text
fe/src/features/writing_room/
  pages/WritingRoomPage.tsx
  components/SummaryHeader.tsx, WorkRow.tsx, PipelineSteps.tsx, TailPreview.tsx,
             WaitingReason.tsx, PriorityQueueList.tsx, EventLog.tsx, CostChart.tsx,
             AutowriteDialog.tsx, RunningIndicator.tsx, ProviderSlots.tsx
  hooks/useQueues.ts, useWritingRoomStream.ts, useCountdown.ts
  model/writingRoomStore.ts      Zustand theo workId
  api/autowrite.ts, queues.ts
  index.ts                       export RunningIndicator, ProviderSlots, AutowriteDialog
fe/src/features/settings/components/ConcurrencyBudgetSection.tsx
```

| Component | Trách nhiệm |
|---|---|
| `SummaryHeader` | "Đang chạy x · Chờ slot y · Bị chặn z", ô chọn song song (PUT `/v1/settings/concurrency`), "Hôm nay $a / $b", slot/RPM từng provider, [▶ Chạy tất cả] [⏸ Dừng] (gọi resume/pause cho mọi truyện có batch) |
| `WorkRow` | Một dòng/truyện: tên (link workspace), chương `done/target`, `PipelineSteps`, badge liền mạch, chi phí hôm nay, menu ⋯ (tạm dừng/tiếp tục/hủy/Tạm dừng để sửa) |
| `PipelineSteps` | 6 nhãn UI: Kế hoạch ▸ Viết ▸ Kiểm tra ▸ Nối ▸ Review ▸ Lưu; bước hiện tại in đậm; `↻ vòng k/K` cạnh bước gây sửa |
| `TailPreview` | 2 dòng cuối từ `stream.tail`, throttle ~4 lần/giây, `aria-live="off"` |
| `WaitingReason` | Icon ⏳/⛔ + chữ theo `waiting_reason`, đếm ngược khi có `waiting_until`; nút hành động (Mở vault, Mở Cài đặt ngân sách, [Xử lý] mở Review) |
| `PriorityQueueList` | Danh sách sắp xếp bằng `@dnd-kit/sortable`; thả → `PUT /v1/queues/priority` (optimistic, rollback khi lỗi); hỗ trợ bàn phím của dnd-kit |
| `EventLog` | `react-virtuoso` tự cuộn, giữ tối đa 1.000 mục trong RAM (giả định), lọc theo truyện |
| `CostChart` | Recharts (lazy) chi phí theo giờ hôm nay từ `GET /v1/usage/summary?group_by=hour` (F14) |
| `AutowriteDialog` | Số chương hoặc đến chương; chế độ + K; ưu tiên; gọi estimate (debounce 400 ms) và hiện min–max token/chi phí/thời gian, "ước tính thô" khi `basis=default`, model chưa có giá; cảnh báo vượt ngân sách và yêu cầu tick xác nhận (`confirm_over_budget`) |
| `RunningIndicator` | "● N truyện đang chạy" ở header (N = số truyện có job ghi `running`); bấm mở Phòng viết |
| `ProviderSlots` | Status bar "provider: in_use/max slot" |

Ánh xạ `stage` (pipeline F10) → nhãn: `load`, `plan`, `compose` → Kế hoạch; `write` → Viết; `check`, `settle`, `validate` → Kiểm tra; `seam` → Nối; `review` → Review; `repair` → giữ nhãn bước gây sửa + `↻`; `commit` → Lưu; `resettle` (F11) → nhãn "Đồng bộ lại".

## State và dữ liệu

- TanStack Query keys: `['queues']` (refetch khi reconnect SSE), `['autowriteEstimate', workId, params]`, `['settings', 'concurrency']`, `['usage', 'summary', range, 'hour']`.
- Zustand `writingRoomStore`: `byWork[workId] = {stage, repairRound, repairMax, status, waitingReason, waitingUntil, tail}`; selector hẹp theo `workId` để một dòng không làm render lại cả bảng (UI §6.3).
- Event bus một kết nối của `features/jobs` (UI §6.3): Phòng viết đăng ký `job.state`, `job.step`, `stream.tail`, `queue.changed`, `provider.status`, `usage.updated`, `work.continuity`. Không đăng ký `token.delta` (chỉ cho truyện đang mở trong workspace).
- Tail: ghi vào ref buffer, flush bằng `requestAnimationFrame` nhưng tối đa mỗi 250 ms (UI §5.3, §6.2).
- API dùng: autowrite (start/pause/resume/cancel/estimate), `GET /v1/queues`, `PUT /v1/queues/priority`, `POST /v1/jobs/{id}/cancel|resume`, `GET/PUT /v1/settings/concurrency`.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton 5 dòng |
| Rỗng | "Chưa có truyện nào đang auto-write" + nút mở Thư viện |
| `waiting_slot` | ⏳ + lý do: "provider đầy", "đạt giới hạn tốc độ – thử lại sau 0:42", "hết ngân sách hôm nay (truyện/app)", "chờ job khác của truyện", "vault đang khóa", "mất kết nối provider – thử lại sau 2:00", "đang tạm dừng" |
| `waiting_user` | ⛔ + tóm tắt (ví dụ "seam fail sau 2 vòng") + [Xử lý] → Review/Diff chương đó |
| `blocked` / continuity khác `ok` | ⛔ "cần đồng bộ lại từ Ch.K" + [Mở] |
| `interrupted` sau restart | Banner "N truyện bị gián đoạn" + [Tiếp tục tất cả] |
| Lỗi `PROVIDER_AUTH` | ⛔ "API key bị từ chối" + [Mở Cài đặt Mô hình AI] |
| SSE mất kết nối | Banner chung (F01) + giữ số liệu cũ mờ đi |

## Tương tác, phím tắt, khả năng tiếp cận

- Ctrl+Shift+W mở Phòng viết (UI §8). Trong bảng: ↑/↓ chọn dòng, Enter mở truyện, `P` tạm dừng/tiếp tục dòng đang chọn (đề xuất).
- Kéo thả có tay nắm `aria-label="Kéo để đổi ưu tiên"` và thay thế bằng bàn phím (Space nhấc, mũi tên di chuyển) theo dnd-kit.
- Trạng thái luôn có icon + chữ (✓ / ⚠ / ⛔ / ⏳); đếm ngược có `aria-label` đầy đủ, không đọc mỗi giây.
- "Tạm dừng để sửa" có confirm: "Chương đang viết sẽ bị bỏ, phần đã commit giữ nguyên".
- Editor chương N-1 read-only khi job `write` N đang chạy, hiện nút "Tạm dừng để sửa" (Plan §23.4 #3) – component nằm ở `editor`/`workspace`, dùng `writingRoomStore` qua public export.

## Chuỗi giao diện (i18n)

Namespace `writing_room`, `autowrite`. Ví dụ khóa: `writing_room.summary.running`, `writing_room.wait.PROVIDER_RATE_LIMIT`, `writing_room.wait.BUDGET_EXCEEDED`, `writing_room.step.write`, `writing_room.repair_round`, `autowrite.mode.review_every_k`, `autowrite.estimate.rough`, `autowrite.over_budget_confirm`, `header.running_count` (số nhiều theo i18next). MVP chỉ có `vi`.

## Việc cần làm

- [ ] `writingRoomStore` + đăng ký event bus.
- [ ] `WritingRoomPage`, `WorkRow`, `PipelineSteps`, `WaitingReason` + `useCountdown`.
- [ ] `TailPreview` throttle 250 ms.
- [ ] `PriorityQueueList` dnd-kit + optimistic update.
- [ ] `EventLog` virtuoso, `CostChart` lazy.
- [ ] `AutowriteDialog` + estimate + xác nhận vượt ngân sách.
- [ ] `RunningIndicator`, `ProviderSlots` trong app shell.
- [ ] `ConcurrencyBudgetSection` (react-hook-form + zod, lưu tự động từng mục).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Ánh xạ `stage` → nhãn, vòng sửa | `fe/src/features/writing_room/components/PipelineSteps.test.tsx` |
| unit | Throttle tail ≤ 4 lần/giây với 50 event/giây | `fe/src/features/writing_room/hooks/useWritingRoomStream.test.ts` |
| component | `AutowriteDialog` hiển thị ước tính, chặn gửi khi vượt ngân sách chưa xác nhận | `fe/src/features/writing_room/components/AutowriteDialog.test.tsx` |
| component | Kéo thả đổi ưu tiên, rollback khi API lỗi | `fe/src/features/writing_room/components/PriorityQueueList.test.tsx` |
| e2e (mock backend) | 5 truyện stream cùng lúc, lý do chờ, reconnect SSE từ `seq` (T17, T08) | `fe/tests/e2e/writing-room.spec.ts` |
| e2e (mock backend) | Bật auto-write, bị chặn, sửa, chạy tiếp (Plan §23.4 #12, T07) | `fe/tests/e2e/autowrite-flow.spec.ts` |

## Tên mới đề xuất

- Route `/settings/concurrency` (UI §5.6 gọi mục "Đồng thời & ngân sách" nhưng chưa có tên section).
- Store `writingRoomStore`; component `RunningIndicator`, `ProviderSlots`, `PriorityQueueList`.
- Phím `P` trong Phòng viết.
- Namespace i18n `writing_room`, `autowrite`.
