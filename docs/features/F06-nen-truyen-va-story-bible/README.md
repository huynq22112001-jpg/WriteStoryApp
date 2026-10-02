# F06 — Nền truyện và Story Bible

Giai đoạn: R2 (workflow foundation cần job/AI của R2; UI Story Bible đầy đủ làm sau F12 theo thứ tự ở [../README.md](../README.md)). Trạng thái: planned.

## Mục tiêu

Từ brief, AI sinh nền truyện (story frame, volume map, book rules, author intent, nhân vật có bí danh, quan hệ, địa điểm, tình huống mở đầu), quy tắc xưng hô giữa các nhân vật chính, dàn ý sự kiện (`story_events` có phụ thuộc và chương dự kiến) và hooks có `due_by_chapter`; tác giả sửa rồi nhận, app tạo state seed chương 0. Sau đó tác giả xem/sửa toàn bộ Story Bible (nhân vật, xưng hô, facts, hooks quá hạn, dàn ý sự kiện, timeline, state theo chương); sửa khi truyện đang chạy tạo revision áp từ chương kế tiếp.

## Phạm vi

- Trong phạm vi:
  - Job `foundation` 3 giai đoạn: `frame` (story frame + nhân vật), `address_rules`, `event_outline` (sự kiện + hooks); checkpoint theo phần, recover draft (LNG04).
  - Nhận kết quả (có chỉnh sửa) qua `POST /v1/jobs/{id}/accept`; state seed chương 0 (Plan §6.1 bước 4).
  - Bảng: `outlines`, `author_controls`, `characters`, `address_rules`, `story_events`, `hooks`, `facts`, `timeline`, `bible_revisions`; cột `works.foundation_status`, `works.bible_dirty`.
  - CRUD Plan §7 "API bổ sung": `/v1/works/{id}/characters | facts | hooks | story-events | timeline | address-rules`, `GET /v1/works/{id}/state?chapter=N` (đọc; schema do F09).
  - UI Story Bible (UI §5.4): nhân vật (Hồ sơ, Quan hệ, Xuất hiện, Lịch sử thay đổi, **Xưng hô**), địa điểm (chỉ đọc), facts, hooks (quá hạn ⚠), dàn ý sự kiện (planned/done/moved/dropped), timeline lưới, đồ thị quan hệ (lazy), thanh trượt chương xem `StoryState`.
  - Component bước 3–5 cho wizard của [F05](../F05-thu-vien-va-tao-truyen/README.md).
- Ngoài phạm vi:
  - Schema `StoryState`/`StateDelta`, tóm tắt, composer → F09. F06 chỉ tạo snapshot chương 0 theo schema của F09.
  - Xét lại dàn ý mỗi K chương (Plan §23.3 #6, `outline_review.py`), settle/`address.change` sau mỗi chương → F10.
  - Kiểm tra xưng hô trong văn bản (dùng `address_rules`) → F08; nhảy từ finding sang tab Xưng hô thì F11 gọi route của F06.
  - Import truyện có sẵn rồi dựng foundation (ADP02, R3); "Hỏi AI" trong Story Bible (chat, R3) – ẩn trong MVP.
  - Bảng `locations` riêng (Plan §5 chưa có); MVP đọc địa điểm từ `StoryState.locations`.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F05 | Tác phẩm nháp, brief, thể loại, style profile, khung wizard |
| F09 | Schema `StoryState` v1 (Plan §23.1.A) để tạo snapshot chương 0 và đọc state theo chương |
| F10 | Hạ tầng gọi AI có structured output, refusal/truncation (Plan §23.3 #2–#3) dùng chung |
| F04 | `ModelSelection` cho vai trò `planner` |
| F12 | Job bền (`POST /v1/jobs`, checkpoint, resume, cancel, accept) |
| F08 | Chuẩn hóa NFC, fold bí danh có/không dấu, prompt tiếng Việt trong `languages/vi/prompts` |

## Nguồn thiết kế

- Plan §5 (`outlines`, `characters`, `address_rules`, `story_states`, `facts / hooks`, `story_events`, `timeline`), **§6.1** (Brief → Foundation → Event outline → State seed), §6.4 (lớp prompt, sửa story bible áp từ chương kế tiếp), §6.6 (xưng hô, tên riêng/bí danh), §7 (CRUD bổ sung, `/state?chapter=N`, `POST /v1/jobs` foundation), **FL03**, §23.1.A, §23.3 #2 #3 #6, §23.4 #11.
- Plan §15.3 LNG01–LNG04; §15.4 EDT06; §15.5 MEM01–MEM02; §18 (`author_controls`).
- Arch §4 (`fe/src/features/story_bible/`), §6 (`ai/.../workflows/longform/`, `languages/vi/prompts/`), §9 (module BE `longform`).
- UI §4 (route `/works/$workId/bible/$section`), **§5.4** (Story Bible), **§5.7** (wizard), §5.8 (thanh trượt state).
- Review §4.1 (kế hoạch theo sự kiện), §4.6 (`story_events`, hooks mở rộng, `timeline`).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Module `longform`: bảng nền truyện/bible, accept foundation, state seed, CRUD, `bible_revisions`, kiểm tra DAG/xưng hô/hook quá hạn |
| FE | [fe.md](./fe.md) | `features/story_bible`: bước wizard 3–5, trang Story Bible các mục, tab Xưng hô, timeline lưới, thanh trượt state |
| AI | [ai.md](./ai.md) | Workflow `foundation` (frame, address_rules, event_outline), contract structured output, prompt tiếng Việt |

## Tiêu chí hoàn thành

- [ ] Từ brief truyện mẫu tiên hiệp và ngôn tình, job foundation sinh đủ: story frame, volume map, book rules, author intent, ≥ 3 nhân vật có bí danh, quy tắc xưng hô cho mọi cặp nhân vật chính có quan hệ, `story_events` phủ 1..`target_chapters`, hooks có `due_by_chapter`.
- [ ] Phụ thuộc sự kiện không có chu trình; sự kiện phụ thuộc có chương dự kiến ≤ sự kiện phụ thuộc vào nó.
- [ ] Ngắt app giữa job → mở lại thấy phần đã có, "Tiếp tục" chạy từ phần dở, không trả phí lại phần đã xong (LNG04).
- [ ] Nhận nền truyện → có snapshot `StoryState` chương 0, `works.foundation_status=accepted`; work chỉ `ready` khi điều kiện đủ (F05).
- [ ] Hooks quá hạn hiển thị ⚠ và đếm ở menu trái; 100% hook quá hạn được báo (Plan §9 Giai đoạn 4).
- [ ] Sửa Story Bible khi truyện đang chạy: chương đang viết dùng revision đã ghim; chương kế tiếp dùng revision mới; UI ghi "áp từ chương kế tiếp".
- [ ] Thanh trượt chương hiển thị đúng `StoryState` sau chương N.
- [ ] Các test luồng liên quan pass: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md); phần hook/state của [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md).

## Rủi ro và câu hỏi mở

- **Nguồn chuẩn của facts/hooks:** Plan §5 có cả bảng `facts`/`hooks` và snapshot `story_states` chứa `facts[]`/`hooks[]`. Đề xuất ở be.md: bảng là sổ cái hiện hành tác giả sửa được; snapshot là lịch sử bất biến; sửa tay được F09 gộp vào lần commit chương kế tiếp. Cần F09 xác nhận.
- **Tên bảng snapshot:** Plan §5 gọi `story_states`, Plan §18 gọi `state_snapshots`. F06 dùng `story_states`.
- **Không có vai trò "architect"** trong Plan §7.1; F06 dùng vai trò `planner`.
- **Địa điểm:** UI §5.4 có mục "Địa điểm" nhưng Plan §5 không có bảng; MVP chỉ đọc từ state.
- **Tuyến truyện cho timeline:** UI §5.4 "hàng = tuyến truyện" nhưng chưa có trường; đề xuất cột `story_events.storyline`.
- Kích thước dàn ý cho truyện 200+ chương có thể vượt `max_tokens` của một lần gọi → sinh theo từng quyển (ai.md). Chưa đo.
