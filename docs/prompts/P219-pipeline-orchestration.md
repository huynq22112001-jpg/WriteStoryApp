# P219 – AI: điều phối pipeline một chương

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P218](./P218-repair-loop.md), [P212](./P212-summaries.md), [P121](./P121-retry-limiter-port.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P219] AI: điều phối pipeline một chương

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P218, P212, P121. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md
- docs/implementation-plan.vi.md §6.2

Việc cần làm:
1. `workflows/longform/pipeline.py`: chạy 11 bước, checkpoint qua CheckpointSink, resume_from, CancelToken, gọi provider qua ProviderLimiterPort; trả PipelineResult (candidate, delta, ending_state, findings, usage, trạng thái).
2. KHÔNG ghi DB.
3. Test contract với mock: thành công; seam fail → sửa → pass; repair_exhausted; refusal; JSON hỏng; resume từ giữa.

Phạm vi file: ai/src/writestory_ai/workflows/longform/, ai/tests/contract/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P219 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P219); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
