# P234 – BE: bảng handoff, plan, candidate, findings

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F10 / F11 | [P231](./P231-memory-tables.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P234] BE: bảng handoff, plan, candidate, findings

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P231. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/be.md
- docs/features/F11-candidate-review-va-sua/be.md
- docs/implementation-plan.vi.md §5

Việc cần làm:
1. Migration chapter_handoffs, chapter_plans (input_hash), chapter_candidates (kind, status, round, delta_json, seam_json, accepted_paragraph_ids…), chapter_measurements, findings (gộp, kind đầy đủ theo §5, round, needs_confirmation, override_note), outline_proposals.
2. ORM; test schema.

Phạm vi file: be/migrations/versions/, be/src/writestory_be/infrastructure/db/models/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P234 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P234); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
