# P205 – AI: nạp prompt Jinja2 + manifest

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F08 | [P201](./P201-language-pack-mo-rong.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P205] AI: nạp prompt Jinja2 + manifest

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P201. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/ai.md
- docs/implementation-plan.vi.md §23.3 #8, §24 D38

Việc cần làm:
1. `prompts/loader.py`: Jinja2 SandboxedEnvironment, đọc template qua importlib.resources từ `languages/<lang>/prompts/`.
2. manifest.json: id, version, sha8; prompt_version dạng id@version#sha8.
3. Test: render, checksum đổi khi sửa template, chạy được khi đóng gói (resource).

Phạm vi file: ai/src/writestory_ai/prompts/, ai/src/writestory_ai/languages/vi/prompts/, ai/pyproject.toml, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P205 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P205); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
