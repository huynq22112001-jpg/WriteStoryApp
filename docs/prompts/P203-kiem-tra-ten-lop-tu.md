# P203 – AI: kiểm tra tên riêng + lớp từ

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F08 | [P201](./P201-language-pack-mo-rong.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P203] AI: kiểm tra tên riêng + lớp từ

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P201. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/ai.md (vi.name_variant, vi.lexicon)
- docs/tests/flows/T13-kiem-tra-tieng-viet.md

Việc cần làm:
1. vi.name_variant: tên/bí danh có/không dấu, lẫn Hán Việt – thuần Việt khi canon không cho phép, tên mới chưa khai báo.
2. vi.lexicon: từ hiện đại trong truyện cổ trang theo thể loại; lạm dụng Hán Việt theo vocab_register.
3. Test.

Phạm vi file: ai/src/writestory_ai/languages/vi/checks/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P203 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P203); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
