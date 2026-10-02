# F07 — Editor và phiên bản

Giai đoạn: R0 (spike Tiptap + IME tiếng Việt trên WebView2/WKWebView) → R1 (working copy, revision, chương CRUD) → R2 (diff/restore đầy đủ, chế độ "chương đang làm nền", phối hợp F11/F12). Trạng thái: planned.

## Mục tiêu

Người dùng mở một chương, gõ tiếng Việt ổn định bằng Unikey/EVKey/Telex macOS, được autosave liên tục vào bản làm việc mà không sinh revision rác; revision chỉ tạo ở các mốc có ý nghĩa; xem lịch sử, so sánh hai bản (theo đoạn rồi theo từ), khôi phục bản cũ thành bản mới; không bao giờ ghi đè lẫn nhau với AI (409 khi lệch revision); khi chương đang là nền của chương AI đang viết thì editor chỉ đọc kèm nút "Tạm dừng để sửa".

## Phạm vi

- Trong phạm vi:
  - Cấu hình Tiptap v3 (extension theo UI §3), `UniqueID` sinh `paragraph_id` cho từng đoạn (Plan §23.1.B), pin `prosemirror-view` ≥ 1.41.9.
  - Bảng `chapters`, `chapter_revisions`, `chapter_working_copy`; plain-text projection theo đoạn.
  - API: chapters CRUD/reorder, working copy GET/PUT (base revision), snapshot (Ctrl+S), revisions list/get, diff, restore, `PUT /v1/chapters/{id}` có `expected_revision`.
  - Autosave debounce 500–1.000 ms, flush khi đổi chương/đóng cửa sổ; quy tắc tạo revision Plan §23.2 #2.
  - Diff: BE căn đoạn theo `paragraph_id`, FE diff mức từ bằng jsdiff trong Web Worker với `Intl.Segmenter('vi')`; trang Lịch sử phiên bản.
  - Chế độ chỉ đọc "chương đang làm nền" + "Tạm dừng để sửa" (Plan §23.2 #3, §23.4 #3) phối hợp F12.
  - Chế độ tập trung (Ctrl+Shift+F), cây chương cơ bản (tạo/đổi tên/xóa/sắp xếp), chuẩn hóa NFC khi paste, checklist IME.
- Ngoài phạm vi:
  - Candidate AI, nhận từng đoạn, diff 3 bên khi xung đột với candidate, áp `ops` theo `paragraph_id` → F11 (BE áp ops; F07 cung cấp hàm sinh ID và projection).
  - Đánh dấu `stale_from(K)`/resync khi sửa/chèn/xóa chương committed → F11 (F07 gọi port của F11).
  - Tạm dừng batch auto-write → F12 (F07 gọi API pause và chờ event).
  - Đếm âm tiết chuẩn của gói ngôn ngữ → F08 (F07 dùng bản tạm cho tới khi có F08).
  - Export → F13; tìm kiếm FTS trong truyện → F09.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F01 | Hợp đồng lỗi (`REVISION_CONFLICT` 409), event `job.state`/`chapter.committed`, OpenAPI → TS |
| F02 | SQLite, writer queue, migration |
| F00 | Sự kiện đóng cửa sổ của Tauri để flush autosave trước khi thoát |
| F11 (R2) | `stale_from`, candidate accept dùng `snapshot_if_dirty` của F07 |
| F12 (R2) | Biết job nào đang dùng chương làm nền; API pause |

## Nguồn thiết kế

- Plan §2 (Tiptap, `prosemirror-view` ≥ 1.41.9, jsdiff Web Worker), §4.2 (optimistic concurrency), §4.4 (autosave 500–1.000 ms, mở chương ~300 ms – tiêu chí chưa đo), §5 (`chapters`, `chapter_revisions`, `chapter_working_copy`), §6.6 (NFC khi paste), §7 (`PUT /v1/chapters/{id}`, revisions, working-copy, snapshot, diff, restore, chapters CRUD), §9 Giai đoạn 0 và 2, FL07, **§23.1.B**, **§23.2 #2–#4**, §23.4 #3, #8.
- Plan §15.4 EDT01, EDT04, EDT08, EDT09; §19 NEW03, NEW05.
- Arch §4 (`fe/src/features/editor/`, `review/`), §5 (`be/.../modules/chapters/`).
- UI §3 (thư viện editor/diff), §5.2 (workspace, status bar), §5.5 (Review/Diff – dùng chung cho Lịch sử), §5.8, §6 (hiệu năng editor), §8 (phím tắt), §10 (kiểm chứng R0).
- Review §7.5 (IME tiếng Việt), §1 #14.

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Module `chapters`: 3 bảng, projection `paragraph_id`, working copy có base revision, quy tắc tạo revision, diff theo đoạn, restore, khóa chỉ đọc |
| FE | [fe.md](./fe.md) | `features/editor` (Tiptap, autosave, read-only, focus mode, paste NFC) + `features/review` (lịch sử, diff worker); checklist IME |
| AI | [ai.md](./ai.md) | Không áp dụng – áp `ops` theo đoạn thuộc BE (F11) |

## Tiêu chí hoàn thành

- [ ] Checklist IME (fe.md) pass trên WebView2 (Windows) và WKWebView (macOS bản thấp nhất hỗ trợ) – điều kiện quyết định giữ Tauri ở R0 (Plan §9 Giai đoạn 0).
- [ ] Gõ liên tục 10 phút: số revision không tăng (chỉ working copy); rời chương/Ctrl+S/nhàn 2 phút tạo đúng 1 revision khi có thay đổi.
- [ ] Kill backend hoặc app giữa lúc gõ → mở lại mất tối đa thay đổi trong khoảng debounce chưa gửi (Plan §9 Giai đoạn 2: crash không làm mất bản đã lưu).
- [ ] Mọi đoạn có `paragraph_id` duy nhất trong chương; ID giữ nguyên qua lưu/mở lại/restore; paste/split không tạo ID trùng.
- [ ] Diff hai bản hiển thị theo đoạn và theo từ, đúng với tiếng Việt có dấu; không khóa UI khi chương dài (chạy trong Worker).
- [ ] Restore tạo revision mới, lịch sử không mất bản nào.
- [ ] Ghi working copy/snapshot với base lệch → 409, không ghi đè; UI giữ bản của người dùng.
- [ ] Chương N-1 chỉ đọc khi chương N đang viết; "Tạm dừng để sửa" mở khóa sau khi job dừng.
- [ ] Văn bản dán từ Word/web lưu ở dạng NFC; xuất/nhập lại giữ đúng nội dung Unicode.
- [ ] Các test luồng liên quan pass: [T12](../../tests/flows/T12-editor-autosave-ime.md); phần sửa tay của [T10](../../tests/flows/T10-sua-tay-va-resync.md).

## Rủi ro và câu hỏi mở

- **IME trên WKWebView** là rủi ro cao nhất (Review §7.5); không khắc phục được trong ngân sách spike → cân nhắc Electron (Plan §2).
- **`PUT /v1/chapters/{id}` và `POST …/snapshot` chồng chức năng:** Plan §7 có cả hai. Đề xuất ở be.md: PUT dùng cho đổi tiêu đề và thay toàn văn (EDT04), snapshot dùng để chốt working copy thành revision.
- **Giá trị `chapter_revisions.source`:** Plan §5 chỉ ghi "nguồn sửa"; UI §5.5 nêu "manual/agent/revision/restore". Đề xuất `manual|agent|revise|restore|import` – cần chốt cùng F11.
- **Chương `waiting_user` có candidate dựa trên N-1:** sửa N-1 làm candidate lệch base; đề xuất cảnh báo và để F11 đánh dấu candidate `superseded`.
- `CharacterCount` của Tiptap v3 cho phép hàm đếm tùy biến (cần xác nhận API khi pin phiên bản) để hiển thị số âm tiết.
- `Intl.Segmenter('vi', {granularity:'word'})` có thể chỉ tách theo âm tiết (UI §10) – vẫn đủ cho diff, cần xác nhận trên cả hai webview.
- Cây chương (react-arborist) chưa được giao cho tính năng nào; đề xuất F07 làm bản cơ bản.
