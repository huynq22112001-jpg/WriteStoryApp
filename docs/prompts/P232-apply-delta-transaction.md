# P232 – BE: áp StateDelta trong một transaction

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F09 | [P231](./P231-memory-tables.md), [P208](./P208-validator-v09-v15.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P232] BE: áp StateDelta trong một transaction

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P231, P208. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/be.md
- docs/implementation-plan.vi.md §23.1.A (sổ cái + lịch sử)

Việc cần làm:
1. Service áp delta: gọi apply_delta + validator của AI, ghi story_states + sổ cái (facts/hooks/timeline/story_events) trong cùng transaction qua UnitOfWork.
2. Sửa Story Bible bằng tay → StateDelta nguồn user.
3. Test bất biến: chiếu sổ cái tại N = snapshot N; delta sai → không ghi gì.

Phạm vi file: be/src/writestory_be/modules/memory/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P232 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P232); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
