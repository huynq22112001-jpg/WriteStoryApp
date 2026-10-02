# P202 – AI: kiểm tra xưng hô vi.address

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F08 | [P201](./P201-language-pack-mo-rong.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P202] AI: kiểm tra xưng hô vi.address

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P201. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/ai.md (vi.address)
- docs/implementation-plan.vi.md §24 D44
- docs/tests/flows/T13-kiem-tra-tieng-viet.md

Việc cần làm:
1. Tách đoạn thoại (gạch đầu dòng/ngoặc kép theo style_profile).
2. Xác định người nói/người nghe bằng heuristic có độ tin cậy high/medium; so với address_rules hiệu lực theo chương; address.change trong delta hợp lệ hóa.
3. Mức: high+high → blocker; có medium → major + needs_confirmation; không có luật → bỏ qua.
4. Test các ca T13 về xưng hô.

Phạm vi file: ai/src/writestory_ai/languages/vi/checks/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P202 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P202); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
