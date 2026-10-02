# F05 — Thư viện và tạo truyện

Giai đoạn: R1 (thư viện, CRUD tác phẩm, wizard bước không cần AI, style profile); bước AI của wizard nối với F06 ở R2. Trạng thái: planned.

## Mục tiêu

Người dùng xem mọi tác phẩm trong thư viện (lưới card hoặc bảng, ảo hóa, badge trạng thái liền mạch + job), tìm/lọc, mở truyện, và tạo truyện mới qua wizard nhiều bước: ngôn ngữ (MVP chỉ tiếng Việt) → thể loại + style profile → brief → nền truyện → xưng hô → dàn ý sự kiện → cấu hình viết → tạo. Mỗi bước lưu nháp, đóng giữa chừng mở lại được.

## Phạm vi

- Trong phạm vi:
  - CRUD bảng `works` (tạo nháp, sửa metadata, lưu trữ, xóa vào thùng rác, mở gần đây).
  - Bảng `style_profile` (một hồ sơ/tác phẩm) và API `/v1/works/{id}/style-profile`.
  - Preset thể loại đọc từ gói ngôn ngữ (`ai/src/writestory_ai/languages/vi/genres.json`), danh sách ngôn ngữ (MVP: `vi`).
  - Trang Thư viện (UI §5.1): lưới/bảng, TanStack Virtual, tìm kiếm không dấu, lọc thể loại/trạng thái, badge từ `continuity_status` + trạng thái job.
  - Khung wizard (UI §5.7): stepper, lưu nháp mỗi bước, mở lại đúng bước; các bước 1, 2, 6, 7 do F05 làm; bước 3–5 nhúng component của F06.
  - Cấu hình viết theo truyện: độ dài chương theo âm tiết, chế độ auto-write mặc định, K, ngân sách theo truyện, ghi đè vai trò (gọi API F04).
- Ngoài phạm vi:
  - Sinh nền truyện, nhân vật, xưng hô, dàn ý sự kiện, hooks, state seed chương 0 → [F06](../F06-nen-truyen-va-story-bible/README.md).
  - Workspace 3 cột, editor → F07; Phòng viết → F12; chi phí chi tiết → F14.
  - Ảnh bìa sinh bằng AI (IMG, R4); bìa trong MVP chỉ là ảnh người dùng chọn (tùy chọn) hoặc placeholder.
  - CRUD preset thể loại do người dùng tạo (NEW06, R3).
  - Projects/không gian làm việc nhiều project: MVP dùng một project ngầm định.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F01 | Hợp đồng lỗi, envelope event (`work.continuity`, `job.state`, `queue.changed`, `chapter.committed`), OpenAPI → TS |
| F02 | SQLite/migration/writer queue, asset (ảnh bìa) |
| F04 (mềm) | Bước "Cấu hình viết" ghi đè vai trò theo truyện qua `PUT /v1/settings/roles?work_id=` |
| F06 (R2) | Bước 3–5 của wizard và điều kiện chuyển `draft → ready` |
| F08 (mềm) | `search_normalizer` cho tìm kiếm không dấu và preset thể loại; R1 dùng bản tối giản (xem be.md) |
| F12 (mềm) | Trạng thái job/hàng đợi cho badge; trước khi có F12, badge chỉ dựa trên `continuity_status` và `status` |

## Nguồn thiết kế

- Plan §1 (đa ngôn ngữ, `vi` trước), §4.4 (thư viện 50 tác phẩm/10.000 chương – tiêu chí đề xuất, chưa đo), §5 (`projects`, `works`, `style_profile`), §6.1 bước Brief, §6.6 (style profile, độ dài theo âm tiết, preset thể loại), §7 (`GET/POST/PATCH /v1/works`, CRUD `style-profile`), FL03 bước 1, §23.1.D.
- Plan §15.1 WRK01–WRK03, WRK09; §15.15 OPS10.
- Arch §4 (`fe/src/features/library/`), §5 (`be/.../modules/works/`), §6 (`languages/vi/genres.json`).
- UI §4 (route `/`, `/new`), **§5.1** (Thư viện), **§5.7** (Wizard), §5.8 (mẫu trạng thái), §6 (ảo hóa).
- Review §4.4 (`continuity_status`), §5.3 (trạng thái job).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Module `works`: bảng `works`, `style_profile`; API thư viện/CRUD/style profile/ngôn ngữ/thể loại; tính badge; chuyển trạng thái `draft → ready` |
| FE | [fe.md](./fe.md) | `features/library`: LibraryPage (lưới/bảng ảo hóa), WorkStatusBadge, wizard 7 bước lưu nháp |
| AI | [ai.md](./ai.md) | Không áp dụng – sinh nền truyện thuộc F06 |

## Tiêu chí hoàn thành

- [ ] Tạo, sửa, lưu trữ, xóa (thùng rác) tác phẩm; dữ liệu còn sau restart.
- [ ] Thư viện hiển thị ≥ 50 tác phẩm mượt (ảo hóa), chuyển lưới/bảng, lọc thể loại/trạng thái, tìm "nguyen" ra "Nguyễn", "duong" ra "Đường".
- [ ] Badge đúng bảng ưu tiên ở be.md, cập nhật trực tiếp qua SSE không cần tải lại trang.
- [ ] Wizard: đóng app ở bất kỳ bước nào rồi mở lại → quay đúng bước, dữ liệu các bước trước còn nguyên.
- [ ] Chỉ chọn được ngôn ngữ "Tiếng Việt"; `works.language` khác `vi` bị từ chối.
- [ ] `PATCH status=ready` bị từ chối khi nền truyện chưa được nhận (chi tiết thiếu gì trong `detail.missing`).
- [ ] Style profile lưu đủ: Hán Việt/thuần Việt, kiểu thoại, kiểu bỏ dấu, dấu câu, cụm sáo cấm, giọng văn, đoạn mẫu giọng văn.
- [ ] Các test luồng liên quan pass: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md).

## Rủi ro và câu hỏi mở

- **Thứ tự phụ thuộc:** F05 ở R1 nhưng preset thể loại thuộc gói ngôn ngữ (F08, R2). Đề xuất: R1 tạo sẵn `genres.json` tối thiểu và đọc file trực tiếp; F08 hoàn thiện nội dung và interface `LanguagePack.genre_presets()`.
- **Bảng `projects`** (Plan §5) chưa có use case MVP; đề xuất một project mặc định tạo trong migration, `works.project_id` trỏ tới nó.
- **Badge chi phí** "$3.20" trong UI §5.1 cần tổng usage theo truyện (F14); trước khi có F14 hiển thị "—".
- **Xóa tác phẩm** (WRK09) cần backup trước khi purge (F13); MVP chỉ soft delete, purge từ trang Lưu trữ (F14) – cần chốt chủ sở hữu thao tác purge.
- Wizard đặt "Quy tắc xưng hô" trước "Dàn ý sự kiện" (UI §5.7) trong khi FL03 không nêu thứ tự; giữ thứ tự UI.
