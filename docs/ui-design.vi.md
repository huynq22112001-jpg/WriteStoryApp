# Thiết kế giao diện và thư viện React cho WriteStoryApp

Ngày: 02/10/2026. Trạng thái: thiết kế đề xuất, chưa dựng UI. Phiên bản thư viện lấy từ npm registry ngày 02/10/2026; pin chính xác khi dựng skeleton ở R0.

Liên quan: [implementation-plan.vi.md](./implementation-plan.vi.md) (§4.2 đa truyện, §6.2 pipeline chương), [folder-architecture.vi.md](./folder-architecture.vi.md) (§4 FE), [review-and-optimization.vi.md](./review-and-optimization.vi.md).

---

## 1. Nguyên tắc

1. **Hai trục chính của sản phẩm phải nhìn thấy được:**
   - nhiều truyện đang chạy cùng lúc → màn **Phòng viết**;
   - mạch truyện liền giữa các chương → **trạng thái liền mạch**, **bản giao nối** và **mối nối** hiển thị ngay trong workspace.
2. **Bố cục 3 cột quen thuộc** của app viết: cây chương | editor | panel AI/ngữ cảnh (theo Scrivener, Sudowrite).
3. **AI không ghi thẳng vào editor.** Candidate stream vào pane riêng, xem diff, rồi mới chấp nhận (theo panel Review của Cursor).
4. **Không chặn người viết.** Khi các truyện khác đang chạy, người dùng vẫn đọc và sửa bất kỳ truyện nào.
5. **Đa ngôn ngữ về kiến trúc, tiếng Việt làm trước**: mọi chuỗi qua i18n (`t()`), MVP chỉ có bản tiếng Việt; font có subset tiếng Việt đóng gói offline; nhãn, lỗi và `aria-label` tiếng Việt. Ô chọn ngôn ngữ giao diện và ngôn ngữ tác phẩm có trong Cài đặt/Wizard nhưng MVP chỉ có một lựa chọn "Tiếng Việt".

## 2. Tham khảo bố cục các app tương tự

| App | Bố cục | Áp dụng cho WriteStoryApp |
|---|---|---|
| Sudowrite | Trái: documents + Story Bible; giữa: editor; phải: Chat/History, kết quả AI dạng card có "Looked at:" ([docs](https://docs.sudowrite.com/getting-started/dQph1snuwbfMWG9wRjsNug/interface/ubBg2ZEoAwasV98E3ZBwjn)) | Card candidate ghi rõ AI đã dùng ngữ cảnh nào (context trace) |
| NovelCrafter | Thanh mode Plan / Write / Chat / Review; sidebar công cụ ghim được; chat chọn ngữ cảnh và "Extract" về Codex ([docs](https://www.novelcrafter.com/docs/the-interface/)) | Thanh mode trong workspace; trích xuất từ chat vào Story Bible |
| Scrivener | Binder (cây) \| Editor (chia đôi, Corkboard/Outline) \| Inspector ([manual](https://www.literatureandlatte.com/docs/Scrivener_Manual-Win.pdf)) | Cây chương trái, inspector phải |
| Obsidian | Ribbon dọc, 2 sidebar thu gọn độc lập, command palette ([docs](https://obsidian.md/help/workspace)) | Ribbon điều hướng, Ctrl+K |
| Cursor | Agent ở panel phải, Review diff inline, Accept/Reject từng phần ([changelog](https://cursor.com/changelog/2-4)) | Review/Diff candidate AI |
| Plottr | Timeline lưới: cột = chương, hàng = tuyến truyện, scene card kéo thả ([docs](https://docs.plottr.com/article/54-timeline-overview)) | Timeline trong Story Bible |
| InkOS Studio | Sidebar trái cố định; trang sách lấy chat làm trung tâm + panel phải chia section; textarea; Daemon chỉ có Start/Stop + log | Xem mục 7 |

## 3. Thư viện đề xuất

| Mục đích | Thư viện | Phiên bản kiểm tra | License | Ghi chú |
|---|---|---|---|---|
| Bộ UI | [shadcn/ui](https://ui.shadcn.com) (CLI 4.21.1) trên **[Base UI](https://base-ui.com)** `@base-ui/react` 1.8.0 | 10/2026 | MIT | Base UI là mặc định của shadcn từ 07/2026, Radix vẫn được hỗ trợ ([changelog](https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default)). InkOS Studio cũng dùng Base UI |
| Styling | Tailwind CSS v4 | — | MIT | Đã chọn |
| Icon | Lucide | — | ISC | Đã chọn |
| Panel kéo giãn/thu gọn | **[react-resizable-panels](https://github.com/bvaughn/react-resizable-panels)** 4.14.1 (shadcn Resizable) | 09/2026 | MIT | API v4 Group/Panel/Separator, `collapsible`, lưu layout qua `defaultLayout` + `onLayoutChanged`. Không chọn dockview (phức tạp, license cần kiểm tra), allotment (ít cập nhật), FlexLayout (0.x) |
| Sidebar | shadcn Sidebar | — | MIT | `collapsible="icon"`, Ctrl+B, dùng được nhiều sidebar |
| Editor | **[Tiptap](https://tiptap.dev/docs) v3** 3.31.4: `@tiptap/react`, `starter-kit`, `@tiptap/extensions` (CharacterCount, Placeholder, Focus, TrailingNode, UndoRedo), `extension-bubble-menu`, `extension-drag-handle-react`, `extension-unique-id`, `extension-invisible-characters` | 09/2026 | MIT | Các extension này được mở mã từ 3.0.1 ([blog](https://tiptap.dev/blog/release-notes/were-open-sourcing-more-of-tiptap)). **Không dùng** Tracked Changes/AI Toolkit (trả phí, Tracked Changes còn Alpha). Pin `prosemirror-view` ≥ 1.41.9 |
| Diff văn xuôi | **[jsdiff](https://github.com/kpdecker/jsdiff)** `diff` 9.0.0 | 04/2026 | BSD-3 | `diffWordsWithSpace` / `diffWords` với `intlSegmenter: new Intl.Segmenter('vi', {granularity:'word'})`, `diffSentences`. Tự render `<ins>/<del>`, chạy trong Web Worker |
| Diff 2 cột (tùy chọn) | [react-diff-viewer-continued](https://github.com/Aeolun/react-diff-viewer-continued) 4.4.0 | 07/2026 | MIT | Có chế độ WORDS/SENTENCES, ảo hóa; kéo theo Emotion → chỉ dùng nếu tự render tốn công |
| Ảo hóa danh sách | **[@tanstack/react-virtual](https://tanstack.com/virtual)** 3.14.13 | 09/2026 | MIT | Danh sách hàng nghìn chương, thư viện |
| Log/feed tự cuộn | [react-virtuoso](https://virtuoso.dev) 4.18.16 | 09/2026 | MIT | Log sự kiện ở Phòng viết |
| Cây chương/outline | **[react-arborist](https://github.com/brimdata/react-arborist)** 3.16.0 | 07/2026 | MIT | Có sẵn kéo thả, ảo hóa, đổi tên. Cần thử React 19 Strict Mode ở R0 |
| Kéo thả khác | [@dnd-kit/core](https://dndkit.com) 6.3.1 + sortable 10.0.0 | 12/2024 | MIT | Sắp xếp hàng đợi, card timeline. Bản ổn định; `@dnd-kit/react` mới còn 0.x |
| Router | **[TanStack Router](https://tanstack.com/router)** 1.170.41 | 09/2026 | MIT | `createHashHistory()` hợp với Tauri; search params có type (`?chapter=12&tab=review`) |
| Server state | TanStack Query 5.104.0 | — | MIT | Đã chọn |
| UI state | Zustand 5.0.15 | — | MIT | Đã chọn; store stream theo `workId`, selector hẹp |
| Form | react-hook-form 7.89.0 + @hookform/resolvers 5.9.1 + zod 4.6.5 | — | MIT | Provider, nhân vật, cài đặt; thông báo lỗi tiếng Việt |
| Toast | sonner 2.0.8 | 08/2026 | MIT | Thông báo commit chương, lỗi provider |
| Command palette | cmdk 1.1.1 (shadcn Command) | 03/2025 | MIT | Ổn định, ít release |
| Biểu đồ | Recharts 3.10.1 (shadcn Chart) | — | MIT | Chi phí, token, cache hit |
| Đồ thị quan hệ | [@xyflow/react](https://reactflow.dev) 12.12.0 | 09/2026 | MIT | Quan hệ nhân vật, hook. Lazy-load. Không dùng vis-timeline (API imperative); timeline tự dựng dạng lưới |
| Markdown chat AI | [streamdown](https://streamdown.ai) 2.7.0 | — | Apache-2.0 | Render markdown đang stream trong chat |
| i18n | **i18next 26.4.2 + react-i18next 17.0.15** | — | MIT | Đa ngôn ngữ về kiến trúc, **làm tiếng Việt trước**: MVP chỉ có resource `vi`, mọi chuỗi đi qua `t()` ngay từ đầu để thêm ngôn ngữ sau chỉ cần thêm file JSON. Lingui 6.9 là phương án thay thế |
| Phím tắt | react-hotkeys-hook 5.3.3 | — | MIT | Scope theo panel |
| Font | `@fontsource-variable/inter`, `@fontsource/be-vietnam-pro`, `@fontsource-variable/noto-serif` 5.3.0 | — | OFL | Đều có subset `vietnamese`; đóng gói offline, không `@import` Google Fonts như InkOS |

Không cần: Monaco (dành cho code, nặng), diff-match-patch (cũ, từ 2020), BlockNote (MPL-2.0, thiên về block), Lexical (chưa 1.0), Plate (nặng nhiều lớp).

## 4. Khung ứng dụng

```text
+--+-----------------------------------------------------------------------+
|R | Header: breadcrumb | [Ctrl+K Tìm/lệnh] | ● 3 truyện đang chạy | $ hôm nay|
|i |-----------------------------------------------------------------------|
|b |                                                                       |
|b |                     Nội dung theo route                               |
|o |                                                                       |
|n |-----------------------------------------------------------------------|
|  | Status bar: backend ✓ | provider: 2/4 slot | lưu ✓ | ngôn ngữ VI         |
+--+-----------------------------------------------------------------------+
Ribbon: 📚 Thư viện | ✍ Phòng viết | ⚙ Cài đặt | 📜 Nhật ký
```

- Chỉ báo "● N truyện đang chạy" ở header luôn hiện; bấm vào mở Phòng viết.
- Status bar cho biết số slot provider đang dùng, giúp hiểu vì sao job phải chờ (`waiting_slot`).

### Route (TanStack Router, hash history)

```text
/                                   Thư viện
/new                                Wizard tạo truyện
/writing-room                       Phòng viết (đa truyện)
/works/$workId                      Workspace (mặc định mode Viết)
/works/$workId?mode=plan|write|review|bible&chapter=12&tab=ai|chars|memory|review|handoff
/works/$workId/bible/$section       Story Bible
/works/$workId/review/$chapterNo    Review/Diff
/works/$workId/history/$chapterNo   Lịch sử phiên bản
/settings/$section                  Cài đặt: models | roles | concurrency | writing | data | storage
                                    | notifications | security | appearance | shortcuts | language
/logs?tab=usage|events|ai           Nhật ký và chi phí
/onboarding                         Lần chạy đầu
```

## 5. Wireframe các màn hình

### 5.1 Thư viện

```text
+--------------------------------------------------------------------------+
| Thư viện   [Tìm... Ctrl+K]  [Thể loại ▾] [Trạng thái ▾]  [▦|☰]  [+ Truyện]|
|--------------------------------------------------------------------------|
| +----------+ +----------+ +----------+ +----------+                      |
| | Bìa      | | Bìa      | | Bìa      | | Bìa      |                      |
| | Kiếm Hồn | | Mộng Đô  | | Lam Yên  | | Thủy Mặc |                      |
| | Ch 45/200| | Ch 9/60  | | Ch 3/30  | | Ch 120   |                      |
| | ▶ Đang   | | ⛔ Bị chặn| | ⏳ Chờ   | | ✓ Xong   |                      |
| |   viết   | | cần resync| |  slot #2 | |          |                      |
| | $3.20    | | $0.40    | |          | |          |                      |
| +----------+ +----------+ +----------+ +----------+                      |
+--------------------------------------------------------------------------+
```

Lưới card hoặc bảng, ảo hóa bằng TanStack Virtual. Badge trạng thái lấy từ `continuity_status` + trạng thái job.

### 5.2 Workspace truyện

```text
Mode: [Lập dàn ý] [Viết] [Review] [Bible]           Auto-write: [▶ 10 chương ▾] [auto ▾]
+----------------+------------------------------------+---------------------------+
| Chương      🔍 | Ch.12 "Đêm mưa"        2.341 âm tiết| [AI][Nhân vật][Nhớ][Nối][Rv]|
| ▾ Quyển 1      | B I H1 H2 " ...  (bubble menu)      |                           |
|   Ch.10 ✓      |                                    | Tab "Nối" (bản giao nối): |
|   Ch.11 ✓      |  Văn bản chương (Noto Serif)       |  Kết ch.11:               |
|   Ch.12 ● đang |  ⋮⋮ kéo đoạn                        |  📍 Bến đò, đêm, mưa      |
|   Ch.13 ⏳ hàng |                                    |  👥 Lâm Phong (bị thương),|
|      đợi       |                                    |     Mộc Lan               |
| ▸ Quyển 2      |                                    |  ⏸ đang truy đuổi         |
| (ảo hóa, kéo   |                                    |  🪝 Hook đến hạn: #7 (ch14)|
|  thả)          |                                    |  Mối nối ch.12: ✓ khớp    |
| [+ Chương]     |                                    |                           |
+----------------+------------------------------------+---------------------------+
| Liền mạch: ✓ ok | Lưu ✓ 2 giây trước | Ch.12 chi phí $0.02 | Bản v3 (người)       |
+------------------------------------------------------------------------------------+
     ↔ kéo giãn, thu gọn (Ctrl+B)                          ↔ kéo giãn, thu gọn (Ctrl+Alt+B)
```

Các tab panel phải:

| Tab | Nội dung |
|---|---|
| AI | Ô yêu cầu/ý đồ chương, nút Viết tiếp / Sửa đoạn chọn; **CandidateStream** (pane riêng, không ghi vào editor); card ghi "Đã dùng ngữ cảnh: …" (context trace); [Xem diff] [✓ Nhận] [✗ Bỏ] |
| Nhân vật | Nhân vật xuất hiện trong chương, trạng thái hiện tại |
| Nhớ | Facts và hooks liên quan, kết quả tìm FTS có nguồn chương |
| **Nối** | Bản giao nối của chương trước (`ending_state`, đuôi chương), kết quả seam check của chương hiện tại, hooks đến hạn. Tab này là chỗ người dùng thấy và sửa được "mạch" truyện |
| Review | Findings blocker/major/minor có trích dẫn; bấm vào để nhảy tới đoạn trong editor |

Khi truyện ở `blocked_needs_resync` hoặc `stale_from(K)`, hiển thị banner phía trên editor:

```text
⛔ Mạch truyện bị chặn ở Ch.9: trạng thái sau chương không hợp lệ (2 vòng sửa chưa đạt).
   [Xem lỗi] [Sửa tay rồi settle lại] [Chấp nhận kèm ghi chú] [Settle lại từ Ch.9]
```

### 5.3 Phòng viết (nhiều truyện song song)

```text
+-----------------------------------------------------------------------------+
| Phòng viết   Đang chạy 3 · Chờ slot 2 · Bị chặn 1    Song song: [4 ▾]       |
| Hôm nay: $4.12 / $10   Provider A: 3/4 slot, 812 RPM   [▶ Chạy tất cả] [⏸ Dừng]|
+-----------------------------------------------------------------------------+
| Truyện    | Chương | Pipeline                               | Liền mạch | $   | ⋯ |
|-----------+--------+----------------------------------------+-----------+-----+---|
| Kiếm Hồn  | 45/200 | Kế hoạch▸VIẾT▸Kiểm tra▸Nối▸Review▸Lưu  | ✓         | .31 | ⏸ |
|   └ "…hắn rút kiếm, mưa quất vào mặt…" (2 dòng cuối, cập nhật ~4 lần/giây)       |
| Thủy Mặc  | 121    | Kế hoạch▸Viết▸Kiểm tra▸NỐI ↻ vòng 1/2  | ⚠ đang sửa| .12 | ⏸ |
| Mộng Đô   | 9/60   | ⛔ waiting_user: seam fail sau 2 vòng   | ⛔        | .05 |[Xử lý]|
| Lam Yên   | 3/30   | ⏳ waiting_slot (provider đầy)          | ✓         | —   | ↕ |
| Hạ Vũ     | 1/40   | ⏳ waiting_slot (hết ngân sách truyện)  | ✓         | —   | ↕ |
+-----------------------------------------------------------------------------+
| Hàng đợi ưu tiên (kéo sắp xếp) | Log sự kiện (virtuoso) | Chi phí/giờ (Recharts) |
+-----------------------------------------------------------------------------+
```

- Mỗi dòng là một truyện. Pipeline hiển thị đúng các bước của §6.2 trong kế hoạch, bước hiện tại in đậm; vòng sửa hiện `↻ vòng k/K`.
- Lý do chờ luôn được ghi rõ: provider đầy, hết ngân sách, khóa truyện, chờ tác giả.
- Kéo dòng để đổi ưu tiên (dnd-kit), gọi API cập nhật priority.
- Bấm tên truyện mở workspace; các truyện khác vẫn chạy.
- Chỉ render 1–2 dòng cuối của mỗi luồng stream, throttle khoảng 4 lần/giây; không render toàn văn.

### 5.4 Story Bible

```text
+------------------+--------------------------------------------------------+
| Nhân vật (42)    | Lâm Phong                       [Sửa] [Hỏi AI]          |
| Địa điểm         | Tab: Hồ sơ | Quan hệ | Xuất hiện | Lịch sử thay đổi     |
| Sự kiện / Facts  | Bí danh: Phong ca, Tiểu Lâm                             |
| Hooks (7 mở,     | Trạng thái hiện tại (sau ch.44): bị thương vai trái     |
|   2 quá hạn ⚠)   | Xuất hiện: ch.1, 3, 12, … (link)                        |
| Dàn ý sự kiện    |--------------------------------------------------------|
| Timeline         | Timeline: cột = chương, hàng = tuyến truyện, card kéo thả|
| Đồ thị quan hệ   | hoặc React Flow cho quan hệ nhân vật                    |
| [🔍 lọc]         |                                                        |
+------------------+--------------------------------------------------------+
```

- Danh sách bí danh là nguồn cho kiểm tra tên riêng xác định.
- Tab **Xưng hô** trong hồ sơ nhân vật: bảng người nói → người nghe → từ xưng/gọi theo giai đoạn truyện (`address_rules`); lỗi xưng hô trong Review dẫn về đây.
- Hooks hiển thị `due_by_chapter`; hook quá hạn có cảnh báo.
- "Dàn ý sự kiện" hiển thị `story_events` với trạng thái planned/done/moved/dropped.
- Sửa Story Bible trong lúc batch đang chạy: tạo revision mới, UI ghi "áp từ chương kế tiếp" (để không làm vỡ prompt cache).

### 5.5 Review / Diff

```text
+-----------------------------------------------------------------------------+
| Ch.12   So sánh: [Bản v3 (người) ▾]  ↔  [Candidate AI #2 ▾]                  |
| [Song song | Inline]   Mức: [Từ | Câu]   +128 / −64 âm tiết                    |
+--------------------------------------+--------------------------------------+
| … mưa rơi ~~nặng hạt~~ …             | … mưa rơi [lất phất] …               |
| Đoạn 3                     [✓] [✗]   |                                      |
+--------------------------------------+--------------------------------------+
| Kiểm tra: ⛔ fact #12 mâu thuẫn (ch.7) | ⚠ nhân vật OOC | ✓ mối nối            |
| [Nhận tất cả  Ctrl+Enter]  [Bỏ  Esc]  [Nhận từng đoạn]                       |
+-----------------------------------------------------------------------------+
```

- Diff theo đoạn (neo bằng UniqueID của Tiptap), sau đó diff mức từ trong từng đoạn bằng jsdiff, chạy trong Web Worker.
- Chấp nhận = một transaction duy nhất vào editor, gửi `expected_revision`; xung đột 409 → hiển thị diff 3 bên.
- Dùng chung component cho Lịch sử phiên bản (bản manual/agent/revision/restore, theo mô hình nguồn gốc của InkOS).

### 5.6 Cài đặt

Menu trái: **Mô hình AI** · Vai trò & effort · Đồng thời & ngân sách · Viết truyện · Dữ liệu · Lưu trữ · Thông báo · Bảo mật (vault) · Giao diện & font · Phím tắt · Ngôn ngữ.

Mỗi mục cài đặt theo cùng một mẫu (như trang Models của Claude): **tiêu đề đậm**, một câu mô tả xám, link "Tìm hiểu thêm ⌄" mở phần giải thích chi tiết ngay bên dưới, điều khiển (công tắc/ô chọn) căn phải.

#### 5.6.1 Mô hình AI

```text
+-----------------------------------------------------------------------------+
| MÔ HÌNH AI                                      [● Kiểm tra lấy danh sách]  |
|                                                                             |
| Kết nối                                                                     |
| Giao thức [Anthropic ▾]  (Anthropic | OpenAI-compatible | Ollama/LM Studio) |
| Base URL  [https://llm.horusjsc.com            ]                            |
| API key   [••••••••••••]  (lưu trong vault)          [Kiểm tra kết nối]      |
|                                                                             |
| Tự lấy danh sách model                                              [ ●]   |
| Lấy danh sách model từ {Base URL}/v1/models khi mở app. Nếu tắt và          |
| danh sách bên dưới đã có model thì bỏ qua bước này.                         |
| Tìm hiểu thêm ⌄                                                             |
|                                                                             |
| Ưu tiên bản context dài (1M)                                        [○ ]   |
| Khi chưa chọn model, dùng biến thể context 1M của model mặc định nếu có.    |
| Tìm hiểu thêm ⌄                                                             |
|                                                                             |
| Danh sách model                                                             |
| Ghi đè danh sách lấy tự động. Model đầu tiên là mặc định. Kéo để đổi thứ tự.|
| Tìm hiểu thêm ⌄                                                             |
| +-------------------------------------------------------------------------+ |
| | ⋮⋮ ›  claude-balance                                     mặc định    ✕ | |
| +-------------------------------------------------------------------------+ |
| | ⋮⋮ ⌄  claude-pro                                                     ✕ | |
| |       Tên hiển thị  [Claude Pro          ]                             | |
| |       Context       [200000] token   Output tối đa [64000]             | |
| |       Effort hỗ trợ ☑low ☑medium ☑high ☑xhigh ☑max  (tự điền nếu có)    | |
| |       Giá / 1M token  vào [..]  ra [..]  đọc cache [..]  ghi cache [..] | |
| |       Dùng cho      ☑Lập kế hoạch ☑Viết ☑Kiểm tra ☑Tóm tắt ☑Review       | |
| |       Đồng thời riêng [ ] (trống = theo nhà cung cấp)                    | |
| |       Nguồn: tự lấy 02/10/2026 · ✓ đã thử gọi                           | |
| +-------------------------------------------------------------------------+ |
| + Thêm                                                                      |
|                                                                             |
| Mức effort mặc định                                  [ (mặc định model) ▾] |
| Mức effort cho mọi vai trò chưa đặt effort riêng, thay cho mức khuyến nghị  |
| của nhà cung cấp: low, medium, high, xhigh hoặc max.                        |
| Tìm hiểu thêm ⌄                                                             |
+-----------------------------------------------------------------------------+
```

Hành vi:

| Điều khiển | Hành vi |
|---|---|
| **Kiểm tra lấy danh sách** | Gọi ngay `GET {base_url}/v1/models`, hiển thị số model tìm thấy, model nào mới/biến mất so với lần trước, lỗi cụ thể (401 sai key, 404 endpoint không có, timeout). Chấm tròn trên nút: xám = chưa thử, xanh = thành công, đỏ = lỗi |
| **Tự lấy danh sách model** | Bật: lấy khi mở app (chạy nền, không chặn khởi động), lưu cache trong DB. Tắt: không gọi; nếu danh sách thủ công rỗng thì nhắc người dùng thêm model |
| **Ưu tiên bản context dài** | Chỉ ảnh hưởng lựa chọn mặc định khi người dùng chưa chọn. Mặc định **tắt**: viết chương thường không cần 1M token, còn context dài tốn chi phí hơn. Composer dùng `max_input_tokens` của model đã chọn để tính ngân sách context |
| **Danh sách model** | Rỗng: dùng toàn bộ danh sách tự lấy. Có mục: **thay thế** danh sách tự lấy, model đầu tiên là mặc định. Model tự lấy nhưng không có trong danh sách hiển thị ở mục "Model khả dụng khác" để thêm nhanh. Model có trong danh sách nhưng không còn trên server được đánh dấu ⚠ |
| **Mục mở rộng (›)** | Điền tự động từ dữ liệu `/v1/models` khi server trả về (Anthropic có `display_name`, `max_input_tokens`, `max_tokens`, `capabilities.effort`); server OpenAI-compatible thường chỉ có `id`, khi đó người dùng tự điền context/output/giá. Ô nào người dùng sửa thì giữ nguyên, lần lấy sau không ghi đè |
| **Mức effort mặc định** | Ô chọn chỉ hiện các mức model hỗ trợ; trống = không gửi tham số (dùng mặc định của nhà cung cấp). Model không hỗ trợ effort thì ô bị khóa kèm giải thích |

#### 5.6.2 Vai trò & effort

```text
+-----------------------------------------------------------------------------+
| VAI TRÒ & EFFORT                                                            |
| Vai trò          Model                 Effort                               |
| Lập kế hoạch     [claude-pro ▾]        [high ▾]                             |
| Viết chương      [claude-pro ▾]        [high ▾]                             |
| Kiểm tra/Settle  [claude-balance ▾]    [medium ▾]                           |
| Mối nối & Review [claude-balance ▾]    [medium ▾]                           |
| Tóm tắt          [claude-balance ▾]    [low ▾]                              |
| (trống = dùng model và effort mặc định ở mục Mô hình AI)                    |
| ⓘ Effort được giữ cố định trong một lượt viết để không mất prompt cache.    |
+-----------------------------------------------------------------------------+
```

Truyện có thể ghi đè vai trò/effort trong cài đặt riêng của truyện. Mỗi job **ghim** model + effort tại lúc bắt đầu; sửa cài đặt khi truyện đang chạy chỉ áp dụng từ chương kế tiếp.

#### 5.6.3 Đồng thời & ngân sách, Viết truyện, Dữ liệu

```text
| ĐỒNG THỜI & NGÂN SÁCH | Số truyện chạy song song [4]  Request đồng thời/nhà cung cấp [4] |
|                       | RPM [..]  TPM [..]   Ngân sách $/ngày [10]  theo truyện [3]      |
| VIẾT TRUYỆN           | Chế độ auto-write mặc định [review_every_k ▾] K=[5]              |
|                       | Vòng sửa tối đa mỗi chương [2]   Độ dài chương [2.500–3.500] âm tiết |
| DỮ LIỆU               | Đường dẫn data-root, backup/restore, (macOS) đổi data-root        |
```

Form dùng react-hook-form + zod; lưu tự động từng mục (không có nút Lưu chung), có toast xác nhận.

### 5.7 Wizard tạo truyện

Ngôn ngữ (MVP: Tiếng Việt) + thể loại + style profile (giọng văn, Hán Việt/thuần Việt, kiểu thoại, kiểu bỏ dấu) → Brief → Nền truyện (AI sinh, tác giả sửa) → Quy tắc xưng hô giữa các nhân vật chính → Dàn ý sự kiện → Cấu hình viết (độ dài chương theo âm tiết, chế độ auto-write, ngân sách) → Tạo. Mỗi bước lưu draft; đóng giữa chừng mở lại được.

### 5.8 Màn hình và trạng thái bổ sung

Chi tiết và mức ưu tiên tại [implementation-plan.vi.md §23.4](./implementation-plan.vi.md):

- **Onboarding lần chạy đầu:** (macOS) chọn data-root → mật khẩu vault hoặc dùng key theo phiên → thêm provider và kiểm tra lấy danh sách model → tạo truyện đầu tiên.
- **Trạng thái backend:** đang khởi động; backend dừng bất ngờ (nút khởi động lại); banner mất kết nối và tự nối lại.
- **Chương đang làm nền:** chương N-1 read-only khi chương N đang viết, nút "Tạm dừng để sửa".
- **Hộp thoại:** mở khóa vault; auto-write (số chương, chế độ, ước tính chi phí/thời gian); export (định dạng, khoảng chương, metadata).
- **Trung tâm thông báo**, **chế độ tập trung** (Ctrl+Shift+F), **trang Lưu trữ** (dung lượng, dọn dẹp).
- **State theo chương:** Story Bible có thanh trượt chương để xem `StoryState` sau chương bất kỳ; tab "Nối" cho sửa `ending_state`.
- **Mẫu trạng thái thống nhất:** skeleton khi tải, màn rỗng có hướng dẫn, lỗi theo mã kèm nút hành động.

## 6. Hiệu năng UI khi nhiều truyện cùng stream

Theo [hướng dẫn hiệu năng của Tiptap](https://tiptap.dev/docs/guides/performance) và yêu cầu đa truyện:

1. **Không stream token vào editor.** Token đi vào component `CandidateStream` riêng.
2. **Gom token vào buffer** (ref), flush bằng `requestAnimationFrame` hoặc mỗi 50–100 ms.
3. **Một event bus duy nhất** nhận SSE từ backend rồi phân phối theo `workId`; store Zustand theo `workId`, component dùng selector hẹp.
4. **Cô lập editor**: `shouldRerenderOnTransaction: false`; toolbar dùng `useEditorState(selector)`.
5. **Phòng viết** chỉ hiện 1–2 dòng cuối mỗi luồng, throttle khoảng 4 lần/giây.
6. **Ảo hóa** danh sách chương, thư viện, log.
7. **Lazy-load** React Flow, Recharts, diff viewer.
8. Mỗi chương là một document Tiptap riêng; không nạp cả truyện vào một editor.

## 7. Học gì từ InkOS Studio

InkOS Studio (`E:\Inke\inkos\packages\studio\src`) là **AGPL-3.0-only**: chỉ tham khảo ý tưởng, không chép code.

| Nên mượn ý tưởng | Nên cải thiện |
|---|---|
| Panel phải chia section: tiến độ, nhân vật, hooks chờ (`components/sidebar/`) | Hash route tự viết (`hooks/use-hash-route.ts`) → TanStack Router có type |
| Mô hình phiên bản có nguồn gốc manual/agent/revision/regeneration/restore (`components/ChapterWorkspacePanel.tsx`) | `useApi` tự viết → TanStack Query |
| Card riêng cho hook và state (truth files) | `<textarea>` → Tiptap |
| streamdown cho chat AI | Không có diff → diff mức từ |
| Gom SSE về một chỗ (`hooks/use-sse.ts`) | Trang Daemon chỉ có Start/Stop + log → Phòng viết đa truyện |
| Màn chọn ngôn ngữ lần đầu; dùng Base UI | Không ảo hóa, không panel kéo giãn → TanStack Virtual, react-resizable-panels |
| | Font qua Google Fonts `@import` (không chạy offline) → Fontsource subset vietnamese |
| | Dictionary i18n trong TS → i18next JSON |
| | File quá lớn (`ChatPage.tsx` 1.367 dòng, `Sidebar.tsx` 828 dòng) → tách theo feature |

## 8. Phím tắt và khả năng tiếp cận

| Phím | Hành động |
|---|---|
| Ctrl+K | Command palette |
| Ctrl+B / Ctrl+Alt+B | Bật/tắt panel trái / phải |
| Ctrl+Enter / Esc | Nhận / bỏ candidate |
| Alt+↑ / Alt+↓ | Chương trước / sau |
| Ctrl+S | Tạo snapshot thủ công |
| Ctrl+Shift+W | Mở Phòng viết |

- Base UI lo focus và ARIA; mọi nút chỉ có icon phải có `aria-label` tiếng Việt.
- Trạng thái không chỉ dùng màu: luôn có icon và chữ (✓ / ⚠ / ⛔ / ⏳).
- Hỗ trợ dark/light; font đọc (Noto Serif) và font UI (Be Vietnam Pro hoặc Inter) chỉnh cỡ được.

## 9. Cấu trúc thư mục FE theo màn hình

```text
fe/src/features/
  library/            Thư viện, wizard tạo truyện
  writing_room/       Phòng viết: bảng truyện, pipeline, hàng đợi, chi phí
  workspace/          Khung 3 cột, thanh mode, banner liền mạch
  editor/             Tiptap, autosave, extensions
  ai_workspace/       CandidateStream, context trace, accept/reject
  continuity/         Tab Nối: handoff, seam check, hooks đến hạn
  review/             Findings, diff (worker), lịch sử phiên bản
  story_bible/        Nhân vật, facts, hooks, dàn ý sự kiện, timeline, đồ thị
  jobs/               Event bus SSE, store stream theo workId
  settings/           Provider, đồng thời, ngân sách, dữ liệu, giao diện
fe/src/shared/
  ui/                 Thành phần shadcn (Base UI)
  i18n/vi/*.json      Chuỗi tiếng Việt theo namespace (ngôn ngữ đầu tiên; thêm i18n/<lang>/ sau)
```

## 10. Việc cần kiểm chứng ở R0

| Mục | Cách kiểm |
|---|---|
| IME tiếng Việt trên Tiptap (Unikey, EVKey, Telex/VNI macOS) | Test tay trên WebView2 và WKWebView (xem kế hoạch §9 Giai đoạn 0) |
| react-arborist với React 19 Strict Mode | Dựng cây 2.000 chương, kéo thả, đổi tên |
| `Intl.Segmenter('vi', {granularity:'word'})` trên WebView2/WKWebView | Có thể chỉ tách theo âm tiết; vẫn đủ cho diff, cần xác nhận |
| shadcn Resizable dùng react-resizable-panels v4 | Kiểm tra wrapper khi cài |
| Tên khóa cấu hình WebView2 `fixedRuntime` | Đọc schema Tauri |
| Hiệu năng 5 luồng stream + editor đang gõ | Mock provider, đo FPS và độ trễ gõ phím |

Chưa kiểm chứng: license thực tế của dockview (không chọn nên không chặn); font serif khác (Literata, Source Serif 4) có subset tiếng Việt hay không; giá add-on Tracked Changes/AI Toolkit của Tiptap (không dùng).
