# P231 – BE: bảng trạng thái và bộ nhớ

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F09 | [P126](./P126-chapters-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P231] BE: bảng trạng thái và bộ nhớ

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P126. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/be.md
- docs/implementation-plan.vi.md §5, §23.1.A, §24 D34–D36

Việc cần làm:
1. Migration story_states (state_hash, delta_json, parent_state_id, is_current), facts, hooks (due_by_chapter, history), timeline, story_events (storyline, locked), summaries, context_traces, state_pending_deltas, author_controls.
2. ORM models; test schema.

Phạm vi file: be/migrations/versions/, be/src/writestory_be/infrastructure/db/models/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P231 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P231); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
