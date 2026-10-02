# Test theo luồng – MVP

Mỗi luồng nghiệp vụ có một file test trong [flows/](./flows/). Mẫu: [_template.md](./_template.md). Tính năng liên quan: [../features/README.md](../features/README.md).

## Cấp độ test

| Cấp | Phạm vi | Công cụ | Nơi đặt |
|---|---|---|---|
| unit | Hàm/domain thuần, không I/O | pytest, Vitest | `be/tests/unit`, `ai/tests/unit`, cạnh component FE |
| contract | AI workflow với mock provider; schema API/event | pytest + mock provider; snapshot OpenAPI | `ai/tests/contract`, `be/tests/contract` |
| integration | BE + AI + SQLite thật (data-root tạm) + mock provider | pytest-asyncio | `be/tests/integration`, `tests/integration` |
| e2e-fe | FE thật + mock backend | Playwright | `fe/tests/e2e` |
| desktop | App đã đóng gói trên Windows/macOS | smoke script + thủ công | `tests/desktop` |
| thủ công | IME tiếng Việt, đọc chất lượng văn | checklist trong file luồng | — |

## Mock provider

Một provider giả dùng chung cho contract/integration/e2e (`ai/tests/fixtures/mock_provider.py`), cấu hình theo kịch bản:

| Tham số | Ví dụ |
|---|---|
| `latency_ms`, `tokens_per_sec` | Mô phỏng stream thật |
| `fail_sequence` | `[429(retry_after=2), 500, ok]` |
| `refusal_on` | Bước/prompt nào trả refusal |
| `truncate_on` | Bước nào dừng do `max_tokens` |
| `bad_json_on` | Bước structured output trả JSON hỏng |
| `disconnect_after_tokens` | Mất kết nối giữa stream |
| `scripted_outputs` | Văn bản/JSON cố định theo bước để test xác định |
| `models_endpoint` | Response `/v1/models` kiểu Anthropic hoặc OpenAI-compatible |

## Dữ liệu mẫu

- `tests/fixtures/stories/`: truyện mẫu tiếng Việt (tiên hiệp/kiếm hiệp, ngôn tình/đô thị) gồm nền truyện, nhân vật, xưng hô, dàn ý sự kiện, vài chương đã duyệt.
- `tests/fixtures/state/`: `StoryState` mẫu theo chương, kể cả trạng thái lỗi để test validator.
- Không chứa API key thật hay dữ liệu cá nhân.

## Danh sách luồng

| ID | File | Luồng | Tính năng | Plan |
|---|---|---|---|---|
| T01 | [T01-khoi-dong-va-data-root](./flows/T01-khoi-dong-va-data-root.md) | Khởi động, data-root, single-instance, tắt app | F00 | FL01, §3 |
| T02 | [T02-lan-chay-dau-va-vault](./flows/T02-lan-chay-dau-va-vault.md) | Onboarding, vault tạo/mở/khóa | F03 | §23.4 |
| T03 | [T03-cau-hinh-mo-hinh-ai](./flows/T03-cau-hinh-mo-hinh-ai.md) | Kết nối, lấy danh sách model, danh sách ghi đè, effort, vai trò | F04 | §7.1 |
| T04 | [T04-tao-truyen-va-nen-truyen](./flows/T04-tao-truyen-va-nen-truyen.md) | Wizard, nền truyện, dàn ý sự kiện, xưng hô | F05, F06 | FL03 |
| T05 | [T05-viet-mot-chuong](./flows/T05-viet-mot-chuong.md) | Viết một chương thành công, handoff, commit | F10 | FL04, §6.2 |
| T06 | [T06-chuong-loi-va-bi-chan](./flows/T06-chuong-loi-va-bi-chan.md) | Seam fail, validator fail, vòng sửa, `blocked_needs_resync` | F10, F11 | FL04, §6.2 |
| T07 | [T07-auto-write-mot-truyen](./flows/T07-auto-write-mot-truyen.md) | Auto-write N chương, 3 chế độ duyệt | F12 | FL05 |
| T08 | [T08-da-truyen-dong-thoi](./flows/T08-da-truyen-dong-thoi.md) | Nhiều truyện song song, công bằng, rate limit, ngân sách | F12 | §4.2 |
| T09 | [T09-huy-crash-va-phuc-hoi](./flows/T09-huy-crash-va-phuc-hoi.md) | Cancel, kill process, interrupted, resume | F02, F12 | §4.3 |
| T10 | [T10-sua-tay-va-resync](./flows/T10-sua-tay-va-resync.md) | Sửa tay khi auto-write, `stale_from`, resync, chèn/xóa chương | F11, F07 | FL07, §23.2 |
| T11 | [T11-candidate-va-xung-dot](./flows/T11-candidate-va-xung-dot.md) | Candidate, nhận từng đoạn, 409, revise | F11 | FL06 |
| T12 | [T12-editor-autosave-ime](./flows/T12-editor-autosave-ime.md) | Autosave, revision, diff/restore, IME tiếng Việt | F07 | §23.2, R0 |
| T13 | [T13-kiem-tra-tieng-viet](./flows/T13-kiem-tra-tieng-viet.md) | Xưng hô, lớp từ, chính tả, cụm sáo, đếm âm tiết, tìm kiếm | F08 | §6.6 |
| T14 | [T14-truyen-dai-va-ngu-canh](./flows/T14-truyen-dai-va-ngu-canh.md) | 200+ chương: tóm tắt phân tầng, ngân sách context, nhịp truyện | F09, F10 | §23.3 |
| T15 | [T15-loi-provider](./flows/T15-loi-provider.md) | Refusal, cắt output, JSON hỏng, mất mạng, vault khóa, 429 | F04, F10, F12 | §23.3 |
| T16 | [T16-xuat-va-sao-luu](./flows/T16-xuat-va-sao-luu.md) | Export, backup khi đang viết, restore | F13 | FL25 |
| T17 | [T17-phong-viet-va-su-kien](./flows/T17-phong-viet-va-su-kien.md) | Phòng viết, event stream, reconnect, thông báo | F01, F12, F14 | §23.1.C |

## Quy tắc

- Mỗi kịch bản có ID (`T05-03`), bước, kết quả mong đợi, cấp test và trạng thái tự động hóa.
- Mỗi luồng có ít nhất: thành công, lỗi, hủy, phục hồi (nếu áp dụng).
- Test không gọi AI thật mặc định; test với provider thật chỉ chạy khi cấu hình rõ, đánh dấu `live`.
- Chỉ số liền mạch (Plan §9 Giai đoạn 4) được kiểm ở T05–T08 và T14.
