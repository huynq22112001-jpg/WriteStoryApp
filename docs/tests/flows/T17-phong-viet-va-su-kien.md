# T17 — Phòng viết và sự kiện

Tính năng: F01, F12, F14. Nguồn: Plan §23.1.C (luồng sự kiện toàn cục), §7 (`/v1/events`, `/v1/jobs/{id}/events`, `/v1/queues`), §4.4 (độ trễ event, batch 50–100 ms), §23.2 #9, #10, #12, §23.4 #2, #9, FL24 bước 4, UI §4, §5.3, §6. Cấp test chính: contract, integration, e2e-fe.

## Mục đích

Chứng minh một kết nối SSE duy nhất cấp đủ sự kiện cho Phòng viết, header và workspace; reconnect từ `seq` không mất và không lặp sự kiện; mất kết nối UI không hủy job; `token.delta` được gộp và chỉ gửi cho truyện đã đăng ký; thông báo native và trung tâm thông báo dẫn đúng chỗ xử lý mà không ảnh hưởng chương đã commit.

## Tiền điều kiện và dữ liệu

- 4 truyện từ `tests/fixtures/stories/` auto-write song song với worker pool 3 (một truyện luôn `waiting_slot`), một truyện bị chặn (seam fail như T06-02).
- Mock provider: `{latency_ms: 50, tokens_per_sec: 200, scripted_outputs: <bộ 20 chương như T07>}`; cho truyện bị chặn `scripted_outputs.seam: [fail, fail, fail]`.
- Proxy test giữa FE và BE có thể cắt kết nối SSE theo lệnh (`tests/integration/sse_proxy.py`).
- Thông báo native bật trong Cài đặt; đồng hồ giả cho retention.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T17-01 | thành công | `GET /v1/events?since=0` với Authorization header; chạy 4 truyện 2 phút. | Mỗi event có envelope `{v, seq, ts, type, work_id?, job_id?, chapter_no?, payload}`; `seq` tăng nghiêm ngặt, không trùng; `type` thuộc danh sách §23.1.C; schema khớp `contracts/` (Pydantic export). Có ping định kỳ khi nhàn. | contract, integration | `be/tests/contract/test_event_envelope.py`, `be/tests/integration/test_global_events.py` |
| T17-02 | bảo mật | Gọi `/v1/events` không có header, và với token trong query string. | Cả hai 401; token trong query không được chấp nhận (FE dùng fetch streaming có header, không dùng EventSource). | integration | `be/tests/integration/test_events_auth.py` |
| T17-03 | thành công | Đăng ký `works=A`; A, B, C đang viết. | `token.delta` chỉ của A, gộp mỗi 50–100 ms (đo khoảng cách giữa các event `token.delta`); `job.step` của mọi truyện vẫn tới để Phòng viết hiển thị bước. | integration | `be/tests/integration/test_token_delta_filter.py` |
| T17-04 | phục hồi | Cắt SSE qua proxy 10 s rồi nối lại với `Last-Event-ID = <seq cuối đã nhận>`. | Server replay mọi event (trừ `token.delta`) có `seq` lớn hơn từ `job_events`, đúng thứ tự, không thiếu; FE không render trùng (khử trùng theo `seq`); `token.delta` bị lỡ không replay, văn bản đang viết lấy lại từ checkpoint candidate. | integration, e2e-fe | `be/tests/integration/test_events_replay.py`, `fe/tests/e2e/sse_reconnect.spec.ts` |
| T17-05 | phục hồi | Trong lúc SSE mất kết nối 30 s. | Job backend vẫn chạy và commit (mất kết nối UI không hủy job); FE hiện banner mất kết nối, tự nối lại với backoff, banner tắt khi nối lại; trạng thái Phòng viết sau khi nối lại khớp `GET /v1/queues`. | e2e-fe, integration | `fe/tests/e2e/sse_banner.spec.ts` |
| T17-06 | biên | Nối lại với `since` cũ hơn retention 90 ngày (đồng hồ giả). | Server báo con trỏ đã hết hạn (không replay thiếu âm thầm); FE tải lại trạng thái đầy đủ qua `GET /v1/queues` và các query liên quan rồi tiếp tục từ `seq` mới. | integration | `be/tests/integration/test_events_cursor_expired.py` |
| T17-07 | thành công | FE mở Thư viện, Phòng viết và workspace truyện A cùng lúc. | Chỉ 1 kết nối `/v1/events` (đếm ở proxy); event được phân phối theo `work_id` vào store Zustand theo `workId`. | e2e-fe | `fe/tests/e2e/single_event_connection.spec.ts` |
| T17-08 | thành công | Phòng viết với 4 truyện: đang chạy, chờ slot, bị chặn, đang sửa vòng 1/2. | Dòng mỗi truyện hiện chương hiện tại, pipeline với bước hiện tại in đậm (`job.step`), `↻ vòng 1/2` khi `repair`, lý do chờ cụ thể (provider đầy / hết ngân sách / khóa truyện / chờ tác giả), trạng thái liền mạch có icon + chữ, chi phí theo `usage.updated`; 1–2 dòng đuôi văn bản cập nhật ~4 lần/giây. Header "● 3 truyện đang chạy"; status bar số slot provider. | e2e-fe | `fe/tests/e2e/writing_room.spec.ts` |
| T17-09 | thành công | Bấm [Xử lý] ở truyện bị chặn; bấm tên truyện đang chạy. | [Xử lý] mở workspace đúng chương với banner chặn; bấm tên truyện mở workspace trong khi các truyện khác vẫn chạy (event tiếp tục tới). | e2e-fe | như trên |
| T17-10 | thành công | `POST /v1/works/{id}/autowrite/pause` và `resume` từ nút ⏸ trên dòng; [⏸ Dừng] và [▶ Chạy tất cả]. | Event `queue.changed` và `job.state` tương ứng; trạng thái dòng đổi trong < 200 ms sau event; "Dừng tất cả" không hủy job đang commit. | e2e-fe, integration | `fe/tests/e2e/writing_room_controls.spec.ts` |
| T17-11 | thành công | Chương bị chặn, batch xong, provider lỗi kéo dài (T15-09 > ngưỡng). | Mỗi sự kiện tạo 1 thông báo native (Tauri notification) và 1 mục trong trung tâm thông báo; bấm mục mở đúng route (`/works/$workId?chapter=…&tab=review`, Phòng viết, Cài đặt › Mô hình AI). Tắt thông báo trong Cài đặt → không gửi native, vẫn có mục trong trung tâm. | e2e-fe, desktop | `fe/tests/e2e/notification_center.spec.ts`, `tests/desktop/native_notification.md` |
| T17-12 | lỗi | Tiêm lỗi gửi thông báo native sau commit chương. | Chương vẫn committed (không rollback); lỗi thông báo được ghi log và thử lại độc lập; không phát `job.state` `failed`. | integration | `be/tests/integration/test_notification_failure_after_commit.py` |
| T17-13 | phục hồi | Kill backend khi FE đang mở. | FE hiện "backend dừng bất ngờ – khởi động lại"; sau khởi động lại FE nối SSE từ `seq` cuối; job hiện `interrupted` (event `job.state`). | e2e-fe, desktop | `fe/tests/e2e/backend_crash_banner.spec.ts` |
| T17-14 | thành công | Mở Nhật ký/chi phí và trang Lưu trữ; `GET /v1/storage`, `POST /v1/storage/cleanup`. | Chi phí hôm nay khớp tổng `usage_counters`; Lưu trữ hiện dung lượng DB/asset/log/backup; cleanup xóa candidate bị từ chối > 30 ngày, `job_events` > 90 ngày, log xoay vòng; không xóa revision committed nào. | integration, e2e-fe | `be/tests/integration/test_storage_cleanup.py` |
| T17-15 | hiệu năng | 5 truyện stream + gõ editor; đo từ `ts` event tới lúc DOM cập nhật. | Độ trễ event → UI p95 < 200 ms; Phòng viết không render toàn văn (DOM mỗi dòng ≤ 2 dòng đuôi); không tràn bộ đệm event khi tab ẩn 5 phút rồi hiện lại. | e2e-fe | `fe/tests/e2e/events_latency.spec.ts` |
| T17-16 | thành công | Bật "giữ máy thức khi đang viết"; có batch chạy; batch xong. | Trong lúc batch chạy shell giữ assertion chống ngủ (Windows `SetThreadExecutionState`, macOS IOPMAssertion); batch xong hoặc dừng thì nhả assertion. | desktop, thủ công | `tests/desktop/keep_awake.md` |
| T17-17 | thành công | `GET /v1/jobs/{id}/events` cho một job. | Chỉ event của job đó, cùng envelope và `seq` toàn cục; hỗ trợ `Last-Event-ID` như luồng toàn cục. | integration | `be/tests/integration/test_job_events_endpoint.py` |

## Kiểm tra dữ liệu sau test

- DB: `job_events` chứa mọi event trừ `token.delta`, `seq` liên tục; không có event cũ hơn retention sau cleanup.
- Event: sau T17-04 tập `seq` FE nhận = tập `seq` server đã phát (trừ `token.delta`), không trùng.
- Trạng thái FE (store theo `workId`) khớp `GET /v1/queues` tại cuối mỗi kịch bản.

## Tiêu chí pass

- 0 event mất, 0 event render lặp qua 20 lần cắt/nối SSE ngẫu nhiên.
- 0 job bị hủy do mất kết nối UI.
- `token.delta` chỉ tới truyện đã đăng ký; tần suất ≤ 20 event/giây/truyện (gộp 50–100 ms).
- Độ trễ event → UI p95 < 200 ms (tiêu chí đề xuất §4.4).
- 0 chương bị rollback do lỗi thông báo.

## Ghi chú thủ công

- Kiểm thông báo native trên Windows (Action Center) và macOS (Notification Center, quyền thông báo lần đầu), bấm thông báo mở đúng cửa sổ/route.
- T17-16: kiểm bằng `powercfg /requests` (Windows) và `pmset -g assertions` (macOS).

## Tên mới đề xuất

- `backend.notice` payload `{code: "EVENT_CURSOR_EXPIRED"}` khi `since` cũ hơn retention.
- Loại event `notification.created` (trung tâm thông báo) hoặc dùng `backend.notice` — §23.1.C chưa có loại riêng.
- Bảng `notification_outbox` dùng từ MVP (§18 đặt ở nhóm Operation, NEW07 ghi R7).
- `GET /v1/notifications` cho trung tâm thông báo.
