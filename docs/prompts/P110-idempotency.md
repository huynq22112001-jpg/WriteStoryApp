# P110 – Idempotency-Key cho POST

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F01 | [P104](./P104-writer-queue-uow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P110] Idempotency-Key cho POST

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P104. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F01-hop-dong-api-va-su-kien/be.md (mục A.6)

Việc cần làm:
1. `api/idempotency.py`: request_hash, tra/ghi idempotency_records cùng transaction, trùng key khác body → IDEMPOTENCY_CONFLICT.
2. Test: lặp key trả cùng kết quả; khác body → 409; hai request song song cùng key → một kết quả.

Phạm vi file: be/src/writestory_be/api/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P110 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P110); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
