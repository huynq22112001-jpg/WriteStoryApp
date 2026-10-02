# P214 – AI: bước Writer (nối chương)

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P213](./P213-planner-pacing.md), [P211](./P211-token-tail-text.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P214] AI: bước Writer (nối chương)

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P213, P211. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (bước write)
- docs/review-and-optimization.vi.md §2.3 (InkOS writer không thấy chương trước)

Việc cần làm:
1. Writer LUÔN nhận plan + handoff(N-1) + tail_text(N-1); stream token qua ProgressSink.
2. Cắt max_tokens → viết tiếp từ điểm dừng tối đa 2 lần rồi ghép; refusal → trả kết quả waiting_user (không retry lặp).
3. Test: prompt render chứa tail_text; truncation; refusal.

Phạm vi file: ai/src/writestory_ai/workflows/longform/writer.py, languages/vi/prompts/longform/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P214 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P214); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
