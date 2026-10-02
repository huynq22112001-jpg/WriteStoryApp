# F01 — Frontend

F01 không có màn hình nghiệp vụ. Nó cung cấp lớp truyền tải dùng chung cho mọi tính năng: HTTP client có xác thực, parser SSE trên fetch, event bus duy nhất và cách hiển thị lỗi theo `code`.

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/dev/events` | `EventInspectorPage` (chỉ khi `import.meta.env.DEV`) | Bảng event realtime: seq, type, work, payload rút gọn; trạng thái kết nối; nút "Ngắt kết nối giả" để thử reconnect. Không có trong bản release |

## Component

```text
fe/src/shared/api/
  client.ts                 setSession/clearSession; apiFetch<T>(); ApiError; tự gắn Authorization, Idempotency-Key
  stream.ts                 openEventStream(url, {headers, signal, onEvent, onOpen}) — parser text/event-stream
  errors.ts                 ErrorCode/ErrorAction (từ generated types), mapErrorToView(code) → {i18nKey, actionKey}
  idempotency.ts            newIdempotencyKey() = crypto.randomUUID()
  generated/schema.d.ts     Sinh bởi openapi-typescript, không sửa tay
fe/src/shared/ui/
  ErrorState.tsx            Hiển thị lỗi theo envelope + nút action (handler lấy từ registry do app cung cấp)
fe/src/app/
  errorActions.ts           Đăng ký handler cho ErrorAction: unlock_vault → mở dialog vault (F03), open_resync → điều hướng (F11)…
fe/src/features/jobs/
  eventBus.ts               Một kết nối /v1/events cho toàn app; reconnect; dedup; phân phối theo type/work_id
  eventStore.ts             Zustand: connection, lastSeq, watchedWorks, streams theo workId/candidateId
  invalidation.ts           Bảng event type → TanStack Query keys cần invalidate
  tokenBuffer.ts            Gom token.delta trong ref, flush bằng requestAnimationFrame
  hooks/useConnectionState.ts, useWorkEvents.ts, useCandidateStream.ts, useWatchWork.ts
  pages/EventInspectorPage.tsx   (dev)
  index.ts                  Public exports
```

| Component | Trách nhiệm |
|---|---|
| `client.ts` | `apiFetch(path, {method, body, query, idempotencyKey, signal})`: ghép `base_url` từ session (F00), header `Authorization`, `Content-Type: application/json`; với POST có `idempotencyKey` gửi `Idempotency-Key`. Response không 2xx → parse `ErrorResponse` → throw `ApiError {status, code, message, detail, retryable, action, requestId}`; body không phải JSON → `ApiError` code `INTERNAL`. Lỗi mạng (fetch reject) → `ApiError` code `NETWORK` phía client. Chỉ tự thử lại GET một lần khi lỗi mạng hoặc `DB_BUSY`; không tự thử lại POST/PUT/PATCH/DELETE. `401` → báo `BootGate` kiểm tra lại session (token có thể đã đổi do restart backend) |
| `stream.ts` | Đọc `response.body` qua `TextDecoderStream`, tách dòng theo `\n`/`\r\n`, xử lý `id:`, `event:`, `data:` nhiều dòng, dòng comment `:` (ping), sự kiện kết thúc bằng dòng trống; chunk cắt giữa dòng hoặc giữa ký tự UTF-8 đa byte không làm hỏng dữ liệu. Watchdog: không nhận byte nào trong 45 giây → abort |
| `eventBus.ts` | Xem "Logic kết nối" bên dưới |
| `tokenBuffer.ts` | `token.delta mode=full`: nối `text` vào buffer theo `candidate_id` tại `offset`; bỏ phần đã có (`offset + len <= known_length`); gặp khoảng trống (`offset > known_length`) → đánh dấu `needsResync` để `useCandidateStream` đọc lại candidate partial qua API (F11) rồi tiếp tục. Flush sang store mỗi frame (rAF), tối đa ~ 50–100 ms (UI §6) |
| `ErrorState` | Mẫu lỗi thống nhất (Plan §23.4 #7): icon ⛔/⚠, thông điệp i18n theo `code` (fallback `message` của BE), `detail` rút gọn, nút action, mã `request_id` có nút sao chép |

### Logic kết nối của `eventBus`

1. `start()` được `BootGate` gọi khi `phase=ready`; `stop()` khi rời `ready`.
2. URL: `/v1/events?works=<watchedWorks>&previews=1`; header `Authorization` và `Last-Event-ID: <lastSeq>` nếu đã có.
3. Mỗi event: nếu có `id`/`seq` mới (khác `token.delta`) và `seq <= lastSeq` → bỏ (dedup); ngược lại cập nhật `lastSeq`, đẩy vào store, gọi listener theo `type` và `work_id`, áp bảng invalidation.
4. `backend.notice kind=replay_gap` → `queryClient.invalidateQueries()` toàn bộ, xóa buffer candidate (sẽ đọc lại khi cần).
5. Đứt kết nối (lỗi mạng, server đóng, watchdog) → trạng thái `reconnecting`, chờ backoff `500 ms × 2^n` có jitter, tối đa 10 giây; thử lại vô hạn khi backend còn `ready`. Mở lại thành công → `open`, reset backoff.
6. `401` khi mở stream → dừng, hỏi `BootGate` lấy session mới (backend có thể vừa restart) rồi mở lại; `lastSeq` giữ nguyên vì `seq` nằm trong DB.
7. `useWatchWork(workId)` thêm/bớt `watchedWorks` (đếm tham chiếu); thay đổi được gom 300 ms rồi mở lại kết nối (đóng kết nối cũ sau khi kết nối mới mở để không hở event; dedup theo `seq` xử lý phần trùng).

### Bảng invalidation (khởi điểm, tính năng sau bổ sung)

| Event `type` | Query keys invalidate |
|---|---|
| `chapter.committed` | `['works', workId]`, `['chapters', workId]`, `['chapter', chapterId]` (nếu payload có) |
| `work.continuity` | `['works', workId]`, `['continuity', workId]` |
| `queue.changed`, `job.queued`, `job.state` | `['queues']`, `['jobs', jobId]` |
| `candidate.ready` | `['candidates', chapterId]` |
| `finding.added` | `['findings', workId]` |
| `usage.updated` | `['usage']` |
| `provider.status` | `['providers']` |
| `vault.status` | `['vault']` |

## State và dữ liệu

- TanStack Query keys: không sở hữu key riêng; chỉ invalidate theo bảng trên.
- Zustand store `useEventStore` (selector hẹp): `connection: 'idle' | 'connecting' | 'open' | 'reconnecting'`, `lastSeq`, `attempt`, `watchedWorks`, `jobProgress[jobId]` (step, attempt, status), `previews[workId]` (tail), `candidates[candidateId]` (text đã nhận, `knownLength`, `needsResync`). Không sao chép dữ liệu DB khác vào store (Arch §4).
- API dùng: `GET /v1/events`; `GET /v1/jobs/{id}/events` chỉ dùng ở `EventInspectorPage` để thử.
- Event SSE dùng: tất cả type; `token.delta` qua `tokenBuffer`.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Không có màn riêng; `connecting` lần đầu nằm trong `StartingScreen` của F00 |
| Rỗng | `EventInspectorPage`: "Chưa có sự kiện" |
| Lỗi (`code`) | `ErrorState` theo bảng mã của be.md; mất kết nối SSE → `ConnectionBanner` (F00) |
| Thành công | Dữ liệu cập nhật tại chỗ, không reload trang |

## Tương tác, phím tắt, khả năng tiếp cận

- `ErrorState` dùng `role="alert"` cho lỗi chặn thao tác, `role="status"` cho lỗi có thể chờ (`retryable`).
- Nút action có nhãn động từ rõ ràng ("Mở khóa vault", "Xem khác biệt", "Thử lại").
- Không render token từng ký tự vào DOM: chỉ cập nhật theo frame, tránh làm chậm trình đọc màn hình; vùng stream dùng `aria-live="off"` và có nút "Đọc bản hiện tại".

## Chuỗi giao diện (i18n)

Namespace `errors` và `events`. Ví dụ khóa: `errors.REVISION_CONFLICT.title`, `errors.REVISION_CONFLICT.body`, `errors.VAULT_LOCKED.title`, `errors.PROVIDER_RATE_LIMIT.body` (nội suy `{{retryAfter}}`), `errors.NETWORK.title`, `errors.INTERNAL.body`, `errors.action.unlock_vault`, `errors.action.view_diff`, `errors.action.retry`, `errors.requestId`, `events.inspector.title`. Mỗi `ErrorCode` trong generated types phải có khóa; test kiểm đủ. MVP chỉ có `vi`.

## Việc cần làm

- [ ] Script `gen:api` trong `fe/package.json`; commit `generated/schema.d.ts`.
- [ ] `client.ts`, `ApiError`, `idempotency.ts`.
- [ ] `stream.ts` + test chunk biên.
- [ ] `eventBus.ts`, `eventStore.ts`, `tokenBuffer.ts`, `invalidation.ts`, hooks.
- [ ] `ErrorState.tsx` + `app/errorActions.ts` (registry; handler cụ thể do F03, F04, F11… đăng ký).
- [ ] Resource i18n `errors` đủ mọi `ErrorCode`.
- [ ] `EventInspectorPage` (dev).
- [ ] ESLint rule: chỉ `shared/api` được gọi `fetch` tới backend.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Parser SSE: chunk cắt giữa dòng, giữa ký tự UTF-8 (chữ "ộ", "đ"), CRLF, `data:` nhiều dòng, comment ping | `fe/src/shared/api/stream.test.ts` |
| unit | `apiFetch` parse `ErrorResponse`, gửi `Idempotency-Key`, không retry POST, retry GET một lần khi lỗi mạng | `fe/src/shared/api/client.test.ts` |
| unit | `eventBus`: dedup theo `seq`, reconnect gửi `Last-Event-ID`, `replay_gap` invalidate toàn bộ, backoff tăng có trần | `fe/src/features/jobs/eventBus.test.ts` |
| unit | `tokenBuffer`: offset trùng bị bỏ, khoảng trống → `needsResync` | `fe/src/features/jobs/tokenBuffer.test.ts` |
| unit | Mọi `ErrorCode` có khóa i18n | `fe/src/shared/api/errors.test.ts` |
| component | `ErrorState` hiển thị đúng nút theo `action` và gọi handler registry | `fe/src/shared/ui/ErrorState.test.tsx` |
| e2e (mock backend) | Mock server SSE đóng kết nối giữa chừng; UI không mất/lặp event, banner hiện rồi ẩn | `fe/tests/e2e/events-reconnect.spec.ts` |

## Tên mới đề xuất

- Route dev `/dev/events`, `EventInspectorPage`.
- File: `fe/src/shared/api/errors.ts`, `fe/src/shared/api/idempotency.ts`, `fe/src/shared/ui/ErrorState.tsx`, `fe/src/app/errorActions.ts`, `fe/src/features/jobs/eventBus.ts`, `eventStore.ts`, `invalidation.ts`, `tokenBuffer.ts`, hooks `useConnectionState`, `useWorkEvents`, `useCandidateStream`, `useWatchWork`.
- Kiểu/hàm: `ApiError`, `apiFetch`, `openEventStream`, `mapErrorToView`, `useEventStore`. Mã lỗi phía client `NETWORK` (không do BE trả).
- Namespace i18n `errors`, `events`. Script `gen:api`.
