# P901 – TEST: truyện mẫu tiên hiệp + đô thị

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P001](./P001-cai-moi-truong-uv-python.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P901] TEST: truyện mẫu tiên hiệp + đô thị

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P001. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/README.md (Dữ liệu mẫu)
- docs/tests/flows/T04-tao-truyen-va-nen-truyen.md
- docs/tests/flows/T05-viet-mot-chuong.md

Việc cần làm:
1. `tests/fixtures/stories/tien_hiep_01/` và `do_thi_01/`: nền truyện, nhân vật + bí danh, quy tắc xưng hô, dàn ý sự kiện, 10 chương đã duyệt (JSON + text).
2. Tự viết, không chép truyện có bản quyền.
3. Test nhỏ nạp fixture đúng schema.

Phạm vi file: tests/fixtures/stories/
Xong khi: Fixture nạp được.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P901 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P901); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
