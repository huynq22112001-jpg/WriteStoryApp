# P201 – AI: mở rộng LanguagePack + dữ liệu tiếng Việt

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F08 | [P002](./P002-kiem-chung-ai-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P201] AI: mở rộng LanguagePack + dữ liệu tiếng Việt

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P002. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/ai.md
- docs/implementation-plan.vi.md §6.6

Việc cần làm:
1. Mở rộng `languages/base.py`: deterministic_checks, slop_list, genre_presets, prompts_dir (giữ normalize/count_length/search_fold đã có).
2. Dữ liệu trong `languages/vi/data/`: pronouns.json, speech_verbs.txt, tập âm tiết hợp lệ, genres.json đầy đủ (tiên hiệp, kiếm hiệp, huyền huyễn, ngôn tình, đô thị, cung đấu, xuyên không, trinh thám) kèm từ lạc thời.
3. Contracts LanguageFinding, CheckContext; test nạp dữ liệu.

Phạm vi file: ai/src/writestory_ai/languages/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P201 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P201); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
