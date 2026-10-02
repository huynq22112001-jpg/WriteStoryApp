# F06 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/new?workId=&step=foundation\|address_rules\|event_outline` | Bước 3–5 của wizard (UI §5.7) | Khung wizard thuộc F05; F06 cung cấp component bước |
| `/works/$workId/bible/$section` | Story Bible (UI §5.4) | `$section ∈ foundation \| characters \| locations \| facts \| hooks \| events \| timeline \| graph` |
| `/works/$workId/bible/characters?character=&tab=profile\|relations\|appearances\|history\|address` | Hồ sơ nhân vật | `tab=address` là đích khi bấm lỗi xưng hô ở Review (F11) |
| `/works/$workId?mode=bible` | Workspace mode Bible | Điều hướng sang route Story Bible |

Search param chung `?chapter=N` cho thanh trượt state (mặc định = chương committed mới nhất).

## Component

```text
fe/src/features/story_bible/
  pages/StoryBiblePage.tsx           Menu trái + vùng nội dung + thanh trượt chương
  components/BibleNav.tsx            Nhân vật (n), Địa điểm, Sự kiện/Facts, Hooks (x mở, y quá hạn ⚠), Dàn ý sự kiện, Timeline, Đồ thị quan hệ, Nền truyện
  components/ChapterStateSlider.tsx
  components/AppliesNextChapterBanner.tsx
  components/foundation/FoundationView.tsx      Story frame, volume map, book rules, author intent, current focus (sửa Markdown)
  components/foundation/FoundationJobPanel.tsx  Tiến độ theo phần, phần dở, Tiếp tục / Tạo lại phần / Hủy
  components/characters/CharacterList.tsx       Ảo hóa + lọc
  components/characters/CharacterDetail.tsx     Tab Hồ sơ | Quan hệ | Xuất hiện | Lịch sử thay đổi | Xưng hô
  components/characters/AliasEditor.tsx
  components/address/AddressRulesTable.tsx      Người nói → người nghe → xưng/gọi, giai đoạn
  components/events/EventOutlineTable.tsx       story_events: trạng thái, chương dự kiến, phụ thuộc, khóa
  components/hooks/HookList.tsx
  components/facts/FactList.tsx
  components/timeline/TimelineGrid.tsx          Cột = chương, hàng = tuyến truyện, card kéo thả (dnd-kit)
  components/graph/RelationshipGraph.tsx        React Flow, lazy
  components/locations/LocationList.tsx         Chỉ đọc từ StoryState
  wizard/FoundationStep.tsx, AddressRulesStep.tsx, EventOutlineStep.tsx
  hooks/useFoundation.ts, useBibleCollection.ts, useStoryState.ts, useBibleRevisionStatus.ts
  api/foundation.ts, api/bible.ts
  index.ts                                      Export 3 bước wizard + link builder tới tab Xưng hô
```

| Component | Trách nhiệm |
|---|---|
| `FoundationStep` | Nút "Sinh nền truyện" (POST job `stage=frame`), `FoundationJobPanel` khi chạy; khi có candidate: form sửa story frame, volume map, book rules, author intent, danh sách nhân vật (tên, bí danh, vai trò, mô tả), quan hệ, tình huống mở đầu; cảnh báo `warnings`; "Nhận nền truyện" gọi accept với bản đã sửa |
| `AddressRulesStep` | Sinh quy tắc (`stage=address_rules`) rồi sửa trong `AddressRulesTable`; chỉ báo cặp nhân vật chính có quan hệ mà chưa có quy tắc |
| `EventOutlineStep` | Sinh dàn ý (`stage=event_outline`, tiến độ theo quyển); sửa trong `EventOutlineTable` + `HookList`; biểu đồ mật độ sự kiện/chương (thanh ngang đơn giản) để thấy chỗ dồn/thưa |
| `FoundationJobPanel` | Hiển thị `parts_done/parts_total`, phần lỗi; nút "Tiếp tục" (resume), "Tạo lại phần này", "Hủy" |
| `CharacterDetail` | Tab Hồ sơ (sửa), Quan hệ (từ `StoryState.relationships` tại chương slider), Xuất hiện (danh sách chương có tên/bí danh qua `/search`, link mở chương), Lịch sử thay đổi (`/history`), Xưng hô (lọc `AddressRulesTable` theo nhân vật, cả chiều nói và nghe) |
| `HookList` | Cột: hook, trạng thái, mở ở ch., hạn `due_by_chapter`, ưu tiên; hook quá hạn đứng đầu, nhãn "⚠ quá hạn (hạn ch.14)"; lọc trạng thái |
| `EventOutlineTable` | Nhóm theo quyển; cột trạng thái `planned/done/moved/dropped` (icon + chữ), chương dự kiến, phụ thuộc (chip), khóa 🔒; sự kiện bị chặn bởi phụ thuộc chưa xong có chú thích |
| `TimelineGrid` | Cột chương ảo hóa ngang; hàng theo `storyline` (NULL → "Tuyến chính"); card = sự kiện; kéo card sang cột khác = PATCH `planned_chapter`; dòng trên cùng hiện `timeline.story_time_label` |
| `ChapterStateSlider` | Thanh trượt 0..chương committed mới nhất; đổi giá trị cập nhật `?chapter=` và tải `StoryState` (debounce 200 ms) |
| `AppliesNextChapterBanner` | Hiện khi `bible_dirty` và có job đang chạy: "Thay đổi sẽ áp dụng từ chương kế tiếp (Ch.{n+1})" |

## State và dữ liệu

- TanStack Query keys: `['works', id, 'foundation']`, `['works', id, 'bible', collection, params]` (collection ∈ `characters|address-rules|story-events|hooks|facts|timeline`), `['works', id, 'bible', 'summary']`, `['works', id, 'bible-revisions']`, `['works', id, 'state', chapter]`, `['works', id, 'characters', cid, 'history']`.
- Zustand: không cần; vị trí slider nằm trong URL.
- Form: react-hook-form + zod (`useFieldArray` cho nhân vật, bí danh, sự kiện); candidate foundation được sửa cục bộ rồi gửi một lần khi "Nhận". Sửa trong Story Bible lưu theo dòng (Lưu/Hủy từng dòng), gửi `expected_revision`.
- API dùng: `POST /v1/jobs` (foundation), `POST /v1/jobs/{id}/accept|resume|cancel`, `GET /v1/works/{id}/foundation`, `PUT /v1/works/{id}/foundation/{section}`, CRUD 6 nhóm, `/characters/{cid}/history`, `/bible/summary`, `/bible-revisions`, `GET /v1/works/{id}/state?chapter=N`, `GET /v1/works/{id}/search?q=` (F09).
- Event SSE dùng (`/v1/events`): `job.state`, `job.step` (lọc `type=foundation` cho `FoundationJobPanel`; job chương để quyết định hiện `AppliesNextChapterBanner`), `chapter.committed` → invalidate `summary`, `hooks` (thay đổi quá hạn), giới hạn slider.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton danh sách; slider khóa tới khi có `latest_committed_chapter` |
| Rỗng (chưa có nền truyện) | "Chưa có nền truyện" + nút "Sinh nền truyện" hoặc "Tự viết" (form trống) |
| Rỗng (mục) | Ví dụ hooks: "Chưa có hook nào" + "+ Thêm hook" |
| Đang sinh | Tiến độ theo phần ("Đang tạo nhân vật… 1/2"), nút Hủy; người dùng rời trang được, job vẫn chạy |
| Lỗi `VALIDATION` khi nhận | Đánh dấu đỏ đúng trường theo `detail.errors[].path`; chu trình sự kiện tô các dòng liên quan |
| Lỗi `PROVIDER_REFUSAL` (job) | "Model từ chối nội dung" + gợi ý chỉnh brief/đổi model (F04) + "Thử lại" |
| Lỗi `OUTPUT_TRUNCATED` / `STRUCTURED_OUTPUT_INVALID` | Phần lỗi được đánh dấu, nút "Tạo lại phần này" |
| Lỗi `VAULT_LOCKED` | Job `waiting_slot`: "Đang chờ mở vault" + nút mở vault |
| Lỗi `REVISION_CONFLICT` | Toast + tải lại dòng, giữ bản đang sửa để so sánh |
| Thành công | Toast "Đã nhận nền truyện"; dòng vừa sửa nhấp nháy nhẹ |

## Tương tác, phím tắt, khả năng tiếp cận

- Menu trái là `nav` có đếm số; mục hooks có chữ "2 quá hạn" (không chỉ màu/icon).
- Slider chương: phím ←/→ đổi 1 chương, PageUp/PageDown đổi 10, Home/End; `aria-valuetext="Sau chương 44"`.
- Timeline kéo thả dùng dnd-kit với KeyboardSensor; mỗi card có menu "Chuyển sang chương…" thay thế cho kéo.
- Bảng xưng hô: mỗi dòng đọc được thành câu cho trình đọc màn hình ("Lâm Phong xưng 'ta', gọi Mộc Lan là 'nàng', từ chương 1").
- Đồ thị quan hệ lazy-load; có danh sách thay thế dạng bảng cho người dùng bàn phím.
- Nút "Hỏi AI" (UI §5.4) không render trong MVP.

## Chuỗi giao diện (i18n)

Namespace `storyBible` và `foundation`, ví dụ khóa: `storyBible.nav.characters` ("Nhân vật"), `storyBible.nav.hooksCount` ("Hooks ({{open}} mở, {{overdue}} quá hạn)"), `storyBible.hooks.overdue` ("Quá hạn (hạn ch.{{due}})"), `storyBible.events.status.planned|done|moved|dropped` ("Dự kiến", "Đã xảy ra", "Đã dời", "Đã bỏ"), `storyBible.character.tabs.address` ("Xưng hô"), `storyBible.address.sentence`, `storyBible.appliesNextChapter` ("Thay đổi sẽ áp dụng từ chương kế tiếp (Ch.{{n}})"), `storyBible.stateSlider.label` ("Trạng thái sau chương {{n}}"), `foundation.generate` ("Sinh nền truyện"), `foundation.accept` ("Nhận nền truyện"), `foundation.regeneratePart` ("Tạo lại phần này"), `foundation.parts.frame_core|cast|address_rules|hooks` và `foundation.parts.events` ("Dàn ý quyển {{n}}"). MVP chỉ có `vi`.

## Việc cần làm

- [ ] 3 bước wizard + `FoundationJobPanel` (tiến độ, resume, tạo lại phần, hủy).
- [ ] `StoryBiblePage`, `BibleNav` (đếm từ `/bible/summary`), `ChapterStateSlider`.
- [ ] Nhân vật: danh sách ảo hóa, `CharacterDetail` 5 tab, `AliasEditor` (loại bí danh, cảnh báo trùng).
- [ ] `AddressRulesTable` dùng chung cho wizard và tab Xưng hô.
- [ ] `EventOutlineTable`, `HookList` (quá hạn), `FactList`, `TimelineGrid`, `LocationList` (chỉ đọc), `RelationshipGraph` (lazy).
- [ ] `AppliesNextChapterBanner` + đọc `bible-revisions`.
- [ ] Link builder `bibleAddressLink(workId, characterId)` export cho F11.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `FoundationStep`: sửa candidate → accept gửi bản đã sửa; lỗi 422 tô đúng trường | `fe/src/features/story_bible/wizard/FoundationStep.test.tsx` |
| component | `HookList`: quá hạn đứng đầu, nhãn chữ | `fe/src/features/story_bible/components/hooks/HookList.test.tsx` |
| component | `AddressRulesTable`: thêm quy tắc chồng khoảng → hiển thị lỗi `overlap_with` | `fe/src/features/story_bible/components/address/AddressRulesTable.test.tsx` |
| component | `ChapterStateSlider`: phím mũi tên đổi `?chapter=` | `fe/src/features/story_bible/components/ChapterStateSlider.test.tsx` |
| e2e (mock backend) | Wizard bước 3–5 với job mock: sinh, ngắt, tiếp tục, nhận, sang bước Cấu hình viết | `fe/tests/e2e/foundation-wizard.spec.ts` |
| e2e (mock backend) | Story Bible: sửa nhân vật khi có job chạy → banner "áp từ chương kế tiếp"; kéo sự kiện trên timeline | `fe/tests/e2e/story-bible.spec.ts` |

Luồng: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md).

## Tên mới đề xuất

- Giá trị `$section`: `foundation`, `characters`, `locations`, `facts`, `hooks`, `events`, `timeline`, `graph`; search params `?character=&tab=profile|relations|appearances|history|address&chapter=`.
- Component/hook: `StoryBiblePage`, `BibleNav`, `ChapterStateSlider`, `AppliesNextChapterBanner`, `FoundationView`, `FoundationJobPanel`, `CharacterList`, `CharacterDetail`, `AliasEditor`, `AddressRulesTable`, `EventOutlineTable`, `HookList`, `FactList`, `TimelineGrid`, `RelationshipGraph`, `LocationList`, `FoundationStep`, `AddressRulesStep`, `EventOutlineStep`, `useFoundation`, `useBibleCollection`, `useStoryState`, `useBibleRevisionStatus`, `bibleAddressLink`.
- i18n namespace `storyBible`, `foundation`.
