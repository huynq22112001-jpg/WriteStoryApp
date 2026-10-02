# P246 – BE: job nền truyện + seed state

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F06 | [P232](./P232-apply-delta-transaction.md), [P222](./P222-foundation-workflow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P246] BE: job nền truyện + seed state

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P232, P222. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F06-nen-truyen-va-story-bible/be.md
- docs/tests/flows/T04-tao-truyen-va-nen-truyen.md

Việc cần làm:
1. Job type foundation gọi P222, checkpoint 3 giai đoạn, recover bản nháp dở, waiting_user chờ tác giả duyệt.
2. Seed story_states chương 0 qua P232; GET /v1/works/{id}/foundation, PUT /foundation/{section}.
3. Test T04 phần BE.

Phạm vi file: be/src/writestory_be/modules/bible/ (hoặc foundation/), be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P246 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P246); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
