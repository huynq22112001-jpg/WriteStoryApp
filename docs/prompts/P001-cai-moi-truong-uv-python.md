# P001 – Cài uv + Python 3.14 và uv sync

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| Tất cả | S00 | — |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P001] Cài uv + Python 3.14 và uv sync

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: không có. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S00-moi-truong.md
- docs/steps/S01-khung-monorepo.md

Việc cần làm:
1. Kiểm tra `uv --version`. Nếu chưa có: HỎI TÔI trước khi cài, rồi cài uv theo lệnh trong S00.
2. `uv python install 3.14`.
3. `uv sync` ở gốc repo, xác nhận tạo `.venv/` và `uv.lock`.
4. `uv run python --version` trả 3.14.x.

Phạm vi file: uv.lock, .venv/ (không sửa code)
Xong khi: `uv run python --version` = 3.14.x và `uv sync` không lỗi.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P001 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P001); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
