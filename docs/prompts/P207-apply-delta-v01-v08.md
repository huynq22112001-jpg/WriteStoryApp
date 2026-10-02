# P207 – AI: apply_delta + validator V01–V08

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 | [P206](./P206-storystate-contracts.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P207] AI: apply_delta + validator V01–V08

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P206. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md (luật V01–V15)

Việc cần làm:
1. `state/apply.py` apply_delta thuần (không I/O), trả state mới + hash.
2. Validator xác định V01–V08 theo spec.
3. Test mỗi luật có ca đúng và ca sai (dùng tests/fixtures/state nếu P903 đã có).

Phạm vi file: ai/src/writestory_ai/state/ (hoặc evaluators/), ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P207 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P207); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
