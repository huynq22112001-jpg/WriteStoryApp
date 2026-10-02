# P005 – Chạy thử backend dev + health

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | S06 | [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P005] Chạy thử backend dev + health

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S06-chay-dev.md
- docs/features/F00-nen-tang-desktop/be.md

Việc cần làm:
1. Chạy nền `uv run python -m writestory_be --dev`.
2. Gọi `GET http://127.0.0.1:8765/v1/health` có `Authorization: Bearer dev-token` (httpx qua `uv run python -c`) → 200; không token → 401 code UNAUTHORIZED.
3. Gọi `POST /v1/dev/mock-runs` rồi đọc vài event từ `/v1/events` để thấy token.delta của 3 truyện.
4. Tắt server.

Phạm vi file: Không sửa code (trừ khi phát hiện lỗi – sửa tối thiểu và báo lại)
Xong khi: Ghi kết quả 3 phép thử vào báo cáo và vào docs/steps/TRANG-THAI.md.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P005 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P005); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
