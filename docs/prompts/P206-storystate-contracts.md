# P206 – AI: contract StoryState + StateDelta

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 | [P002](./P002-kiem-chung-ai-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P206] AI: contract StoryState + StateDelta

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P002. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md (schema + bảng op)
- docs/implementation-plan.vi.md §23.1.A, §24 D34–D36

Việc cần làm:
1. `contracts/state.py`: StoryState, mọi op StateDelta (character.add/update/move/learn, relationship.set, address.change, location.add, fact.add/close, hook.open/advance/resolve(as_superseded)/defer, event.done/move/drop, time.advance(in_flashback)), evidence hoặc reason, EndingState, TailText.
2. Test schema (JSON round-trip, op thiếu evidence bị từ chối).

Phạm vi file: ai/src/writestory_ai/contracts/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P206 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P206); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
