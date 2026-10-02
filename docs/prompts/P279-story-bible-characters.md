# P279 – FE: Story Bible – nhân vật, xưng hô, facts, hooks

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F06 | [P271](./P271-memory-ui.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P279] FE: Story Bible – nhân vật, xưng hô, facts, hooks

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P271. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F06-nen-truyen-va-story-bible/fe.md
- docs/ui-design.vi.md §5.4

Việc cần làm:
1. Danh sách nhân vật + hồ sơ (bí danh, trạng thái theo chương, xuất hiện), tab Xưng hô (người nói → người nghe → từ xưng/gọi theo giai đoạn), facts, hooks (quá hạn ⚠), địa điểm chỉ đọc.
2. Ghi chú 'áp từ chương kế tiếp' khi đang chạy batch.
3. Test.

Phạm vi file: fe/src/features/story_bible/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P279 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P279); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
