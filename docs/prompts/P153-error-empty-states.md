# P153 – FE: ErrorState, EmptyState, Skeleton, toast

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F01 | [P150](./P150-shadcn-base-ui.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P153] FE: ErrorState, EmptyState, Skeleton, toast

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P150. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F01-hop-dong-api-va-su-kien/fe.md
- docs/implementation-plan.vi.md §23.1.D

Việc cần làm:
1. `shared/ui/ErrorState.tsx` (thông báo theo code, nút theo action), EmptyState, LoadingSkeleton.
2. `app/errorActions.ts`: ánh xạ action → hành vi (retry, reload, unlock_vault, open_provider_settings…).
3. Toast sonner cho lỗi mutation.
4. Test component.

Phạm vi file: fe/src/shared/ui/, fe/src/app/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P153 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P153); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
