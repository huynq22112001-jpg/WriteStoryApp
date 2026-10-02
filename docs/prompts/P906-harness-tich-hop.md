# P906 – TEST: harness tích hợp + marker luồng

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P905](./P905-mock-provider-mo-rong.md), [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P906] TEST: harness tích hợp + marker luồng

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P905, P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/README.md

Việc cần làm:
1. `tests/integration/conftest.py`: backend thật trên data-root tạm + mock provider theo kịch bản; helper đọc SSE.
2. Marker pytest t01…t17, integration, live (khai báo trong pyproject.toml); `uv run pytest -m t05` chạy đúng một luồng.

Phạm vi file: tests/, pyproject.toml
Xong khi: `uv run pytest tests -q` chạy được.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P906 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P906); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
