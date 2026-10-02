# P252 – BE: log AI debug + lưu trữ + dọn dẹp

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F14 | [P235](./P235-write-job-runner.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P252] BE: log AI debug + lưu trữ + dọn dẹp

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P235. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F14-thong-bao-nhat-ky-chi-phi/be.md
- docs/implementation-plan.vi.md §23.2 #10 #11

Việc cần làm:
1. Log request/response AI tùy chọn (mặc định tắt) vào data/logs/ai/, che secret, giới hạn dung lượng.
2. GET /v1/storage (dung lượng theo loại), POST /v1/storage/cleanup theo retention; GET /v1/logs.
3. Test.

Phạm vi file: be/src/writestory_be/modules/operations/, be/src/writestory_be/infrastructure/logging/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P252 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P252); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
