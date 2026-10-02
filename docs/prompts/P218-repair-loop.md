# P218 – AI: vòng sửa cục bộ

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P217](./P217-reviewer-step.md), [P209](./P209-paragraph-ops.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P218] AI: vòng sửa cục bộ

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P217, P209. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (repair)
- docs/implementation-plan.vi.md §6.2 bước 10, §24 D8

Việc cần làm:
1. repair: chỉ khi có blocker hoặc seam fail; trả ParagraphOps cho đoạn vi phạm; quay lại check; tối đa K vòng (mặc định 2) + trần token; hết vòng → repair_exhausted.
2. Test: sửa thành công vòng 1; hết vòng.

Phạm vi file: ai/src/writestory_ai/workflows/longform/repair.py, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P218 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P218); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
