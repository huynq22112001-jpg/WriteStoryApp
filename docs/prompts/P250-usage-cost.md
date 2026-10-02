# P250 – BE: ghi usage + chi phí

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F14 | [P235](./P235-write-job-runner.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P250] BE: ghi usage + chi phí

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P235. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F14-thong-bao-nhat-ky-chi-phi/be.md
- docs/implementation-plan.vi.md §24 D3

Việc cần làm:
1. Migration usage_records (mỗi request) + usage_counters (ngày/timezone, truyện, provider); giá từ provider_models; token cache.
2. GET /v1/usage/summary, /v1/usage/records; event usage.updated.
3. Test.

Phạm vi file: be/src/writestory_be/modules/operations/usage*, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P250 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P250); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
