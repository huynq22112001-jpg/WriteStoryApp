# P272 – FE: tab AI + CandidateStream

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F10 | [P164](./P164-workspace-chapter-tree.md), [P154](./P154-event-bus-fe.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P272] FE: tab AI + CandidateStream

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P164, P154. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/fe.md
- docs/ui-design.vi.md §5.2, §6, §24 D41

Việc cần làm:
1. Tab AI: ô yêu cầu, nút Viết tiếp/Sửa đoạn chọn, CandidateStream (pane riêng, gom token, nối theo candidate_id + offset), tiến độ pipeline (ánh xạ 11 bước → hiển thị), nút Xem diff / Nhận / Bỏ.
2. Test: stream nhiều token không làm editor render lại.

Phạm vi file: fe/src/features/ai_workspace/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P272 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P272); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
