# P213 – AI: bước Planner + nhịp truyện

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P210](./P210-composer-context.md), [P118](./P118-adapter-anthropic.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P213] AI: bước Planner + nhịp truyện

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P210, P118. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (bước plan)
- docs/implementation-plan.vi.md §6.2, §23.3 #5

Việc cần làm:
1. ChapterPlan (sự kiện bắt buộc, hook tiến/trả, cảnh mở nối ending_state N-1, input_hash).
2. PacingBudget: sự kiện còn lại / chương còn lại; cấm kết thúc sớm trừ allow_early_ending.
3. Kiểm tra xác định plan + một lần sửa JSON; test với mock.

Phạm vi file: ai/src/writestory_ai/workflows/longform/planner.py, pacing.py, languages/vi/prompts/longform/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P213 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P213); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
