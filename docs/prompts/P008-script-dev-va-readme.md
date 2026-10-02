# P008 – Script chạy dev BE+FE và README gốc

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| Tất cả | S06 | [P005](./P005-chay-thu-dev-health.md), [P004](./P004-kiem-chung-fe-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P008] Script chạy dev BE+FE và README gốc

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P005, P004. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S06-chay-dev.md
- docs/folder-architecture.vi.md

Việc cần làm:
1. `tools/dev/run_dev.py`: chạy song song BE `--dev` và `pnpm --filter fe dev`, log có tiền tố [be]/[fe], Ctrl+C tắt cả hai (Windows + macOS).
2. Script gốc `"dev": "uv run python tools/dev/run_dev.py"`.
3. README.md gốc: giới thiệu, công cụ cần (S00), cấu trúc thư mục, lệnh cài/test/dev/build, link docs/README.md.
4. Thử mở http://localhost:5173/#/system: health ok, nút mock 3 truyện stream được, tắt BE thì banner nối lại.

Phạm vi file: tools/dev/, package.json (scripts), README.md
Xong khi: Bước thử cuối đúng mô tả (ghi quan sát vào báo cáo).

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P008 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P008); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
