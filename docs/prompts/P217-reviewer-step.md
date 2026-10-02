# P217 – AI: bước Review

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P216](./P216-validate-seam.md), [P202](./P202-kiem-tra-xung-ho.md), [P203](./P203-kiem-tra-ten-lop-tu.md), [P204](./P204-kiem-tra-slop-chinh-ta.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P217] AI: bước Review

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P216, P202, P203, P204. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (review)
- docs/implementation-plan.vi.md §24 D7

Việc cần làm:
1. Gộp findings: kiểm tra xác định (chung + gói vi) + review LLM; mức blocker/major/minor theo D7; xác nhận các finding needs_confirmation.
2. Test.

Phạm vi file: ai/src/writestory_ai/workflows/longform/reviewer.py, evaluators/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P217 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P217); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
