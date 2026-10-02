# F04 — Cấu hình mô hình AI

Giai đoạn: R1–R2 (R1: kết nối + lấy danh sách model + danh sách ghi đè; R2: effort, vai trò, ghim vào job, cấu hình limiter). Trạng thái: planned.

## Mục tiêu

Người dùng kết nối một hoặc nhiều nhà cung cấp AI (Anthropic, OpenAI-compatible, Ollama/LM Studio), app tự lấy danh sách model từ `{base_url}/v1/models`, người dùng sắp xếp/ghi đè danh sách (model đầu = mặc định), chọn effort mặc định và gán model + effort cho từng vai trò (toàn app và theo truyện). Mỗi job ghim model + effort lúc bắt đầu để không đổi giữa chừng và không phá prompt cache.

## Phạm vi

- Trong phạm vi:
  - CRUD provider: giao thức, base URL, API key lưu trong vault (F03) hoặc chỉ dùng cho phiên; kiểm tra kết nối.
  - Lấy danh sách model (discovery) chạy nền khi backend sẵn sàng và theo nút "Kiểm tra lấy danh sách"; chuẩn hóa Anthropic (`id`, `display_name`, `max_input_tokens`, `max_tokens`, `capabilities.effort.*`, phân trang `has_more`/`after_id`, `limit` ≤ 1.000) và OpenAI-compatible (`data[].id`).
  - Quy tắc merge: danh sách ghi đè **thay thế** danh sách tự lấy, mục đầu là mặc định; không ghi đè trường người dùng đã sửa; model biến mất trên server đánh dấu ⚠, không tự xóa.
  - Công tắc "Ưu tiên bản context dài (1M)", effort mặc định (`low`/`medium`/`high`/`xhigh`/`max`, trống = mặc định provider).
  - Vai trò → model + effort (`planner`, `writer`, `checker`, `reviewer`, `summary`), ghi đè theo truyện; `ModelResolver` chọn và ghim cấu hình vào job.
  - Lưu cấu hình limiter theo provider (concurrency, RPM/TPM) và ngân sách/số truyện song song toàn app.
  - Adapter AI cho ba giao thức: liệt kê model, kiểm tra kết nối, ánh xạ effort sang tham số request.
- Ngoài phạm vi:
  - Thực thi limiter/token bucket, `Retry-After`, ngân sách lúc chạy và trạng thái `waiting_slot` → F12 (đọc cấu hình F04 lưu).
  - Bộ đếm usage/chi phí, `GET /v1/providers/{id}/usage` → F14.
  - Vault (tạo/mở/khóa, lưu secret) → F03; F04 chỉ gọi API nội bộ của vault và lưu `secret_ref`.
  - Model dự phòng theo vai trò (Plan §23.3 #10, mức "Sau"); proxy/custom headers (MOD08, R4); model ảnh (IMG02, R4).
  - Bộ đánh giá model tiếng Việt để gợi ý vai trò (Plan §6.6, R2) → F10/F08.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F01 | Hợp đồng lỗi `{code, message, detail, retryable, action}`, envelope sự kiện `provider.status`, sinh OpenAPI → TS |
| F02 | SQLite, migration Alembic, writer queue để merge danh sách model trong transaction ngắn |
| F03 | Vault lưu API key; trạng thái `VAULT_LOCKED`, event `vault.status` để chạy lại discovery khi mở vault |

Tính năng phụ thuộc vào F04: F10 (gọi model theo vai trò), F12 (limiter, ghim job), F14 (giá model để tính chi phí), F03 onboarding (bước "thêm provider + kiểm tra lấy danh sách").

## Nguồn thiết kế

- Plan §2 (httpx, adapter), §4.2 (limiter theo provider), §5 (`providers`, `settings`, `provider_models`, `role_models`, `provider_limits`), §6.6 (chọn model, timeout, không retry lỗi key/model), §7 (API providers/roles), **§7.1** (discovery, merge, context dài, effort, vai trò), §23.1.D (mã lỗi), §23.3 #2 #4 (structured outputs, tỷ lệ token/âm tiết lưu trong `provider_models`).
- Plan FL26 (Provider settings), §15.13 MOD01, MOD02, MOD04, MOD05, MOD06, MOD07, MOD09, MOD10.
- Arch §5 (`be/.../infrastructure/ai/factory.py`, `limits.py`, `discovery.py`, `model_resolver.py`), §6 (`ai/.../providers/`, `ports/provider.py`, `policies/`).
- UI §5.6 (mẫu mục cài đặt), **§5.6.1** (Mô hình AI), **§5.6.2** (Vai trò & effort), §5.6.3 (Đồng thời & ngân sách), §4 (status bar "provider: 2/4 slot").
- Review §5.2 (giới hạn theo provider), §6 (prompt cache).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Bảng `providers`, `provider_models`, `role_models`, `provider_limits`, `settings`; API provider/discover/models/roles/limits; merge; `ModelResolver` ghim cấu hình vào job |
| FE | [fe.md](./fe.md) | Cài đặt "Mô hình AI" đúng UI §5.6.1, "Vai trò & effort" §5.6.2, "Đồng thời & ngân sách" §5.6.3; ghi đè vai trò theo truyện |
| AI | [ai.md](./ai.md) | Port `TextProvider.list_models/test_connection`, adapter Anthropic/OpenAI-compatible/Ollama-LM Studio, chuẩn hóa discovery, ánh xạ effort, contract `ModelSelection` |

## Tiêu chí hoàn thành

- [ ] Thêm provider Anthropic với key trong vault → "Kiểm tra lấy danh sách" hiển thị số model, model mới/biến mất; chấm tròn xanh/đỏ/xám đúng trạng thái.
- [ ] Discovery Anthropic đọc đủ mọi trang (`has_more`/`after_id`, `limit=1000`); OpenAI-compatible đọc `data[].id`; Ollama/LM Studio không cần key.
- [ ] Lỗi 401/404/timeout/JSON sai được lưu kèm thời điểm, hiển thị cụ thể, **không** làm mất danh sách cũ.
- [ ] Danh sách ghi đè có mục → danh sách hiệu lực đúng thứ tự, mục đầu là mặc định; rỗng → dùng danh sách tự lấy.
- [ ] Trường người dùng đã sửa (tên hiển thị, context, output, effort, giá…) không bị lần discovery sau ghi đè; có nút khôi phục giá trị tự lấy.
- [ ] Ô effort chỉ hiện mức model hỗ trợ; model không hỗ trợ effort → ô khóa kèm giải thích; adapter không gửi mức không hỗ trợ.
- [ ] Vai trò toàn app và ghi đè theo truyện hoạt động; thứ tự áp dụng effort: vai trò truyện → vai trò app → effort mặc định → mặc định provider (Plan §7.1).
- [ ] Job ghim model + effort lúc bắt đầu; đổi cài đặt khi đang chạy chỉ áp từ chương kế tiếp (kiểm bằng integration test với mock provider).
- [ ] API key không xuất hiện trong log, response API, OpenAPI example hay trace.
- [ ] Các test luồng liên quan pass: [T03](../../tests/flows/T03-cau-hinh-mo-hinh-ai.md), [T15](../../tests/flows/T15-loi-provider.md) (phần 401/429/mất mạng/vault khóa khi discovery).

## Rủi ro và câu hỏi mở

- **Context 1M:** dữ liệu Models API hiện tại có thể đã báo `max_input_tokens` = 1.000.000 cho model mặc định; khi đó công tắc "Ưu tiên context dài" không có tác dụng. Biến thể 1M (ID riêng hoặc tham số/beta) phải khai báo trong metadata model (Plan §7.1); MVP không tự đoán quy ước đặt tên biến thể của gateway. Cần chốt cách khai báo khi có gateway thật.
- **Effort mặc định khi vai trò dùng model khác model mặc định:** UI §5.6.1 mô tả effort mặc định là "mức effort của model mặc định", Plan §7.1 dùng nó cho mọi vai trò chưa gán effort. Đề xuất: áp cho mọi model, nhưng bỏ nếu model đích không hỗ trợ mức đó (ghi trong trace). Cần xác nhận.
- **Nhiều provider:** wireframe §5.6.1 chỉ có một khối "Kết nối". Đề xuất: dữ liệu hỗ trợ nhiều provider; UI hiện thanh chọn provider phía trên khối "Kết nối" khi có > 1 provider (xem fe.md). Cần xác nhận với thiết kế.
- **Không có vai trò cho nền truyện (architect):** Plan §7.1 chỉ có 5 vai trò; F06 dùng vai trò `planner` cho foundation. Cần xác nhận hoặc thêm vai trò.
- **Ánh xạ effort cho OpenAI-compatible:** tham số reasoning khác nhau theo endpoint; MVP chỉ gửi khi người dùng khai báo mức hỗ trợ. Giả định chưa kiểm chứng với gateway cụ thể.
- Lỗi provider mã HTTP khác (403, 5xx, 429) khi discovery: ánh xạ ở be.md; 429 khi discovery không retry nền quá 1 lần để tránh tốn quota.
