# F08 — Backend

BE không chứa thuật toán ngôn ngữ; nó gọi `LanguagePack` của package AI (`writestory_ai.languages.get_pack(work.language)`) ở đúng các điểm ghi/tìm/so sánh và cung cấp API cấu hình. Quy tắc import (Arch §6): BE import AI, AI không import BE.

## Module và file

```text
be/src/writestory_be/modules/language/
  router.py      /v1/languages/*, /v1/works/{id}/text/check, /v1/evals/language-models
  schemas.py     LanguageInfo, GenrePresetDTO, SlopListDTO, TextCheckRequest/Response, NormalizeRequest/Response, ModelEvalDTO
  service.py     Đọc preset, hợp nhất cụm sáo (gói + app + truyện), chạy kiểm tra nhanh, tạo job đánh giá
  domain.py      Gộp danh sách cụm sáo, kiểm tra regex an toàn (độ dài, timeout biên dịch), ánh xạ LanguageFinding → findings
be/src/writestory_be/infrastructure/
  db/fts.py                 (F02) gọi pack.search_normalizer.for_index / for_query
  ai/language_adapter.py    Cache LanguagePack theo code; dựng CheckContext từ repositories (characters, address_rules, style_profile, state)
be/src/writestory_be/modules/chapters/service.py   (F07) gọi normalizer khi lưu working copy/revision
be/src/writestory_be/jobs/handlers/language_eval.py   Job `language_eval`
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `style_profile` (F05 tạo) | Cột F05 dùng: `tone_mark_style` (`old`=hoà \| `new`=hòa), `dialogue_style` (`dash` \| `quotes`), `dialogue_dash_char` (`–` \| `—`), `vocab_register` (`han_viet` \| `balanced` \| `thuan_viet`), `punctuation_rules` JSON (F08 định nghĩa khóa `quote_chars`: `“”`\|`""`, `ellipsis`: `…`\|`...`), `banned_phrases` JSON (`[SlopEntry]`), `voice_samples` (style anchor, F10), `revision`. F08 thêm: `slop_disabled` JSON, `anachronism_allow` JSON. (Cho phép trộn tên Hán Việt/thuần Việt là cột `characters.allow_mixed_naming` của F06) | — | F08 định nghĩa ý nghĩa và giá trị hợp lệ |
| `settings` | khóa `language.vi.slop_user` (JSON `{additions[], disabled[], version}`) | — | Cụm sáo do người dùng thêm ở mức toàn app; không tạo bảng mới |
| `provider_models` (F04) | F04 đã có `tokens_per_syllable` REAL NULL; F08 thêm `tokens_per_syllable_source` (`measured` \| `default`), `tokens_per_syllable_measured_at` | — | Plan §23.3 #4 "lưu trong `provider_models`" |
| `model_evals` | `id`, `language`, `provider_id`, `model_id`, `eval_set_version`, `prompt_version`, `metrics` JSON, `judge_model_id`, `status`, `job_id`, `created_at` | index (`language`, `model_id`, `created_at`) | Bảng mới; lưu kết quả để gợi ý model theo vai trò |
| `findings` (F10/F11) | dùng cột `source='check'`, `kind`, `severity`, `paragraph_id`, `quote`, `check_id`, `confidence`, `message_key`, `params` JSON | — | Kiểm tra F08 ghi vào đây khi chạy trong pipeline |

Migration: `be/migrations/versions/<rev>_language_pack.py` (cột `provider_models.tokens_per_syllable_source|_measured_at`, cột `style_profile` bổ sung, bảng `model_evals`). Backfill: chạy một lần `NFC` trên dữ liệu văn bản có sẵn chỉ cần khi import dữ liệu cũ (MVP chưa có dữ liệu cũ → không cần).

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/languages` | — | `[{code, name, pack_version, enabled, length_unit}]` (MVP chỉ `vi`) | — |
| GET | `/v1/languages/{code}/genre-presets` | — | `[GenrePresetDTO]` (xem ai.md) | `VALIDATION` (code không có) |
| GET | `/v1/languages/{code}/slop-list` | — | `{builtin:[SlopEntry], user:{additions, disabled}, version}` | `VALIDATION` |
| PUT | `/v1/languages/{code}/slop-list` | `{expected_version, additions:[SlopEntry], disabled:[entry_id]}` | `{version}` | `REVISION_CONFLICT` (409), `VALIDATION` (regex lỗi/quá dài) |
| GET/PUT | `/v1/works/{id}/style-profile` | (Plan §7 CRUD) `expected_revision` + trường bảng trên | `StyleProfileDTO` | `REVISION_CONFLICT`, `VALIDATION` |
| POST | `/v1/languages/{code}/normalize` | `{text, mode: "paste" \| "save", work_id?}` | `{text, changes:[{kind, count}], legacy_encoding?: {name, confidence, preview}}` | `VALIDATION` (quá 1 MB) |
| POST | `/v1/works/{id}/text/check` | `{chapter_id?, paragraphs?: [{paragraph_id, text}], checks?: [check_id]}` | `{findings:[LanguageFindingDTO], length:{units, chars}}` (không persist) | `VALIDATION` |
| POST | `/v1/evals/language-models` | `{language:"vi", models:[{provider_id, model_id}], judge?: {provider_id, model_id}, idempotency_key}` | `202 {job_id}` | `VAULT_LOCKED`, `BUDGET_EXCEEDED`, `VALIDATION` |
| GET | `/v1/evals/language-models?language=vi` | — | `[ModelEvalDTO]` mới nhất mỗi model | — |

`SlopEntry = {id, pattern, is_regex, scope: "paragraph_start" | "anywhere", max_per_1000_units?, note}`.

## Logic xử lý

Điểm áp chuẩn hóa (bảng quyết định – áp đúng chỗ, không chuẩn hóa hai lần khác nhau):

| Điểm | Hàm gọi | Gì được đổi | Người dùng có thấy thay đổi? |
|---|---|---|---|
| Lưu working copy / revision (F07) | `normalizer.normalize(text, profile, mode="save")` | NFC, bỏ ký tự zero-width/điều khiển, gộp khoảng trắng đuôi dòng | Không (tương đương chuẩn Unicode) |
| Dán vào editor | FE NFC tại chỗ; nếu FE phát hiện ký tự nghi bảng mã cũ → gọi `/normalize` `mode=paste` | NFC + đề xuất chuyển TCVN3/VNI | Có, hộp xác nhận khi đổi bảng mã |
| Candidate AI (F10) | `normalize(mode="ai_output")` trong AI trước khi trả candidate; BE gọi lại `mode="save"` khi lưu | + kiểu bỏ dấu theo `tone_mark_style`, thoại theo `dialogue_style`, dấu câu, `...`→`…` nếu cấu hình | Thấy trong candidate, không đổi văn bản người viết |
| Lưu nhân vật/bí danh/facts (F06) | `normalize(mode="save")` + sinh biến thể so khớp | NFC | Không |
| Index FTS (F02/F09) | `search_normalizer.for_index(text)` | NFC + `đ→d`, `Đ→D` | Không (cột ẩn) |
| Truy vấn tìm kiếm | `search_normalizer.for_query(q)` | Như index + escape cú pháp FTS5 | Không |
| So sánh (trích dẫn bằng chứng, tên riêng, n-gram) | `normalizer.for_compare(text)` | NFC, casefold, gộp khoảng trắng, quy kiểu bỏ dấu về một dạng | Không |

Kiểm tra nhanh `/text/check`:

1. Đọc `style_profile`, preset thể loại theo `works.genre`, canon nhân vật + bí danh, `address_rules` hiệu lực ở chương đó, quan hệ từ `StoryState` của chương trước (F09).
2. Dựng `CheckContext` (ai.md), gọi `pack.run_checks(ctx, checks)`; giới hạn 50.000 âm tiết mỗi lần (giả định để giữ p95 thấp – đo ở R2).
3. Trả finding kèm `message_key` + `params`; FE dịch bằng i18n. Không ghi DB.

Hợp nhất cụm sáo (domain.py): `builtin (gói) − app.disabled + app.additions − work.slop_disabled + work.banned_phrases`. Regex do người dùng nhập: biên dịch bằng `re` với giới hạn độ dài 200 ký tự, từ chối lookbehind lồng/backreference để tránh ReDoS; chạy quét có giới hạn thời gian mỗi đoạn.

Job `language_eval`: tạo job (F12 scheduler, không cần khóa truyện), gọi `ai.languages.vi.eval.run_model_eval(...)` qua provider limiter; mỗi model là một `job_step`; lưu `model_evals` và cập nhật `provider_models.tokens_per_syllable` (`source=measured`) trong một transaction ngắn sau mỗi model.

Quy tắc transaction: chuẩn hóa chạy **trước** khi mở transaction ghi; không giữ transaction trong lúc chạy kiểm tra hay gọi model.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `job.step` | Bắt đầu/xong đánh giá một model | `{step:"language_eval", model_id, status, metrics?}` |
| `job.state` | Job đánh giá đổi trạng thái | theo F01 |
| `finding.added` | Kiểm tra trong pipeline (F10) ghi finding | `{finding_id, kind, severity, paragraph_id, source:"check"}` |
| `usage.updated` | Sau mỗi request đánh giá | theo F14 |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| `works.language` khác `vi` | Từ chối tạo/sửa ở F05; nếu dữ liệu lạ → lỗi rõ | `VALIDATION` |
| Regex cụm sáo không biên dịch được / quá dài | Trả vị trí lỗi | `VALIDATION` |
| Hai tab sửa danh sách cụm sáo | So `expected_version` | `REVISION_CONFLICT` |
| Văn bản dán > 1 MB | FE chia nhỏ hoặc chỉ NFC phía client | `VALIDATION` |
| Phát hiện bảng mã cũ nhưng độ tin cậy thấp | Không đổi, trả `legacy_encoding.confidence` để FE hỏi | — |
| Đổi `tone_mark_style` khi truyện đã có chương | Không tự sửa chương cũ; trả cảnh báo số chương đang dùng kiểu khác và gợi ý tác vụ chuẩn hóa (sau MVP) | — |
| Đánh giá model khi vault khóa | Job `waiting_slot` lý do `VAULT_LOCKED` (Plan §23.2 #7) | `VAULT_LOCKED` |

## Việc cần làm

- [ ] `language_adapter.py`: cache pack, dựng `CheckContext` từ repositories.
- [ ] Gọi `normalize(mode="save")` trong service lưu working copy/revision, nhân vật, facts (phối hợp F06, F07).
- [ ] `fts.py`: dùng `search_normalizer` cho cả index và query (phối hợp F02, F09).
- [ ] Router + schemas cho 9 endpoint trên; đăng ký vào OpenAPI.
- [ ] Domain hợp nhất cụm sáo + kiểm tra regex an toàn.
- [ ] Migration `provider_models.tokens_per_syllable_source|_measured_at`, cột `style_profile` bổ sung, `model_evals`.
- [ ] Job handler `language_eval` + ghi usage.
- [ ] Ánh xạ `LanguageFinding` → bảng `findings` (dùng chung với F10).
- [ ] `message` lỗi API lấy từ `pack.messages` (Plan §23.1.D).

### P230 đã triển khai

- [x] API preset thể loại, danh sách cụm sáo có revision, chuẩn hóa và kiểm tra văn bản; finding giữ `check_id`, `confidence`, `message_key`, `params`.
- [x] Điểm lưu working copy gọi `LanguagePack` để chuẩn hóa NFC; kiểm tra có thể nhận đoạn văn trực tiếp hoặc đọc chương hiện tại.
- [x] Gộp cụm sáo gói/app/truyện, kiểm tra regex đầu vào; test unit, integration và OpenAPI cho phạm vi P230.

Các endpoint đánh giá model và lưu finding vào pipeline tiếp tục ở prompt phụ thuộc tương ứng; F08 vẫn chưa nghiệm thu tổng thể.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Hợp nhất cụm sáo theo thứ tự ưu tiên; từ chối regex nguy hiểm | `be/tests/unit/language/test_slop_merge.py` |
| unit | Bảng điểm áp chuẩn hóa: mỗi mode gọi đúng hàm | `be/tests/unit/language/test_normalize_points.py` |
| integration | Lưu chương chứa chữ dạng NFD → DB chứa NFC; FTS tìm `duong` ra `Đường` | `be/tests/integration/language/test_save_and_search.py` |
| integration | `/text/check` trên truyện mẫu trả finding có `paragraph_id` đúng | `be/tests/integration/language/test_text_check_api.py` |
| integration | Job `language_eval` với mock provider ghi `model_evals` và `tokens_per_syllable` | `be/tests/integration/language/test_language_eval_job.py` |
| contract | Schema OpenAPI cho DTO ngôn ngữ ổn định | `be/tests/contract/test_openapi_language.py` |

Luồng: [T13](../../tests/flows/T13-kiem-tra-tieng-viet.md).

## Tên mới đề xuất

- Module `be/src/writestory_be/modules/language/`; `infrastructure/ai/language_adapter.py`; `jobs/handlers/language_eval.py`.
- API: `GET /v1/languages`, `GET /v1/languages/{code}/genre-presets`, `GET|PUT /v1/languages/{code}/slop-list`, `POST /v1/languages/{code}/normalize`, `POST /v1/works/{id}/text/check`, `POST|GET /v1/evals/language-models`.
- Bảng `model_evals`; cột `provider_models.tokens_per_syllable_source`, `tokens_per_syllable_measured_at` (`tokens_per_syllable` đã có ở F04).
- Cột `style_profile`: `slop_disabled`, `anachronism_allow`; cột `characters.is_transmigrator`; khóa `punctuation_rules.quote_chars`, `punctuation_rules.ellipsis` (các cột còn lại dùng tên F05).
- Khóa settings `language.vi.slop_user`; job type `language_eval`.
- Cột `findings`: `check_id`, `confidence`, `message_key`, `params`.
