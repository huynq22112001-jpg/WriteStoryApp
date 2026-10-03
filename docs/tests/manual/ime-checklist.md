# Checklist thủ công: bộ gõ tiếng Việt trong Tiptap

Ngày chạy: __________  Người chạy: __________  Commit/build: __________

Ghi kết quả thực tế sau mỗi bước. Để trống đến khi có người chạy; không suy diễn kết quả từ test tự động.

## Môi trường

| Mục | Giá trị |
|---|---|
| Hệ điều hành và phiên bản | |
| WebView2 / WKWebView và phiên bản | |
| WriteStoryApp chạy bằng `tauri dev` / bản đóng gói | |
| Bàn phím / ngôn ngữ hệ thống | |

Mở `/#/editor-spike`. Câu mẫu: “Người đàn ông ấy đứng lặng trước bến đò, mưa quất vào mặt.” và “Thuở ấy, hoà bình chưa về; khuya, quýt, gìn giữ, Nguyễn Văn Ộc.” So với mẫu sau từng bước; ghi ký tự mất/nhân đôi, vị trí con trỏ sai, lỗi dấu hoặc dấu định dạng bất ngờ.

| Bộ gõ / chế độ | Gõ đoạn thường | Trong **bold** / *italic* | Đầu/cuối mark | Undo/redo | Dán Word/web | Backspace giữa từ | Ghi chú / bằng chứng |
|---|---|---|---|---|---|---|---|
| Windows: Unikey Telex, “sửa lỗi gợi ý” bật | | | | | | | |
| Windows: Unikey Telex, “sửa lỗi gợi ý” tắt | | | | | | | |
| Windows: Unikey VNI | | | | | | | |
| Windows: EVKey Telex, “sửa lỗi gợi ý” bật | | | | | | | |
| Windows: EVKey Telex, “sửa lỗi gợi ý” tắt | | | | | | | |
| macOS: Telex có sẵn | | | | | | | |
| macOS: VNI có sẵn | | | | | | | |

## Các bước

Với từng cấu hình ở trên, đánh dấu từng ô là Đạt / Không đạt và ghi phiên bản bộ gõ. Nếu cấu hình không có trên hệ điều hành đang thử, ghi “Không áp dụng” cùng lý do.

1. Gõ câu mẫu ở đoạn thường; thử Telex/VNI gồm `hoà`, `hòa`, `quýt`, `gìn`, `Ộc`.
2. Bật/tắt nút **B** và *I*, gõ câu mẫu trong vùng định dạng.
3. Đặt con trỏ ngay đầu và cuối vùng bold/italic rồi gõ; xác nhận mark không lan sang chữ bên cạnh và không bị mất.
4. Gõ một cụm từ có dấu, undo rồi redo; kiểm tra không mất dấu hoặc để lại chữ nửa vời.
5. Paste văn bản từ Word/web, gồm dấu tiếng Việt và nhiều đoạn; sau paste gõ tiếp.
6. Đặt con trỏ giữa từ trong lúc đang ghép dấu rồi nhấn Backspace; xác nhận chỉ xóa ký tự dự kiến.
7. Gõ đoạn dài liên tục khoảng 2 phút, so nội dung cuối cùng với bản mẫu đã chuẩn bị.
8. Chọn một đoạn, gõ đè bằng IME; kiểm tra không mất phần chưa chọn và không nhân đôi phần đã chọn.
9. Quan sát số âm tiết/ký tự dưới editor sau gõ và paste; xác nhận số liệu phù hợp nội dung.

## Kết quả theo cấu hình

| Cấu hình | Đạt / Không đạt / Chưa chạy | Lỗi tái hiện và bước | Ảnh/clip hoặc log | Người chạy / ngày |
|---|---|---|---|---|
| Windows WebView2 | Chưa chạy | | | |
| macOS WKWebView | Chưa chạy | | | |

Chỉ ghi đạt cho cấu hình và thao tác đã chạy thật. Lỗi làm mất/nhân đôi ký tự cần được ghi lại kèm bước tái hiện trước khi quyết định shell.
