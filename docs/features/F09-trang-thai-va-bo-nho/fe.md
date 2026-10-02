# F09 — Frontend

F09 cung cấp hook dữ liệu và component cho bộ nhớ truyện; màn hình Story Bible đầy đủ thuộc F06 nhưng dùng các hook ở đây.

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/works/$workId?tab=memory&chapter=N` | Workspace → panel phải → tab **Nhớ** | Facts/hooks liên quan chương đang mở, thay đổi trong chương, ô tìm kiếm (UI §5.2) |
| `/works/$workId/bible/$section?chapter=N` | Story Bible (F06) với **thanh trượt chương** | Xem `StoryState` sau chương bất kỳ (UI §5.4, §5.8; Plan §23.4 #11) |
| `/works/$workId?tab=ai` | Tab AI → card candidate "Đã dùng ngữ cảnh: …" | Mở `ContextTraceViewer` (UI §5.2, §2 Sudowrite "Looked at") |
| `/works/$workId/search?q=` | Kết quả tìm trong truyện (toàn trang) | Mở từ ô tìm ở tab Nhớ hoặc Ctrl+K → "Tìm trong truyện" |

## Component

```text
fe/src/features/story_bible/hooks/
  useStoryState.ts          (workId, chapterNo?) → StoryState + meta
  useStateChanges.ts        (workId, from, to, entity?) → danh sách thay đổi
  useApplyStateDelta.ts     mutation /state/deltas (expected_state_hash)
fe/src/features/story_bible/components/
  ChapterStateSlider.tsx    Thanh trượt chương 0..N, ghi nhãn chương committed / stale
  StateEntityCard.tsx       Hiển thị một nhân vật/hook/fact tại chương đã chọn + nguồn bằng chứng
fe/src/features/memory/
  components/MemoryTab.tsx
  components/FactList.tsx, HookDueList.tsx, ChapterChanges.tsx
  components/WorkSearchBox.tsx, SearchResults.tsx, SearchResultItem.tsx
  hooks/useChapterMemory.ts, useWorkSearch.ts
  pages/WorkSearchPage.tsx
fe/src/features/ai_workspace/components/
  ContextTraceSummary.tsx   Dòng "Đã dùng ngữ cảnh: handoff ch.11, đuôi ch.11, 5 tóm tắt, 7 dữ kiện…"
  ContextTraceViewer.tsx    Dialog chi tiết theo lớp
  TokenBudgetBar.tsx        Thanh ngân sách: bảo vệ | nén được | trống | dự trữ output
fe/src/features/ai_workspace/hooks/useContextTrace.ts
```

| Component | Trách nhiệm |
|---|---|
| `ChapterStateSlider` | Kéo chọn chương; debounce 200 ms rồi đổi `chapter` trong search params; prefetch chương kề bên; đánh dấu ⚠ chương thuộc `stale_from(K)`; chương 0 ghi "Nền truyện (seed)" |
| `StateEntityCard` | Trường trạng thái tại chương chọn (vd. Lâm Phong: còn sống, ở Bến đò, bị thương vai trái, biết dữ kiện #12); mỗi trường có link bằng chứng → mở chương ở `paragraph_id` |
| `MemoryTab` | Ba khối: "Dữ kiện đang hiệu lực" (lọc theo nhân vật có mặt), "Hook đến hạn / đang mở" (`due_by_chapter`, ⚠ quá hạn), "Thay đổi trong chương này" (op của delta đã commit); ô tìm kiếm ở đầu |
| `FactList`, `HookDueList` | Danh sách ảo hóa; nút "Sửa" mở form F06 (đi qua `/state/deltas`); hook quá hạn hiện icon + chữ "Quá hạn ch.14" |
| `WorkSearchBox` / `SearchResults` | Gõ có hoặc không dấu; lọc theo loại (chương, dữ kiện, hook, tóm tắt, nhân vật) và khoảng chương; kết quả hiển thị snippet có dấu với tô sáng, nhãn "Ch.7 · đoạn 12"; bấm → mở editor tại `paragraph_id` |
| `ContextTraceViewer` | Nhóm theo lớp 1–4; mỗi mục: loại nguồn, tên/chương, token, 🔒 bảo vệ hoặc nén được, preview; mục bị loại hiển thị riêng kèm lý do (`over_budget`, `low_rank`, `duplicate`); đầu dialog: model, effort, `prompt_version`, ngân sách, token ước lượng vs thực nhận, cache đọc/ghi, cách đếm (`exact`/`estimate`); chọn bước (plan/write/settle/…, vòng sửa) |
| `TokenBudgetBar` | Thanh chồng 4 phần, có `aria-label` đọc số liệu; không chỉ dùng màu |

## State và dữ liệu

- TanStack Query keys:
  - `['works', workId, 'state', chapterNo]` (`staleTime` dài; snapshot chương cũ bất biến trừ khi resync)
  - `['works', workId, 'state-changes', {from, to, entity}]`
  - `['chapters', chapterId, 'memory']`
  - `['works', workId, 'search', {q, kinds, from, to}]` (infinite query theo `cursor`)
  - `['chapters', chapterId, 'trace', {jobId, step}]`
  - `['works', workId, 'summaries', {level}]`
- Zustand: không lưu state truyện; chỉ lưu tùy chọn UI (bộ lọc loại kết quả tìm kiếm gần nhất trong phiên).
- API dùng: `/v1/works/{id}/state`, `/state/changes`, `/state/deltas`, `/v1/chapters/{id}/memory`, `/v1/works/{id}/search`, `/v1/chapters/{id}/trace`, `/v1/works/{id}/summaries` (xem [be.md](./be.md#api)).
- Event SSE: `chapter.committed` → invalidate `state` (chương mới), `memory`, `search`, `trace` của chương đó; `work.continuity` → làm mới nhãn stale trên thanh trượt; `job.step` với `step=summarize_hierarchy` → invalidate `summaries`.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton danh sách; thanh trượt giữ vị trí cũ, mờ nội dung tới khi có dữ liệu |
| Rỗng | Tab Nhớ chương 1: "Chưa có dữ kiện. Dữ kiện xuất hiện sau khi chương được lưu."; tìm kiếm không có kết quả: gợi ý thử bỏ dấu hoặc mở rộng khoảng chương |
| Lỗi (`code`) | `REVISION_CONFLICT` khi sửa state → "State vừa đổi (có thể do chương mới được lưu)" + tải lại; `VALIDATION` → liệt kê vi phạm (vd. "Nhân vật đã chết không thể di chuyển"); `WORK_BLOCKED` → "Đang viết chương N, thay đổi sẽ áp từ chương kế tiếp" (khi API trả `202` pending) |
| Thành công | Toast "Đã lưu thay đổi state"; với pending: "Sẽ áp trước khi viết chương N+1" |

## Tương tác, phím tắt, khả năng tiếp cận

- Thanh trượt: phím ←/→ lùi/tiến một chương, Home/End về 0/mới nhất; `aria-valuetext="Sau chương 44"`.
- Ctrl+K → mục "Tìm trong truyện: <q>"; Enter mở trang kết quả.
- Kết quả tìm kiếm điều hướng bằng ↑/↓, Enter mở đoạn.
- Mọi nhãn trạng thái dùng icon + chữ (UI §8).
- `ContextTraceViewer` là dialog Base UI: bẫy focus, Esc đóng.

## Chuỗi giao diện (i18n)

Namespace `memory`, `bible`, `ai`. Ví dụ khóa:

- `memory:tab.title` ("Nhớ"), `memory:facts.active`, `memory:hooks.due` ("Hook đến hạn"), `memory:hooks.overdue` ("Quá hạn ch.{{chapter}}"), `memory:changes.title` ("Thay đổi trong chương này").
- `memory:search.placeholder` ("Tìm trong truyện (gõ có hoặc không dấu)"), `memory:search.result.location` ("Ch.{{chapter}} · đoạn {{index}}").
- `bible:slider.label` ("Trạng thái sau chương"), `bible:slider.seed` ("Nền truyện"), `bible:slider.stale` ("Cần đồng bộ lại").
- `ai:trace.summary` ("Đã dùng ngữ cảnh: {{items}}"), `ai:trace.layer.1`…`ai:trace.layer.4`, `ai:trace.protected` ("Bảo vệ – không nén"), `ai:trace.dropped.over_budget` ("Bỏ do vượt ngân sách"), `ai:trace.count.estimate` ("Ước lượng (±15%)").

## Việc cần làm

- [ ] Hook `useStoryState`, `useStateChanges`, `useApplyStateDelta` (dùng type sinh từ OpenAPI).
- [ ] `ChapterStateSlider` + `StateEntityCard` (F06 lắp vào trang Story Bible).
- [ ] Feature `memory`: `MemoryTab`, danh sách, tìm kiếm, trang kết quả.
- [ ] `ContextTraceSummary`, `ContextTraceViewer`, `TokenBudgetBar` trong `ai_workspace`.
- [ ] Nối event bus SSE (F01/F12) để invalidate đúng query.
- [ ] Điều hướng tới `paragraph_id` (API của editor F07).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | Thanh trượt đổi chương → gọi đúng query key, prefetch kề bên, nhãn stale | `fe/src/features/story_bible/components/ChapterStateSlider.test.tsx` |
| component | `MemoryTab` hiển thị hook quá hạn bằng icon + chữ | `fe/src/features/memory/components/MemoryTab.test.tsx` |
| component | `SearchResultItem` tô sáng đúng vị trí trên văn bản có dấu | `fe/src/features/memory/components/SearchResultItem.test.tsx` |
| component | `ContextTraceViewer` nhóm theo lớp, tách mục bị loại, hiện cách đếm | `fe/src/features/ai_workspace/components/ContextTraceViewer.test.tsx` |
| e2e (mock backend) | Viết chương mock → `chapter.committed` → tab Nhớ cập nhật; tìm `lam phong` ra "Lâm Phong" | `fe/tests/e2e/memory-and-search.spec.ts` |
| e2e (mock backend) | Sửa fact khi đang viết → thông báo pending → sau commit thấy fact đã áp | `fe/tests/e2e/state-pending-edit.spec.ts` |

Luồng: [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md), [T05](../../tests/flows/T05-viet-mot-chuong.md).

## Tên mới đề xuất

- Thư mục `fe/src/features/memory/` (Arch §4 chưa có; tab Nhớ cần nơi riêng, không đặt trong `story_bible`).
- Route `/works/$workId/search`; tham số `tab=memory` đã có trong UI §4.
- Component `ChapterStateSlider`, `StateEntityCard`, `MemoryTab`, `WorkSearchBox`, `SearchResults`, `ContextTraceSummary`, `ContextTraceViewer`, `TokenBudgetBar`; hook `useStoryState`, `useStateChanges`, `useApplyStateDelta`, `useChapterMemory`, `useWorkSearch`, `useContextTrace`.
- Namespace i18n `memory`.
