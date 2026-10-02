# P210 – AI: Composer ngữ cảnh theo lớp

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 | [P206](./P206-storystate-contracts.md), [P205](./P205-prompt-loader.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P210] AI: Composer ngữ cảnh theo lớp

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P206, P205. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md
- docs/implementation-plan.vi.md §6.4

Việc cần làm:
1. `context/composer.py`: 4 lớp (app → truyện → chương → lượt), khối bảo vệ không nén (plan, handoff, tail_text), khối nén được, ContextPackage + ContextTrace.
2. Đọc dữ liệu qua ContextPort (không chạm DB).
3. Test: không bao giờ cắt khối bảo vệ; vượt ngân sách bảo vệ → CONTEXT_PROTECTED_OVER_BUDGET.

Phạm vi file: ai/src/writestory_ai/context/, ai/src/writestory_ai/ports/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P210 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P210); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
