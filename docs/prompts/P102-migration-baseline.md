# P102 – Migration baseline: settings, jobs, events

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 / F01 | [P101](./P101-alembic-setup.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P102] Migration baseline: settings, jobs, events

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P101. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md
- docs/features/F01-hop-dong-api-va-su-kien/be.md (bảng job_events, idempotency_records)
- docs/implementation-plan.vi.md §4.3, §24 D19

Việc cần làm:
1. `be/migrations/versions/0001_baseline.py`: settings, jobs (wait_reason, pinned_json, idempotency_key unique, revision, interrupted_at), job_steps, job_events (seq AUTOINCREMENT, v, ts, type, work_id, job_id, chapter_no, payload_json + index), idempotency_records.
2. ORM models trong `infrastructure/db/models/`.
3. Test: upgrade/downgrade; cột và index đúng spec.

Phạm vi file: be/migrations/versions/, be/src/writestory_be/infrastructure/db/models/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P102 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P102); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
