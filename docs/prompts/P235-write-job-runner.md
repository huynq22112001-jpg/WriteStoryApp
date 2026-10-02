# P235 – BE: job viết chương chạy pipeline

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F10 | [P234](./P234-longform-tables.md), [P233](./P233-memory-api-context-port.md), [P219](./P219-pipeline-orchestration.md), [P124](./P124-models-roles-resolver.md), [P125](./P125-limiter-provider.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P235] BE: job viết chương chạy pipeline

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P234, P233, P219, P124, P125. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/be.md
- docs/implementation-plan.vi.md §4.3, FL04

Việc cần làm:
1. Job type write: lấy khóa truyện, ghim model+effort (model_resolver), dựng ports (ContextPort, ProgressSink → events + checkpoint, ProviderLimiterPort), gọi pipeline P219.
2. `infrastructure/ai/progress_adapter.py`; partial candidate lưu theo checkpoint; resume sau interrupted.
3. Test integration với mock: kill giữa chừng → resume đúng bước.

Phạm vi file: be/src/writestory_be/modules/longform/, be/src/writestory_be/jobs/, be/src/writestory_be/infrastructure/ai/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P235 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P235); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
