# P157 – FE: luồng lần chạy đầu

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F03 | [P153](./P153-error-empty-states.md), [P156](./P156-playwright-mock.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P157] FE: luồng lần chạy đầu

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153, P156. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F03-khoi-dau-va-vault/fe.md
- docs/ui-design.vi.md §5.8
- docs/tests/flows/T02-lan-chay-dau-va-vault.md

Việc cần làm:
1. Route /onboarding + stepper: data-root (macOS qua bridge), bảo mật (vault hoặc key theo phiên), provider (form tối thiểu + nút kiểm tra; dùng component P161 nếu đã có), truyện đầu tiên.
2. useOnboardingRedirect khi chưa hoàn tất.
3. Dùng types OpenAPI; API chưa có thì mock và ghi rõ.
4. Test component + e2e.

Phạm vi file: fe/src/features/onboarding/, fe/src/app/router.tsx
Xong khi: test + e2e pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P157 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P157); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
