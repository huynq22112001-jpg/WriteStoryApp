# P124 – BE: thứ tự model, vai trò, model_resolver

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F04 | [P123](./P123-discovery-service.md), [P115](./P115-works-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P124] BE: thứ tự model, vai trò, model_resolver

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P123, P115. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/be.md
- docs/implementation-plan.vi.md §7.1, §24 D13, D17

Việc cần làm:
1. GET/PUT /v1/providers/{id}/models (thứ tự, đầu = mặc định, sửa metadata).
2. Migration role_models; GET/PUT /v1/settings/roles (toàn app + ?work_id=).
3. `infrastructure/ai/model_resolver.py`: thứ tự áp dụng vai trò truyện → app → mặc định → provider; chỉ effort model hỗ trợ; ghim vào job (PinnedModelConfig).
4. Test.

Phạm vi file: be/src/writestory_be/modules/providers/, be/src/writestory_be/infrastructure/ai/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P124 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P124); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
