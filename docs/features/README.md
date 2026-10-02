# Tính năng MVP – chia nhỏ để triển khai

Mỗi tính năng là một thư mục, gồm 4 file:

| File | Nội dung |
|---|---|
| `README.md` | Mục tiêu, phạm vi, phụ thuộc, nguồn thiết kế, tiêu chí hoàn thành, liên kết test |
| `be.md` | Backend Python/FastAPI: module, bảng/migration, API, logic, job/event, lỗi, checklist, test |
| `fe.md` | Frontend React: route, màn hình/component, state, API/event dùng, trạng thái UX, i18n, checklist, test |
| `ai.md` | Package AI: contract, workflow, prompt, model/effort, structured output, lỗi, eval, checklist, test. Ghi "Không áp dụng" nếu tính năng không có phần AI |

Mẫu: [_template/](./_template/). Test theo luồng: [../tests/README.md](../tests/README.md).

Nguồn thiết kế gốc: [implementation-plan.vi.md](../implementation-plan.vi.md) (viết tắt **Plan**), [folder-architecture.vi.md](../folder-architecture.vi.md) (**Arch**), [ui-design.vi.md](../ui-design.vi.md) (**UI**), [review-and-optimization.vi.md](../review-and-optimization.vi.md) (**Review**). Khi file tính năng và tài liệu gốc khác nhau, sửa cả hai cho khớp; không để hai bản lệch nhau.

## Danh sách tính năng MVP

| ID | Thư mục | Tính năng | Giai đoạn | Phụ thuộc | Test chính |
|---|---|---|---|---|---|
| F00 | [F00-nen-tang-desktop](./F00-nen-tang-desktop/) | Desktop shell Tauri, vòng đời backend, data-root, single-instance, token, đóng gói | R0 | — | T01 |
| F01 | [F01-hop-dong-api-va-su-kien](./F01-hop-dong-api-va-su-kien/) | Quy ước API, hợp đồng lỗi, luồng sự kiện toàn cục SSE, OpenAPI → TS | R0–R1 | F00 | T17 |
| F02 | [F02-nen-du-lieu](./F02-nen-du-lieu/) | SQLite WAL, migration, writer queue, FTS, asset, khóa truyện | R1 | F00 | T09, T16 |
| F03 | [F03-khoi-dau-va-vault](./F03-khoi-dau-va-vault/) | Onboarding lần chạy đầu, vault API key, mở/khóa vault | R1 | F00, F02 | T02 |
| F04 | [F04-cau-hinh-mo-hinh-ai](./F04-cau-hinh-mo-hinh-ai/) | Provider, tự lấy danh sách model, danh sách model, effort, vai trò, limiter | R1–R2 | F01, F02, F03 | T03, T15 |
| F05 | [F05-thu-vien-va-tao-truyen](./F05-thu-vien-va-tao-truyen/) | Thư viện, wizard tạo truyện, ngôn ngữ, thể loại, style profile | R1 | F01, F02 | T04 |
| F06 | [F06-nen-truyen-va-story-bible](./F06-nen-truyen-va-story-bible/) | Nền truyện, nhân vật, xưng hô, dàn ý sự kiện, hooks, timeline, Story Bible | R2 | F05, F09, F10 | T04 |
| F07 | [F07-editor-va-phien-ban](./F07-editor-va-phien-ban/) | Tiptap, `paragraph_id`, working copy, revision, diff/restore, IME tiếng Việt | R0–R2 | F01, F02 | T12 |
| F08 | [F08-goi-ngon-ngu-vi](./F08-goi-ngon-ngu-vi/) | Gói ngôn ngữ `vi`: chuẩn hóa, đếm âm tiết, search, kiểm tra tiếng Việt, prompt | R2 | F02 | T13 |
| F09 | [F09-trang-thai-va-bo-nho](./F09-trang-thai-va-bo-nho/) | `StoryState`/`StateDelta`, tóm tắt phân tầng, tìm kiếm FTS, composer ngân sách context | R2 | F02, F08 | T14 |
| F10 | [F10-viet-chuong-lien-mach](./F10-viet-chuong-lien-mach/) | Pipeline một chương: plan → write → check → settle → validate → seam → review → sửa → commit | R2 | F04, F07, F08, F09 | T05, T06 |
| F11 | [F11-candidate-review-va-sua](./F11-candidate-review-va-sua/) | Candidate, findings, nhận từng đoạn, sửa theo yêu cầu, `stale_from`/resync | R2 | F07, F10 | T10, T11 |
| F12 | [F12-auto-write-da-truyen](./F12-auto-write-da-truyen/) | Scheduler đa truyện, hàng đợi, khóa, ngân sách, ước tính, Phòng viết | R2 | F04, F10 | T07, T08, T09 |
| F13 | [F13-xuat-va-sao-luu](./F13-xuat-va-sao-luu/) | Export TXT/MD/EPUB, backup/restore | R2 | F02, F07 | T16 |
| F14 | [F14-thong-bao-nhat-ky-chi-phi](./F14-thong-bao-nhat-ky-chi-phi/) | Thông báo, usage/chi phí, log AI debug, giữ máy thức, trang Lưu trữ | R2 | F01, F12 | T15, T17 |

## Thứ tự làm đề xuất

```text
R0: F00 → F01 (khung) → F07 (spike editor + IME)
R1: F02 → F03 → F05 → F04 (kết nối + danh sách model) → F07 (working copy, revision)
R2: F08 → F09 → F10 → F11 → F12 → F06 (UI Story Bible đầy đủ) → F13 → F14
```

Trước khi code R2 phải chốt các hợp đồng "Chặn MVP" của Plan §23.5: `StoryState`/`StateDelta` (F09), `paragraph_id` (F07), event envelope + lỗi (F01), candidate/working copy (F11, F07).

## Backlog sau MVP (chưa tách file)

Tách thành thư mục tính năng khi bắt đầu giai đoạn tương ứng, cùng mẫu 4 file:

| Giai đoạn | Nhóm (Plan §15) |
|---|---|
| R3 | Chat/action engine (CHT06–CHT11), truyện ngắn (SHT), import/fanfic/spinoff/style (ADP), tài liệu tham khảo (MEM06–07), Skills (SKL), forecast (LNG15) |
| R4 | Dịch thuật (TRN), bìa/ảnh (IMG), research/radar, detection, mở rộng provider |
| R5 | Kịch bản, storyboard (SCR) |
| R6 | Interactive film (FIL), Play (PLY) |
| R7 | Scheduler theo lịch, kênh thông báo ngoài, CLI/TUI, migration InkOS, installer ký + update |

## Quy ước chung cho mọi file

- Viết tiếng Việt; tên bảng, cột, API, file code giữ tiếng Anh và **dùng đúng tên trong Plan §5, §7, §23**. Tên mới phải ghi vào mục "Tên mới đề xuất" ở cuối file để đồng bộ lại Plan.
- Đường dẫn code theo Arch: `be/src/writestory_be/...`, `ai/src/writestory_ai/...`, `fe/src/...`.
- Checklist dùng `- [ ]` để đánh dấu tiến độ.
- Mỗi API ghi: method, path, request, response, mã lỗi (theo Plan §23.1.D).
- Không có số liệu chưa đo được ghi như sự thật; giả định ghi rõ là giả định.
