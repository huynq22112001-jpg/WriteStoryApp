# F08 — Gói ngôn ngữ `vi`

Giai đoạn: R2 (giao diện `LanguagePack` và chuẩn hóa NFC cần có từ R1 vì F02/F07 dùng). Trạng thái: planned.

## Mục tiêu

Mọi xử lý phụ thuộc ngôn ngữ (chuẩn hóa, đếm độ dài, chuẩn hóa tìm kiếm, kiểm tra xác định, prompt, phương pháp, cụm sáo, preset thể loại, chuỗi giao diện) đi qua một interface `LanguagePack` chọn theo `works.language`. Sau tính năng này, tác giả viết truyện tiếng Việt được: văn bản luôn ở NFC với một kiểu bỏ dấu thống nhất, độ dài đo bằng âm tiết, tìm kiếm có/không dấu đều ra, và nhận cảnh báo xưng hô, tên riêng, lớp từ, cụm sáo, chính tả có trích dẫn theo `paragraph_id`.

## Phạm vi

- Trong phạm vi:
  - Interface `LanguagePack` + registry trong `ai/src/writestory_ai/languages/` (Arch §6); pipeline §6.2 không chứa logic riêng của tiếng Việt.
  - Gói `vi` theo Plan §6.6: `normalizer` (NFC, kiểu bỏ dấu `hoà`/`hòa`, thoại và dấu câu, phát hiện bảng mã cũ khi dán), `length_counter` (âm tiết), `search_normalizer` (NFC + `đ→d`, phần bỏ dấu do FTS5 `remove_diacritics 2`), `deterministic_checks` (xưng hô, tên riêng, lớp từ, cụm sáo, chính tả hỏi/ngã + Telex sót, trộn kiểu bỏ dấu, quy ước thoại).
  - Prompt Jinja2 sandbox + manifest id/version/checksum (Plan §23.3 #8), phương pháp sáng tác tiếng Việt cho MVP, `slop_list.txt`, `genres.json` cho 8 thể loại: tiên hiệp, kiếm hiệp, huyền huyễn, ngôn tình, đô thị, cung đấu, xuyên không, trinh thám.
  - Bộ đánh giá chất lượng tiếng Việt của model (Plan §6.6 "Chọn model", §23.3 #9 bản nhỏ) và đo tỷ lệ token/âm tiết theo model (§23.3 #4).
  - BE: điểm áp chuẩn hóa khi lưu/dán/tìm, API danh sách cụm sáo, preset thể loại, kiểm tra nhanh một đoạn văn, chạy đánh giá model.
  - FE: khởi tạo i18next (chỉ resource `vi`), UI sửa style profile và danh sách cụm sáo, hiển thị finding tiếng Việt, hiển thị âm tiết/ký tự.
- Ngoài phạm vi:
  - Gói ngôn ngữ khác (en, zh) – sau MVP; không port nhánh zh/en của InkOS (Plan §14.2).
  - Tự sửa chính tả (chỉ cảnh báo – Plan §6.6). Sửa cụm sáo bằng LLM là bước repair của F10.
  - CRUD preset thể loại do người dùng tạo (NEW06, R3); MVP chỉ đọc preset đóng gói.
  - Đủ 20 nhóm phương pháp §15.16: MVP chỉ cần nhóm phục vụ truyện dài (viết dài, review, deslop); các nhóm khác theo giai đoạn R3–R6.
  - Bảng `address_rules`, `characters`, `style_profile` – dữ liệu do F05/F06 sở hữu; F08 chỉ định nghĩa trường mà kiểm tra cần đọc.

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F02 | FTS5 `unicode61 remove_diacritics 2`, writer queue, cột tìm kiếm đã chuẩn hóa |
| F05 (song song) | `works.language`, `works.genre`, `style_profile` dùng preset và lựa chọn của gói |
| F06 (song song) | `characters.aliases`, `address_rules` là đầu vào kiểm tra tên riêng/xưng hô |
| F04 | Bộ đánh giá model cần provider/model; `provider_models` lưu tỷ lệ token/âm tiết |
| F07 | `paragraph_id` để neo finding; editor gọi chuẩn hóa khi dán |

Tính năng dùng F08: F09 (search normalizer, đếm token ước lượng), F10 (kiểm tra bước 5, prompt, chuẩn hóa candidate), F11 (hiển thị finding), F13 (xuất giữ NFC).

## Nguồn thiết kế

- Plan §6.6 (toàn bộ), §6.5 (độ dài theo âm tiết), §5 (`style_profile`, `address_rules`, `characters`, ghi chú FTS), §2 dòng Search MVP, §6.2 bước 5, §9 Giai đoạn 4 (0 lỗi xưng hô, không trộn kiểu bỏ dấu), §23.1.D (`message` lấy từ gói ngôn ngữ), §23.3 #4, #8, #9.
- Arch §6 (`languages/base.py`, `languages/vi/...`, `evaluators/deterministic.py`), §4 FE `shared/`.
- UI §1 nguyên tắc 5, §3 dòng i18n/font, §5.7 wizard (style profile), §9 `shared/i18n/vi/*.json`.
- Review §7.3 (FTS5 đã chạy thử: `remove_diacritics 2`, `đ` không gập), §6 (lớp 1 prompt chứa quy tắc tiếng Việt + cụm cấm).
- Nghiên cứu: Antislop ([arxiv 2510.15061](https://arxiv.org/abs/2510.15061)) – danh sách cụm cấm + sửa sau sinh.
- Mã Plan §15: LNG10 (độ dài theo đơn vị gói ngôn ngữ), NEW02 (kiến trúc gói ngôn ngữ), MEM04 (FTS dùng chung).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Module `language`: điểm áp chuẩn hóa (lưu, dán, import, tìm kiếm, so sánh), API ngôn ngữ/preset/cụm sáo/kiểm tra nhanh/đánh giá model, bảng kết quả đánh giá, lưu finding kiểm tra |
| FE | [fe.md](./fe.md) | i18next chỉ `vi`, kiểu khóa có type, ánh xạ mã lỗi; editor style profile, editor cụm sáo, hiển thị finding tiếng Việt, đếm âm tiết phía client theo bộ golden chung |
| AI | [ai.md](./ai.md) | Interface `LanguagePack`, gói `vi`: thuật toán chuẩn hóa, đếm âm tiết, search, 7 nhóm kiểm tra, prompt Jinja2 sandbox + manifest, preset thể loại, bộ đánh giá model tiếng Việt |

## Tiêu chí hoàn thành

- [ ] `get_pack("vi")` trả gói đầy đủ 9 thành phần của Plan §6.6; `get_pack("en")` trả lỗi `VALIDATION` rõ ràng (MVP chỉ `vi`).
- [ ] Mọi văn bản ghi vào DB qua F07/F10/F06 đã NFC (test quét DB fixture: 0 chuỗi khác dạng NFC).
- [ ] Tìm `nguyen`, `oc`, `duong`, `Đường`, `duong di` đều ra câu "Đường đi Nguyễn Văn Ộc" (lặp lại bảng Review §7.3 với `đ→d`).
- [ ] Đếm âm tiết khớp 100% bộ golden `tests/fixtures/language/vi/length_cases.json` ở cả Python và TypeScript.
- [ ] Bộ kiểm tra tiếng Việt bắt được mọi lỗi cài sẵn trong `tests/fixtures/state/` và truyện mẫu (xưng hô, tên ngoài canon, từ lạc thời, cụm sáo, `tieengs`/`ddi`, trộn `hoà`/`hòa`) với trích dẫn đúng `paragraph_id`.
- [ ] Candidate AI được chuẩn hóa về kiểu bỏ dấu của `style_profile`; truyện mẫu 20 chương không trộn hai kiểu (chỉ số Plan §9 Giai đoạn 4).
- [ ] Prompt render có snapshot test; checksum manifest khớp file; `prompt_version` ghi vào `job_steps`.
- [ ] Bộ đánh giá model chạy được với mock provider (contract) và với provider thật khi bật `live`; kết quả lưu và hiển thị ở Cài đặt → Vai trò.
- [ ] FE không có chuỗi hiển thị cứng ngoài `t()` (lint pass).
- [ ] Test luồng pass: [T13](../../tests/flows/T13-kiem-tra-tieng-viet.md); phần kiểm tra tiếng Việt trong [T05](../../tests/flows/T05-viet-mot-chuong.md) và [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md).

## Rủi ro và câu hỏi mở

- **Xác định người nói trong thoại** bằng luật (không LLM) có thể sai; thiết kế cho kiểm tra xưng hô trả `confidence` và chỉ chặn khi độ tin cậy cao, còn lại chuyển reviewer LLM xác nhận (ai.md). Cần đo tỷ lệ báo nhầm trên truyện mẫu.
- **Từ điển âm tiết hợp lệ, danh sách Hán Việt thông dụng, cặp hỏi/ngã**: cần nguồn có giấy phép tương thích; chưa chọn. Kiểm tra hỏi/ngã chỉ bắt được cặp đã liệt kê (cả hai âm tiết đều hợp lệ, ví dụ `sửa`/`sữa`), không phải bộ kiểm tra chính tả đầy đủ.
- **Tỷ lệ token/âm tiết** khác theo tokenizer; giá trị mặc định trước khi đo là giả định cấu hình, không phải số đo.
- Chuyển đổi bảng mã cũ (TCVN3/VNI-Windows) dễ nhận nhầm; chỉ đề xuất chuyển khi phát hiện chắc chắn, người dùng xác nhận.
- `xuyên không` cho phép từ hiện đại trong độc thoại của nhân vật xuyên tới: luật lớp từ cần ngoại lệ theo nhân vật (`characters` cần cờ, chưa có trong Plan – xem "Tên mới đề xuất" ở ai.md).
- Plan §6.6 nói cụm sáo "quét regex rồi sửa cục bộ", nhưng §6.2 bước 10 chỉ sửa khi có `blocker`/seam fail; cách gộp được chốt ở F10 ai.md.
