# T12 — Editor, autosave, revision và IME tiếng Việt

Tính năng: F07. Nguồn: Plan §23.2 #2, §23.1.B, §4.4 (autosave, mở chương), §6.6 (NFC khi dán), §9 Giai đoạn 0 và 2, §2 (pin `prosemirror-view` ≥ 1.41.9), UI §5.5, §6, §10; Review §7.5. Cấp test chính: integration, e2e-fe, thủ công.

## Mục đích

Chứng minh editor không làm mất chữ: autosave ghi working copy (không tạo revision mỗi lần), revision chỉ tạo ở các mốc quy định, diff/restore không xóa lịch sử, `paragraph_id` ổn định, văn bản luôn NFC, và gõ tiếng Việt bằng Unikey/EVKey/Telex/VNI ổn định trên WebView2 và WKWebView.

## Tiền điều kiện và dữ liệu

- Truyện `tests/fixtures/stories/do_thi_01/` (3 chương); ch.1 ~3.000 âm tiết.
- File dán thử: `tests/fixtures/paste/word_vi_nfd.html` (HTML từ Word, có dấu dạng NFD, bold/italic, ngắt dòng mềm), `tests/fixtures/paste/long_10k_syllables.txt`.
- Không cần mock provider trừ T12-07 (dùng `{scripted_outputs: {revise: "do_thi_01/revise_ch01.json"}}`).

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T12-01 | thành công | Gõ 20 ký tự trong ch.1, dừng 1,5 s. | Đúng 1 `PUT /v1/chapters/{id}/working-copy` kèm base revision sau debounce 500–1.000 ms; `chapter_working_copy` cập nhật; 0 dòng `chapter_revisions` mới; status bar "Lưu ✓". | e2e-fe, integration | `fe/tests/e2e/autosave.spec.ts`, `be/tests/integration/test_working_copy.py` |
| T12-02 | thành công | Lần lượt: rời chương (Alt+↓); để nhàn 2 phút có thay đổi (đồng hồ giả); Ctrl+S (`POST /v1/chapters/{id}/snapshot`); nhận candidate AI; restore revision cũ. | Mỗi mốc tạo đúng 1 revision (nhận AI tạo revision trước và sau; restore tạo revision chụp trước rồi revision restore); không mốc nào khác tạo revision. | integration, e2e-fe | `be/tests/integration/test_revision_triggers.py` |
| T12-03 | phục hồi | Gõ, chờ autosave xong, kill backend + shell; mở lại. | Working copy được nạp lại vào editor (không mất chữ đã autosave); revision history nguyên vẹn; editor báo đang có bản sửa chưa chụp revision. | desktop, integration | `tests/desktop/test_autosave_crash.py` |
| T12-04 | lỗi | Backend tạm không phản hồi (mock 503) khi autosave. | Status bar "chưa lưu được" + nút thử lại; buffer giữ trong editor; khi backend trở lại, autosave tự gửi lại; đóng cửa sổ khi chưa lưu → cảnh báo. | e2e-fe | `fe/tests/e2e/autosave_error.spec.ts` |
| T12-05 | biên | Gõ rồi đổi chương ngay (< debounce) và đóng cửa sổ ngay sau khi gõ. | Flush ngay khi đổi chương/đóng cửa sổ: working copy chứa ký tự cuối cùng. | e2e-fe, desktop | `fe/tests/e2e/autosave_flush.spec.ts` |
| T12-06 | lỗi | Hai cửa sổ/tab FE mở cùng chương; tab A tạo revision R6; tab B (base R5) autosave. | B nhận `409 REVISION_CONFLICT`, không ghi đè; B hiện xung đột và cho xem diff. | integration, e2e-fe | `be/tests/integration/test_working_copy_conflict.py` |
| T12-07 | thành công | `GET /v1/chapters/{id}/revisions/{a}/diff/{b}`; restore revision a. | Diff theo đoạn (`paragraph_id`) và mức từ; restore tạo revision mới, mọi revision cũ còn nguyên (đếm trước/sau +2: chụp + restore). | integration | `be/tests/integration/test_diff_restore.py` |
| T12-08 | biên | Sửa giữa đoạn `p4`; tách `p4` bằng Enter; gộp `p6` vào `p5` bằng Backspace; dán 3 đoạn. | `p4` giữ ID khi sửa; phần sau khi tách có ID mới; đoạn gộp giữ ID của `p5`; đoạn dán có ID mới, không trùng; plain-text projection ở BE giữ đúng ID. | e2e-fe, integration | `fe/src/features/editor/extensions/paragraphId.test.ts` |
| T12-09 | biên | Dán `word_vi_nfd.html`. | Văn bản lưu dạng NFC (kiểm bằng `is_normalized`); bold/italic giữ; style Word lạ bị loại; không xuất hiện ký tự dấu tách rời. | e2e-fe, integration | `fe/tests/e2e/paste_word.spec.ts` |
| T12-10 | hiệu năng | Dán `long_10k_syllables.txt`; mở chương 3.000 âm tiết. | Dán xong không treo UI > 200 ms liên tục; mở chương đã lưu p95 < 300 ms sau backend sẵn sàng; CharacterCount hiện số âm tiết. | e2e-fe | `fe/tests/e2e/editor_perf.spec.ts` |
| T12-11 | biên | Undo/redo 50 bước sau khi gõ tiếng Việt, dán, nhận candidate. | Undo không làm vỡ dấu (không còn trạng thái nửa từ như "tie" + dấu rời); nhận candidate là 1 bước undo. | e2e-fe | `fe/tests/e2e/undo_redo.spec.ts` |
| T12-12 | thành công | Xuất TXT ch.1 rồi nhập lại văn bản (dán) vào chương mới; so sánh. | Nội dung Unicode giống hệt sau NFC (so chuỗi). | integration | `be/tests/integration/test_unicode_roundtrip.py` |
| T12-13 | biên | Kiểm phiên bản phụ thuộc. | `prosemirror-view` trong lockfile ≥ 1.41.9 (test fail nếu thấp hơn). | unit | `fe/tests/deps/prosemirror_version.test.ts` |
| T12-14 | thủ công | Checklist IME bên dưới trên Windows WebView2 và macOS WKWebView (phiên bản macOS tối thiểu hỗ trợ). | Mọi ô trong checklist đạt; lỗi không khắc phục được trên WKWebView là tiêu chí chuyển Electron (Plan §9 Giai đoạn 0). | thủ công | `tests/desktop/ime_vi_checklist.md` |

## Checklist IME tiếng Việt (T12-14)

Câu mẫu gõ: "Người đàn ông ấy đứng lặng trước bến đò, mưa quất vào mặt." và "Thuở ấy, hoà bình chưa về; khuya, quýt, gìn giữ, Nguyễn Văn Ộc." Mỗi ô ghi Đạt/Không đạt + ảnh/clip khi lỗi.

| Bộ gõ / chế độ | Gõ đoạn thường | Trong **bold**/*italic* | Đầu/cuối mark | Undo/redo | Dán từ Word | Backspace giữa từ |
|---|---|---|---|---|---|---|
| Unikey Telex, "sửa lỗi gợi ý" bật | | | | | | |
| Unikey Telex, "sửa lỗi gợi ý" tắt | | | | | | |
| Unikey VNI | | | | | | |
| EVKey Telex, "sửa lỗi gợi ý" bật | | | | | | |
| EVKey Telex, "sửa lỗi gợi ý" tắt | | | | | | |
| macOS Telex có sẵn | | | | | | |
| macOS VNI có sẵn | | | | | | |

Tiêu chí từng ô: không nhân đôi ký tự (kiểu tiptap#2780); không mất dấu; con trỏ không nhảy; không tạo đoạn mới ngoài ý muốn; gõ ở đầu và cuối vùng bold/italic không làm mark lan sang chữ bên cạnh hoặc mất mark; Undo hoàn tác theo từ đã gõ, không để lại chữ nửa vời; Backspace trong lúc đang ghép dấu xóa đúng một ký tự; autosave trong lúc đang composition không làm gián đoạn gõ; working copy sau khi gõ là NFC.

## Kiểm tra dữ liệu sau test

- DB: `chapter_working_copy` một dòng mỗi chương, base revision đúng; `chapter_revisions` chỉ tăng ở các mốc T12-02; mọi văn bản NFC.
- `paragraph_id` duy nhất trong mỗi chương, ổn định qua sửa/tách/gộp như T12-08.
- Event: không có event job cho autosave; `chapter.committed` không phát khi autosave.

## Tiêu chí pass

- 0 ký tự mất qua crash sau autosave (T12-03) và qua đổi chương/đóng cửa sổ (T12-05).
- 0 revision tạo bởi autosave thông thường.
- 0 ghi đè khi base lệch (mọi trường hợp trả 409).
- Checklist IME: 100% ô đạt trên WebView2; WKWebView không có lỗi mức "mất/nhân đôi ký tự"; lỗi còn lại được ghi issue kèm bước tái hiện.
- Mở chương p95 < 300 ms (tiêu chí đề xuất §4.4).

## Ghi chú thủ công

- Chạy checklist IME trên máy thật, không qua remote desktop (RDP có thể đổi cách gửi phím). Ghi phiên bản Unikey/EVKey, WebView2, macOS.
- Lặp lại checklist mỗi khi nâng `@tiptap/*` hoặc `prosemirror-view`.

## Tên mới đề xuất

- Nguồn revision trong `chapter_revisions.source`: `manual` (Ctrl+S), `auto_snapshot` (rời chương/nhàn 2 phút), `agent` (nhận AI), `pre_agent` (chụp trước nhận AI), `restore`.
