# F07 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/works/$workId?mode=write&chapter=12` | Workspace, cột giữa là editor (UI §5.2) | Mỗi chương một document Tiptap riêng (UI §6 #8) |
| `/works/$workId/history/$chapterNo` | Lịch sử phiên bản | Dùng chung component diff với Review (UI §5.5) |
| (trạng thái) Chế độ tập trung | Ẩn hai panel, chỉ editor + font đọc | Ctrl+Shift+F (Plan §23.4 #8) |

## Component

```text
fe/src/features/editor/
  components/ChapterEditor.tsx        Khởi tạo Tiptap, cô lập render
  components/EditorToolbar.tsx        useEditorState(selector): B, I, H1, H2, trích dẫn, ngắt cảnh
  components/EditorBubbleMenu.tsx
  components/ReadOnlyBaseBanner.tsx   "Chương này đang làm nền cho Ch.N" + [Tạm dừng để sửa]
  components/ConflictBanner.tsx       409: [So sánh] [Giữ bản của tôi] [Lấy bản mới]
  components/SaveStatus.tsx           "Lưu ✓ 2 giây trước" / "Đang lưu…" / "Chưa lưu được – thử lại"
  components/ChapterTree.tsx          react-arborist: tạo, đổi tên, xóa, kéo sắp xếp (ảo hóa)
  extensions/index.ts                 Danh sách extension + cấu hình
  extensions/paragraphId.ts           UniqueID cấu hình paragraph_id
  extensions/pasteNormalize.ts        NFC + làm sạch khi paste
  extensions/syllableCounter.ts       Hàm đếm âm tiết cho CharacterCount
  hooks/useAutosave.ts
  hooks/useEditLock.ts
  hooks/useFocusMode.ts
  model/editorUiStore.ts              Zustand: focusMode, saveState theo chapterId
  model/serialize.ts                  getJSON() → bản NFC để gửi (không sửa state editor)
  pages/EditorPage.tsx
fe/src/features/review/
  pages/RevisionHistoryPage.tsx
  components/RevisionList.tsx         Ảo hóa; nhãn nguồn: người, AI, sửa theo yêu cầu, khôi phục, nhập
  components/RevisionDiffView.tsx     Song song | Inline; Mức: Từ | Câu; +x / −y âm tiết
  components/RestoreDialog.tsx
  workers/diff.worker.ts              jsdiff + Intl.Segmenter('vi')
  hooks/useDiffWorker.ts
```

**Cấu hình Tiptap v3** (UI §3; pin `prosemirror-view` ≥ 1.41.9 bằng `pnpm.overrides`):

| Extension | Cấu hình |
|---|---|
| `@tiptap/react` | `useEditor({ shouldRerenderOnTransaction: false })` (UI §6 #4) |
| `starter-kit` | Bật: Document, Paragraph, Text, Heading (`levels: [1, 2]`), Bold, Italic, Blockquote, HardBreak, HorizontalRule (ngắt cảnh), Dropcursor, Gapcursor. Tắt: code, codeBlock, lists, link, strike, underline (không dùng cho văn xuôi MVP). Nếu bản StarterKit đã chứa UndoRedo/TrailingNode thì không thêm lần hai – xác minh khi pin |
| `@tiptap/extensions` | `UndoRedo` (`depth: 200`, `newGroupDelay: 500`), `CharacterCount` (hàm đếm âm tiết – xác minh tên option), `Placeholder` ("Bắt đầu viết…"), `Focus` (`mode: 'deepest'`, dùng cho chế độ tập trung), `TrailingNode` |
| `extension-bubble-menu` | B, I, H1, H2, trích dẫn |
| `extension-drag-handle-react` | Kéo đoạn `⋮⋮` (UI §5.2); kéo giữ nguyên `paragraph_id` |
| `extension-unique-id` | `types: ['paragraph','heading','horizontalRule']`, `attributeName: 'id'`, `generateID: newParagraphId` (8 ký tự `[a-z0-9]`, trùng với BE) |
| `extension-invisible-characters` | Tắt mặc định; bật bằng nút "Hiện ký tự ẩn" để soát khoảng trắng/ký tự lạ |

Không dùng Tracked Changes/AI Toolkit (trả phí). Hành vi ID cần kiểm ở R0: Enter tách đoạn → đoạn mới có ID mới, đoạn cũ giữ ID; Backspace gộp → giữ ID đoạn trên; paste nội dung có ID trùng → UniqueID sinh lại.

| Component | Trách nhiệm |
|---|---|
| `ChapterEditor` | Tạo editor một lần cho mỗi `chapterId`; nạp `doc` (working copy nếu base = revision hiện tại, ngược lại revision hiện tại + `ConflictBanner`); `editable` theo `useEditLock`; không bao giờ `setContent` sau khi lưu |
| `useAutosave` | Xem thuật toán dưới |
| `useEditLock` | Đọc `edit_lock` của chương + nghe `job.state`; chuyển `editor.setEditable(false/true)` |
| `ReadOnlyBaseBanner` | Gọi `POST /v1/works/{id}/autowrite/pause` `{reason:"edit_base", chapter_id}`; trạng thái "Đang dừng sau bước hiện tại…" tới khi lock mất |
| `RevisionDiffView` | Nhận `DiffOut` (theo đoạn) → gửi cặp `changed` vào Worker → render `<ins>/<del>`; đoạn `added/removed` render cả khối; nút "Khôi phục bản này" |
| `ChapterTree` | Danh sách chương ảo hóa, trạng thái (✓ committed, ● đang viết, ⏳ hàng đợi), thêm/xóa/kéo sắp xếp; hiển thị lỗi `WORK_BUSY_QUEUED` khi truyện đang chạy |

## State và dữ liệu

- TanStack Query keys: `['works', workId, 'chapters']`, `['chapters', id]`, `['chapters', id, 'working-copy']`, `['chapters', id, 'revisions']`, `['chapters', id, 'revisions', rev]`, `['chapters', id, 'diff', a, b]`.
- Zustand `editorUiStore`: `focusMode`, `saveState[chapterId] = {status, savedAt, error}`; buffer chưa lưu nằm trong state Tiptap, **không** lưu localStorage (Plan §3.1).
- API dùng: chapters CRUD/reorder, `GET/PUT /v1/chapters/{id}`, `GET/PUT …/working-copy`, `POST …/snapshot`, `GET …/revisions[/{rev}]`, `GET …/revisions/{a}/diff/{b}`, `POST …/revisions/{rev}/restore`, `POST /v1/works/{id}/autowrite/pause` (F12).
- Event SSE dùng (`/v1/events`): `job.state` (bật/tắt khóa nền), `chapter.committed` (chương đang mở có revision mới → nếu không có thay đổi cục bộ thì nạp lại, nếu có thì `ConflictBanner`), `work.continuity` (banner liền mạch thuộc workspace).

**Thuật toán autosave** (Plan §4.4, §23.2 #2):

1. `onUpdate` có `docChanged` → `dirty=true`, đặt debounce 750 ms (trong khoảng 500–1.000 ms).
2. Khi hết debounce mà `view.composing` = true (đang gõ IME) → chờ `compositionend`, tối đa thêm 1.000 ms.
3. Mỗi lúc chỉ một request; thay đổi mới trong lúc gửi → gửi tiếp sau khi request trước xong (gộp). Mỗi request tăng `client_seq`.
4. Thành công → `savedAt`; lỗi mạng/5xx → thử lại 1, 2, 4, 8… tối đa 30 s, `SaveStatus` báo "Chưa lưu được"; 409 → dừng autosave, `ConflictBanner`; 423 → editor chỉ đọc, giữ buffer, hộp thoại "[Tạm dừng để sửa] [Sao chép thay đổi của tôi]".
5. Nhàn 2 phút kể từ lần sửa cuối và đã có thay đổi so với revision → `snapshot(reason=idle)`.
6. Đổi chương (Alt+↑/↓, chọn cây), rời route, đóng cửa sổ (sự kiện đóng của Tauri – F00) → flush ngay + `snapshot(leave_chapter)`; lỗi → hộp thoại "Chưa lưu được. Ở lại / Rời đi (mất thay đổi)".
7. Ctrl+S → flush + `snapshot(manual_snapshot)` → toast "Đã tạo bản v{n}".

**Diff Worker:** input `{jobId, pairs: [{paragraph_id, a, b}], level: 'word'|'sentence'}`; mức từ dùng `diffWordsWithSpace(a, b, {intlSegmenter: new Intl.Segmenter('vi', {granularity: 'word'})})`, mức câu dùng `diffSentences`; trả kết quả theo lô 50 đoạn để render dần; yêu cầu mới hủy `jobId` cũ. Thống kê "+x / −y âm tiết": đếm token theo khoảng trắng trong phần thêm/xóa, bỏ token chỉ gồm dấu câu. Nếu `Intl.Segmenter` không có → fallback `diffWordsWithSpace` không segmenter.

**Paste** (`pasteNormalize.ts`, Plan §6.6): `transformPastedText` và `transformPastedHTML` → `normalize('NFC')`, bỏ U+200B/U+FEFF, chuyển CRLF → LF; HTML từ Word/web chỉ giữ đoạn, heading 1–2, bold, italic, trích dẫn; dòng trống tách đoạn. `serialize.ts` chuẩn hóa NFC bản sao JSON trước khi gửi (không sửa state editor để không phá composition).

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton văn bản trong cột giữa; mục tiêu mở chương ~300 ms (Plan §4.4, chưa đo) |
| Rỗng | Chương mới: placeholder "Bắt đầu viết…"; lịch sử chỉ 1 bản: "Chưa có bản cũ để so sánh" |
| Lỗi `REVISION_CONFLICT` | `ConflictBanner`: "Chương vừa có bản mới (v{n}, AI/người khác). Thay đổi của bạn chưa được lưu." [So sánh] [Giữ bản của tôi = tạo bản mới trên nền v{n}] [Lấy bản mới] |
| Lỗi `CHAPTER_READ_ONLY` | `ReadOnlyBaseBanner` + editor chỉ đọc, con trỏ vẫn chọn/copy được |
| Lỗi mạng/backend dừng | `SaveStatus` đỏ "Chưa lưu được – đang thử lại"; không mất buffer |
| Thành công | `SaveStatus` "Lưu ✓ {thời gian} trước"; status bar "Bản v{n} ({nguồn})" (UI §5.2) |

## Tương tác, phím tắt, khả năng tiếp cận

- Ctrl+S tạo snapshot; Alt+↑/↓ chương trước/sau (flush trước khi đổi); Ctrl+Shift+F chế độ tập trung; Ctrl+B / Ctrl+Alt+B thu gọn panel (UI §8); Ctrl+Z/Ctrl+Shift+Z hoàn tác/làm lại.
- Chế độ tập trung: thu gọn hai panel (react-resizable-panels `collapse()`), font Noto Serif, `Focus` làm mờ đoạn khác; Esc thoát; trạng thái không lưu bền.
- Editor có `aria-label="Nội dung chương {n}"`; khi chỉ đọc đặt `aria-readonly="true"` và banner có `role="status"`.
- Diff: `<ins>`/`<del>` kèm gạch chân/gạch ngang và màu, không chỉ màu.
- Cây chương điều hướng bằng bàn phím (react-arborist), F2 đổi tên, Delete xóa có xác nhận.

## Chuỗi giao diện (i18n)

Namespace `editor` và `history`, ví dụ khóa: `editor.placeholder` ("Bắt đầu viết…"), `editor.save.saved` ("Lưu ✓ {{ago}} trước"), `editor.save.saving` ("Đang lưu…"), `editor.save.failed` ("Chưa lưu được – đang thử lại"), `editor.readOnlyBase` ("Chương này đang làm nền cho Ch.{{n}} đang viết"), `editor.pauseToEdit` ("Tạm dừng để sửa"), `editor.conflict.title`, `editor.focusMode` ("Chế độ tập trung"), `editor.syllables` ("{{count}} âm tiết"), `history.source.manual` ("người"), `history.source.agent` ("AI"), `history.source.revise` ("sửa theo yêu cầu"), `history.source.restore` ("khôi phục"), `history.restore.confirm` ("Tạo bản v{{next}} từ v{{rev}}? Bản hiện tại vẫn nằm trong lịch sử."). MVP chỉ có `vi`.

## Checklist IME tiếng Việt (thủ công, R0; Plan §9 Giai đoạn 0, Review §7.5)

Chạy trên Windows 11 WebView2 (Unikey Telex/VNI, Unikey bật/tắt "sửa lỗi gợi ý"/tương đương, EVKey Telex) và macOS WKWebView bản thấp nhất hỗ trợ (bộ gõ Telex và VNI có sẵn). Ghi kết quả vào [T12](../../tests/flows/T12-editor-autosave-ime.md).

- [ ] IME-01 Gõ câu dài có đủ dấu (`Người ấy đã đứng đợi ở bến đò suốt đêm mưa.`) – không mất/nhân đôi ký tự.
- [ ] IME-02 Gõ đè dấu (`tieengs` → `tiếng`, `dduowngf` → `đường`), sửa dấu sau khi gõ xong từ.
- [ ] IME-03 Backspace trong lúc đang ghép từ và ngay sau khi ghép.
- [ ] IME-04 Gõ trong đoạn in đậm/nghiêng; ngay đầu và cuối mark (ranh giới bold).
- [ ] IME-05 Gõ ở đầu/cuối đoạn, đoạn rỗng, ngay sau Enter tách đoạn; `paragraph_id` đoạn cũ không đổi.
- [ ] IME-06 Gõ khi autosave đang gửi request; khi có event SSE đến; khi panel AI đang stream candidate.
- [ ] IME-07 Undo/Redo sau khi gõ một câu có dấu: hoàn tác theo từ/cụm, không để lại ký tự Telex thô.
- [ ] IME-08 Chọn một đoạn văn rồi gõ đè bằng IME.
- [ ] IME-09 Gõ nhanh liên tục 2 phút; so sánh văn bản thu được với bản gõ mẫu.
- [ ] IME-10 Paste từ Word/web/PDF (có ký tự NFD, U+200B) rồi gõ tiếp; kiểm tra lưu NFC.
- [ ] IME-11 Gõ trong heading và blockquote; trong đoạn đang hiển thị drag handle.
- [ ] IME-12 Chuyển chương bằng Alt+↓ ngay giữa lúc đang ghép từ → không mất ký tự cuối.

## Việc cần làm

- [ ] Spike R0: editor tối thiểu + checklist IME trên cả hai webview; pin `prosemirror-view` ≥ 1.41.9. Editor, paragraph ID split/merge tests, paste NFC và syllable count parity có; manual IME chưa chạy.
- [x] Tiptap v3 setup, `paragraph_id` split/merge automated test, paste normalization, Vietnamese syllable/character count and parity tests are implemented.
- [x] Manual IME checklist and bold/italic test controls are ready at `/editor-spike`.
- [ ] Run and record the manual IME matrix on Windows WebView2 and macOS WKWebView; no manual result is claimed yet.
- [ ] `extensions/` đầy đủ + `paragraphId`, `pasteNormalize`, `syllableCounter`.
- [ ] `useAutosave` theo thuật toán trên; `SaveStatus`; flush khi đổi chương/đóng cửa sổ.
- [ ] `useEditLock`, `ReadOnlyBaseBanner`, `ConflictBanner`.
- [ ] Lịch sử phiên bản, `RevisionDiffView`, `diff.worker.ts`, `RestoreDialog`.
- [ ] `ChapterTree` cơ bản; chế độ tập trung.
- [ ] Đo: độ trễ gõ phím khi 5 luồng stream mock (UI §10), thời gian mở chương.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `useAutosave`: debounce, gộp request, chờ composition, 409/423/lỗi mạng | `fe/src/features/editor/hooks/useAutosave.test.ts` |
| component | `pasteNormalize`: NFD → NFC, bỏ U+200B, giữ bold/italic | `fe/src/features/editor/extensions/pasteNormalize.test.ts` |
| component | `paragraphId`: tách/gộp/paste giữ ID duy nhất | `fe/src/features/editor/extensions/paragraphId.test.ts` |
| component | `ChapterEditor` chỉ đọc khi có `edit_lock`; mở khóa khi `job.state` kết thúc | `fe/src/features/editor/components/ChapterEditor.test.tsx` |
| unit | Diff worker: tiếng Việt có dấu, đếm âm tiết thêm/xóa, fallback không segmenter | `fe/src/features/review/workers/diff.worker.test.ts` |
| e2e (mock backend) | Gõ → autosave → Ctrl+S → lịch sử có bản mới → diff → restore | `fe/tests/e2e/editor-history.spec.ts` |
| e2e (mock backend) | Event `chapter.committed` khi đang sửa → banner xung đột | `fe/tests/e2e/editor-conflict.spec.ts` |
| thủ công | Checklist IME-01…IME-12 trên Windows/macOS | [T12](../../tests/flows/T12-editor-autosave-ime.md) |

## Tên mới đề xuất

- Component/hook/file: `ChapterEditor`, `EditorToolbar`, `EditorBubbleMenu`, `ReadOnlyBaseBanner`, `ConflictBanner`, `SaveStatus`, `ChapterTree`, `RevisionHistoryPage`, `RevisionList`, `RevisionDiffView`, `RestoreDialog`, `useAutosave`, `useEditLock`, `useFocusMode`, `useDiffWorker`, `editorUiStore`, `extensions/paragraphId.ts`, `extensions/pasteNormalize.ts`, `extensions/syllableCounter.ts`, `model/serialize.ts`, `workers/diff.worker.ts`, hàm `newParagraphId`.
- ID checklist `IME-01`…`IME-12`.
- i18n namespace `editor`, `history`.
