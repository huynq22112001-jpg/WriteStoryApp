# P908 – Nghiệm thu MVP: 3 truyện × 20 chương

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| Tất cả | Plan §9 G4 | [P245](./P245-estimate-queues.md), [P241](./P241-chapter-structure-rules.md), [P247](./P247-story-bible-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P908] Nghiệm thu MVP: 3 truyện × 20 chương

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P245, P241, P247. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/implementation-plan.vi.md §9 Giai đoạn 4, §21
- docs/tests/flows/T07-auto-write-mot-truyen.md
- docs/tests/flows/T08-da-truyen-dong-thoi.md
- docs/tests/flows/T14-truyen-dai-va-ngu-canh.md

Việc cần làm:
1. Chạy 3 truyện mẫu × 20 chương song song với mock provider (provider thật chỉ khi tôi cho phép, đánh dấu live).
2. Đo: chương state_applied=false, seam pass sau ≤2 vòng, tên ngoài canon, lỗi xưng hô, hook quá hạn được báo, n-gram trùng giữa chương liền kề.
3. Ghi `docs/reports/mvp-acceptance.md` với số liệu thật; chỉ số chưa đo không ghi 'đạt'.

Phạm vi file: tests/, docs/reports/
Xong khi: Có báo cáo số liệu đo được.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P908 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P908); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
