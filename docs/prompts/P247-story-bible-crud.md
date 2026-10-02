# P247 – BE: CRUD Story Bible + bible_revisions

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F06 | [P246](./P246-foundation-job.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P247] BE: CRUD Story Bible + bible_revisions

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P246. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F06-nen-truyen-va-story-bible/be.md
- docs/implementation-plan.vi.md §6.4 (không phá cache), §24 D26

Việc cần làm:
1. CRUD characters, facts, hooks, story-events, timeline, address-rules, style-profile; ghi qua StateDelta nguồn user.
2. bible_revisions: thay đổi áp từ chương kế tiếp.
3. Test.

Phạm vi file: be/src/writestory_be/modules/bible/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P247 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P247); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
