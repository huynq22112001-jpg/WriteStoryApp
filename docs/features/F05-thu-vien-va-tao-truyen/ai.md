# F05 — AI

Không áp dụng – lý do: thư viện, CRUD tác phẩm, style profile và các bước Cơ bản / Brief / Cấu hình viết / Tạo của wizard không gọi model. Bước sinh nền truyện, nhân vật, quy tắc xưng hô và dàn ý sự kiện trong wizard thuộc [F06 ai.md](../F06-nen-truyen-va-story-bible/ai.md) (workflow foundation, Plan FL03, §6.1).

## Ranh giới với phần AI ở tính năng khác

| Dữ liệu F05 tạo ra | Phần AI dùng nó | Tính năng |
|---|---|---|
| `works.brief`, `genre`, `target_chapters`, `chapter_length_min/max` | Input của workflow foundation (`FoundationInput`) | [F06](../F06-nen-truyen-va-story-bible/ai.md) |
| `style_profile` (lớp từ, kiểu thoại, kiểu bỏ dấu, cụm sáo cấm, giọng văn, đoạn mẫu) | Lớp 1–2 của prompt (Plan §6.4, §23.3 #7), kiểm tra xác định tiếng Việt (Plan §6.6) | F08, F10 |
| `works.language` | Chọn `LanguagePack` (Plan §6.6) | F08 |
| Ghi đè vai trò theo truyện (qua F04) | `ModelSelection` theo vai trò | [F04](../F04-cau-hinh-mo-hinh-ai/ai.md) |
| Preset thể loại | Đọc từ `ai/src/writestory_ai/languages/vi/genres.json` bằng `importlib.resources`; chỉ là dữ liệu tĩnh, không gọi model | F08 sở hữu nội dung |

Sửa `style_profile` khi truyện đang chạy không đổi prompt của chương đang viết; áp từ chương kế tiếp để không phá prompt cache (Plan §6.4; cơ chế `bible_revisions` ở F06).

## Tên mới đề xuất

Không có.
