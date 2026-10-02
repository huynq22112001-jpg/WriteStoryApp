# P237 – BE: API liền mạch + chỉ số

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F10 | [P236](./P236-commit-gate.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P237] BE: API liền mạch + chỉ số

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P236. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/be.md
- docs/implementation-plan.vi.md §9 Giai đoạn 4

Việc cần làm:
1. GET /v1/works/{id}/continuity, /continuity/metrics (state_applied=false, seam pass, tên ngoài canon, xưng hô, hook quá hạn, n-gram), GET/PUT /v1/chapters/{id}/plan, GET /seam, PUT /handoff, outline-proposals apply/reject.
2. Test.

Phạm vi file: be/src/writestory_be/modules/longform/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P237 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P237); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
