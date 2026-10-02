# T13 — Kiểm tra tiếng Việt

Tính năng: F08. Nguồn: Plan §6.6 (gói ngôn ngữ `vi`), §5 (FTS5, chuẩn hóa `đ→d`), §2 (Search MVP), §6.2 bước 5, §9 Giai đoạn 4, Review §7.3 (FTS5 đã chạy thử trên SQLite 3.51.3). Cấp test chính: unit, contract, integration.

## Mục đích

Chứng minh gói ngôn ngữ `vi` chuẩn hóa văn bản (NFC, kiểu bỏ dấu), đếm độ dài bằng âm tiết, phát hiện xác định lỗi xưng hô, tên riêng, lớp từ, cụm sáo, chính tả mà không tự sửa văn bản, và tìm kiếm FTS5 khớp được chữ có/không dấu kể cả chữ hai dấu và `đ`.

## Tiền điều kiện và dữ liệu

- Câu kiểm FTS (giống Review §7.3): `"Đường đi Nguyễn Văn Ộc người ơi"`.
- Truyện `tests/fixtures/stories/tien_hiep_01/`: canon "Lâm Phong" (bí danh "Phong ca", "Tiểu Lâm", không dấu "Lam Phong"), "Mộc Lan", "Hắc Long" (tên thuần Việt "Rồng Đen", canon không cho dùng lẫn); `address_rules` Lâm Phong → Mộc Lan "ta/ngươi" ch.1–14, "huynh/muội" từ ch.15; style profile: kiểu bỏ dấu mới (`hòa`), thoại gạch đầu dòng.
- Truyện `tests/fixtures/stories/do_thi_01/`: đô thị, xưng hô anh–em, style profile hạn chế Hán Việt.
- Bộ câu kiểm: `tests/fixtures/vi_checks/*.json` (mỗi mục: văn bản, kỳ vọng finding/không finding).
- Không cần mock provider trừ T13-19 (`{scripted_outputs: {write: "vi_checks/prompt_snapshot_ch04.txt"}}`).

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T13-01 | thành công | `length_counter` với: "Lâm Phong rút kiếm." / "– Đi thôi! – hắn nói." / "Ba… bốn … năm" / "3.500 lượng bạc" / "Nguyễn" dạng NFD / chuỗi có nhiều khoảng trắng, xuống dòng. | Lần lượt 4 / 4 / 3 / 3 / 1 / đếm đúng số âm tiết (dấu câu đứng riêng như "–", "…" bị bỏ; NFD đếm như NFC). Số ký tự trả kèm để UI hiển thị. | unit | `ai/tests/unit/test_vi_length_counter.py` |
| T13-02 | biên | "anh-em", "Lâm-Phong", "A.I." | Đếm theo quy tắc tách khoảng trắng (mỗi chuỗi = 1); ghi rõ trong tài liệu gói `vi` vì là quyết định quy ước. | unit | như trên |
| T13-03 | thành công | `normalizer` với văn bản NFD, có ký tự zero-width, khoảng trắng không ngắt. | Đầu ra NFC; quy tắc xử lý ký tự đặc biệt nhất quán; idempotent (chuẩn hóa hai lần cho cùng kết quả). | unit | `ai/tests/unit/test_vi_normalizer.py` |
| T13-04 | lỗi | Chương có cả "hoà" và "hòa", "thuý" và "thúy"; truyện cấu hình kiểu mới. | Finding cảnh báo trộn kiểu bỏ dấu, liệt kê từng vị trí theo `paragraph_id`; văn bản không bị tự sửa. Kiểm toàn truyện: báo chương nào lệch kiểu so với `style_profile`. | unit, integration | `ai/tests/unit/test_vi_tone_mark_style.py` |
| T13-05 | lỗi | Truyện thoại gạch đầu dòng nhưng chương dùng ngoặc kép; "hắn nói ," (khoảng trắng trước dấu phẩy). | Cảnh báo quy ước thoại và khoảng trắng dấu câu, có vị trí. | unit | `ai/tests/unit/test_vi_punctuation.py` |
| T13-06 | lỗi | Ch.8, thoại Lâm Phong nói với Mộc Lan: "– Tôi sẽ đi cùng cô." | Finding `address` (mức blocker, đề xuất) trích đoạn, nêu quy tắc hiệu lực "ta/ngươi" và từ sai "tôi/cô"; dẫn tới tab Xưng hô của nhân vật. | unit, integration | `ai/tests/unit/test_vi_address_rules.py` |
| T13-07 | thành công | Ch.10, delta có `address.change` (kết nghĩa, có `evidence`) sang "huynh/muội"; thoại ch.10–12 dùng "huynh/muội". | Không finding `address`; quy tắc mới áp từ chương có sự kiện. Cùng thoại ở ch.9 (trước sự kiện) → finding. | unit, integration | như trên |
| T13-08 | biên | Thoại không xác định được người nói/người nghe (không có dẫn thoại, nhiều nhân vật có mặt). | Không tạo blocker (tránh báo sai); ghi cảnh báo "không xác định được cặp xưng hô" mức minor. | unit | như trên |
| T13-09 | lỗi | Văn bản có "Lâm Phong", "Lam Phong", "Phong ca", "Lâm Phog", "Hắc Long" và "Rồng Đen" trong cùng chương. | Ba tên đầu hợp lệ (canon/bí danh, kể cả không dấu); "Lâm Phog" → finding `name`/`blocker`; dùng lẫn "Hắc Long"/"Rồng Đen" → cảnh báo vì canon không cho phép. | unit | `ai/tests/unit/test_vi_names.py` |
| T13-10 | lỗi | Tiên hiệp: "rút điện thoại", "lên ô tô", "OK". Đô thị: cùng câu. | Tiên hiệp: 3 cảnh báo lớp từ lạc thời (mức minor) theo danh sách thể loại. Đô thị: 0 cảnh báo. Đô thị với style profile hạn chế Hán Việt + đoạn dày từ Hán Việt → cảnh báo lạm dụng Hán Việt. | unit | `ai/tests/unit/test_vi_register.py` |
| T13-11 | lỗi | Đoạn mở bằng "Trong khoảnh khắc ấy"; chương có "không khỏi" 6 lần, "một cách" 8 lần (vượt ngưỡng mật độ cấu hình); tác giả thêm "bỗng nhiên" vào danh sách. | Finding `slop` cho từng vị trí/mật độ vượt ngưỡng; cụm tác giả thêm được phát hiện ở lần chạy sau; trong pipeline, finding này kích hoạt sửa cục bộ đoạn vi phạm. | unit, integration | `ai/tests/unit/test_vi_slop_list.py` |
| T13-12 | lỗi | Chính tả: "tieengs", "ddi", "nguwowif", "hoaf"; hợp lệ: "tiếng", "đi", tên canon, từ trong allowlist. | 4 cảnh báo Telex sót (từ điển âm tiết hợp lệ); 0 cảnh báo cho từ hợp lệ, tên canon, allowlist; văn bản không bị tự sửa (hash không đổi). | unit | `ai/tests/unit/test_vi_spelling.py` |
| T13-13 | biên | Lỗi hỏi/ngã mà cả hai dạng đều là âm tiết hợp lệ: "dể dàng", "sữa chữa". | Kỳ vọng tạm: chỉ phát hiện nếu có từ điển từ ghép/bigram; với từ điển âm tiết thuần thì không phát hiện — test ghi nhận giới hạn, không fail (xem mục mâu thuẫn). | unit | như trên |
| T13-14 | thành công | FTS5 tokenizer `unicode61 remove_diacritics 1`, không chuẩn hóa app; truy vấn `nguyen`, `oc`, `nguoi`, `oi`, `Đường`, `duong`, `di`. | Số kết quả lần lượt: 0, 0, 0, 1, 1, 0, 0 (khớp kết quả chạy thử; "nguyen" không khớp "Nguyễn", "oc" không khớp "Ộc"). Test này là test hồi quy để phát hiện khi SQLite đổi hành vi. | unit | `be/tests/unit/test_fts_vi_tokenizer.py` |
| T13-15 | thành công | Như T13-14 với `remove_diacritics 2`, chưa chuẩn hóa `đ→d`. | 1, 1, 1, 1, 1, 0, 0: "nguyen", "oc", "nguoi" khớp; "duong" và "di" KHÔNG khớp "Đường", "đi" (FTS5 không gập `đ`). | unit | như trên |
| T13-16 | thành công | `remove_diacritics 2` + `search_normalizer` của gói `vi` (NFC rồi `đ→d`, `Đ→D`) áp cho cả cột index và câu truy vấn; truy vấn thêm `đường`, `DUONG`, `Nguyễn` dạng NFD. | Mọi truy vấn trong T13-14 và các truy vấn thêm đều khớp 1; snippet kết quả hiển thị văn bản gốc có dấu "Đường", không phải cột đã chuẩn hóa. | unit, integration | `be/tests/integration/test_search_vi.py` |
| T13-17 | biên | Bảng trigram: tìm "hon" trong "Lâm Phong", tìm "Ph". | "hon" khớp qua trigram; chuỗi < 3 ký tự không khớp, UI gợi ý nhập dài hơn. | unit | `be/tests/unit/test_fts_trigram.py` |
| T13-18 | thành công | `GET /v1/works/{id}/search?q=lam phong` trên truyện 10 chương; xóa nội dung FTS rồi rebuild. | Kết quả có chương và `paragraph_id` nguồn, sắp theo `bm25()` tăng dần (cột tiêu đề có trọng số cao hơn); sau rebuild từ dữ liệu chuẩn, kết quả giống hệt trước khi xóa. | integration | `be/tests/integration/test_search_api_rebuild.py` |
| T13-19 | thành công | Render prompt bước `write` và `review` của gói `vi` (snapshot). | Prompt tiếng Việt có dấu đầy đủ, ví dụ tiếng Việt; schema JSON khóa tiếng Anh, giá trị mẫu tiếng Việt; manifest có id/version/checksum khớp; `job_steps` ghi prompt version. | contract | `ai/tests/contract/test_vi_prompt_snapshots.py` |
| T13-20 | thành công | Kiểm interface `LanguagePack` và chọn gói theo `works.language`. | Gói `vi` cung cấp `normalizer`, `length_counter`, `search_normalizer`, `deterministic_checks`, `prompts/`, `methods/`, `slop_list`, `genre_presets`, `ui`; pipeline `ai/workflows/longform/` không import trực tiếp `languages/vi` (kiểm import). | unit | `ai/tests/unit/test_language_pack_contract.py` |

## Kiểm tra dữ liệu sau test

- Findings từ `check` có `paragraph_id`, trích dẫn, `kind` và mức độ; không finding nào làm đổi văn bản chương (hash trước/sau bằng nhau, trừ khi pipeline sửa cục bộ có candidate riêng).
- FTS: cột index đã chuẩn hóa; văn bản gốc vẫn có dấu; rebuild cho kết quả giống hệt.
- Mọi văn bản lưu là NFC.

## Tiêu chí pass

- 100% mục trong `tests/fixtures/vi_checks/*.json` cho đúng kỳ vọng (có/không finding); tỷ lệ báo sai trên 3 chương mẫu đã duyệt (không lỗi) = 0 finding blocker.
- Bảng FTS T13-14/T13-15/T13-16 khớp từng ô; T13-16 khớp 100% truy vấn không dấu, có dấu, NFD, chữ hoa.
- 0 lần kiểm tra chính tả tự sửa văn bản.
- Trên truyện mẫu 20 chương (T07-14, T08-16): 0 lỗi xưng hô không có `address.change`, 0 trộn kiểu bỏ dấu, 0 tên ngoài canon chưa khai báo.

## Ghi chú thủ công

- Bộ so sánh model tiếng Việt (§6.6, `live`): cùng chương mẫu, chấm tự nhiên câu, đúng xưng hô, không lẫn từ Trung/Anh, đúng chính tả; lưu kết quả theo model.
- Tác giả rà danh sách cụm sáo và danh sách từ lạc thời của từng thể loại trước khi chốt ngưỡng.

## Tên mới đề xuất

- Loại finding bổ sung (danh sách §5 chưa có): `spelling`, `register` (lớp từ), `tone_mark_style`, `punctuation`.
- Bảng FTS: `chapter_fts` (`unicode61 remove_diacritics 2`, cột đã chuẩn hóa) và `chapter_fts_trigram`.
- Allowlist chính tả theo truyện: `style_profile.spelling_allowlist`; ngưỡng mật độ cụm sáo: `style_profile.slop_density_threshold`.
