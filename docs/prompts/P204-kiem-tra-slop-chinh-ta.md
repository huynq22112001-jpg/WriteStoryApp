# P204 – AI: cụm sáo, chính tả, kiểu bỏ dấu, thoại

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F08 | [P201](./P201-language-pack-mo-rong.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P204] AI: cụm sáo, chính tả, kiểu bỏ dấu, thoại

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P201. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/ai.md
- docs/implementation-plan.vi.md §24 D7, D37, D45
- docs/tests/flows/T13-kiem-tra-tieng-viet.md

Việc cần làm:
1. vi.slop (regex, minor, mật độ), vi.spelling (âm tiết không hợp lệ + Telex sót; ghi rõ giới hạn hỏi/ngã – D45), vi.accent_mix (hoà/hòa lẫn), vi.dialogue (ký tự gạch/ngoặc).
2. Test.

Phạm vi file: ai/src/writestory_ai/languages/vi/checks/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P204 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P204); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
