# P238 – BE: nhận candidate (cả chương / từng đoạn)

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F11 | [P236](./P236-commit-gate.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P238] BE: nhận candidate (cả chương / từng đoạn)

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P236. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/be.md
- docs/implementation-plan.vi.md §24 D4
- docs/tests/flows/T11-candidate-va-xung-dot.md

Việc cần làm:
1. GET /v1/chapters/{id}/candidates, GET /v1/candidates/{id}, POST /v1/candidates/{id}/accept {paragraph_ids?, expected_revision, note?} | reject.
2. 409 kèm dữ liệu 3 bên (base, hiện tại, candidate); vòng đời candidate.
3. Test T11 phần BE.

Phạm vi file: be/src/writestory_be/modules/longform/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P238 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P238); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
