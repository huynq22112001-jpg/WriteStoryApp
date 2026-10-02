# P163 – FE: vai trò & effort, đồng thời & ngân sách

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F04 / F12 | [P161](./P161-settings-models-connection.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P163] FE: vai trò & effort, đồng thời & ngân sách

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P161. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/ui-design.vi.md §5.6.2, §5.6.3
- docs/features/F04-cau-hinh-mo-hinh-ai/fe.md

Việc cần làm:
1. /settings/roles: bảng vai trò → model + effort, ghi chú giữ effort cố định trong một lượt viết.
2. /settings/concurrency: số truyện song song, request đồng thời/provider, RPM/TPM, ngân sách ngày/truyện.
3. /settings/writing: chế độ auto-write mặc định, K, vòng sửa tối đa, độ dài chương (âm tiết).
4. Test.

Phạm vi file: fe/src/features/settings/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P163 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P163); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
