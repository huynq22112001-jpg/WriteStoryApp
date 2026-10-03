# F08 — AI

Phần chính của F08. Gói ngôn ngữ là code + tài nguyên đóng gói trong package AI, đọc qua `importlib.resources` (Arch §6), không phụ thuộc BE.

## Module và file

```text
ai/src/writestory_ai/languages/
  base.py                    LanguagePack (Protocol) + các contract bên dưới
  registry.py                get_pack(code) -> LanguagePack; MVP chỉ đăng ký "vi"
  vi/
    __init__.py              VI_PACK
    normalizer.py            NFC, kiểu bỏ dấu, thoại, dấu câu, for_compare
    accents.py               Bảng đặt dấu oa/oe/uy kiểu cũ ↔ mới
    legacy_encodings.py      Phát hiện + chuyển TCVN3 (ABC), VNI-Windows
    length.py                Đếm âm tiết, ký tự
    search.py                for_index / for_query (NFC + đ→d, escape FTS5)
    names.py                 extract_name_candidates, name_variants
    telex.py                 telex_decode / vni_decode cho gợi ý chính tả
    checks.py                Đăng ký 7 kiểm tra; mỗi kiểm tra một hàm thuần
    eval.py                  Bộ đánh giá model tiếng Việt
    slop_list.txt            Cụm sáo có sẵn (định dạng ở dưới)
    genres.json              8 preset thể loại
    messages.json            Thông báo lỗi API/finding (Plan §23.1.D)
    data/
      syllables.txt          Âm tiết tiếng Việt hợp lệ (có thanh)
      hoi_nga_pairs.tsv      Cặp sai → đúng (hỏi/ngã) ở mức cụm 2 âm tiết
      pronouns.json          Từ xưng/gọi + vai trò (xưng/gọi/cả hai) + dấu hiệu ngôi ba
      speech_verbs.txt       nói, hỏi, đáp, quát, cười, thì thầm, lên tiếng…
      common_capitalized.txt Từ hay viết hoa nhưng không phải tên (Trời, Phật…)
      han_viet_common.txt    Từ ghép Hán Việt thông dụng (đo mật độ)
      anachronisms/co_trang.txt   Từ hiện đại lạc thời (điện thoại, ô tô, OK…)
      foreign_allowlist.txt  Từ ngoại được phép trong truyện hiện đại
    prompts/
      manifest.json
      common/*.j2  longform/*.j2  eval/*.j2
    methods/
      viet_truyen_dai.md  review_truyen.md  khu_sao.md
  prompt_env.py              ImmutableSandboxedEnvironment + loader theo manifest
ai/src/writestory_ai/evaluators/deterministic.py   (F10) gọi pack.deterministic_checks
```

## Contract (Pydantic)

```text
LanguagePack (Protocol):
  code: str ("vi"); pack_version: str; length_unit: Literal["syllable","word","char"]
  normalizer: TextNormalizer
  length_counter: LengthCounter
  search_normalizer: SearchNormalizer
  deterministic_checks: list[DeterministicCheck]
  names: NameTools
  prompts: PromptRegistry
  methods: MethodRegistry
  slop_list: list[SlopEntry]
  genre_presets: dict[str, GenrePreset]
  messages: dict[str, str]
  ui_namespace_root: str = "fe/src/shared/i18n/vi"   (chỉ là tham chiếu; resource UI nằm ở FE)

TextNormalizer.normalize(text, profile: StyleProfileView, mode: "save"|"paste"|"ai_output") -> NormalizeResult
NormalizeResult: text, changes: list[{kind: "nfc"|"zero_width"|"tone_mark_style"|"dialogue"|"punct"|"ellipsis"|"legacy_encoding", count}],
                 legacy_encoding: {name: "tcvn3"|"vni_win", confidence: float, preview: str} | None
TextNormalizer.for_compare(text) -> str
LengthCounter.count(text) -> LengthStats{units:int, unit:"syllable", chars:int, chars_no_spaces:int, paragraphs:int}
SearchNormalizer.for_index(text) -> str ; for_query(q, mode: "and"|"phrase"|"prefix") -> str
NameTools.extract_name_candidates(paragraphs) -> list[NameMention{text, paragraph_id, start, end, sentence_start: bool}]
NameTools.name_variants(name, kind) -> set[str]   (NFC, không dấu, viết thường)

StyleProfileView: tone_mark_style, dialogue_style, dialogue_dash_char, quote_chars, ellipsis (hai khóa lấy từ
                  style_profile.punctuation_rules), vocab_register, slop (đã hợp nhất ở BE),
                  anachronism_allow                     (tên cột theo F05; xem be.md)
CheckContext:
  work_id, chapter_no, genre_preset: GenrePreset, profile: StyleProfileView
  paragraphs: list[{paragraph_id, text}]                 (văn bản đã NFC)
  canon_characters: list[{id, name, aliases:[{text, kind:"han_viet"|"thuan_viet"|"nickname"|"title"|"unaccented", search}],
                          allow_mixed_naming, status, is_transmigrator}]      (cột theo F06 `characters`)
  canon_locations: list[{id, name, aliases}]                                  (từ StoryState.locations, F09)
  address_rules: list[{speaker_id, listener_id, self_term, address_term, from_chapter, until_chapter|None}]
                 (cột theo F06; nhiều dòng cùng cặp và cùng giai đoạn được gộp thành tập từ hợp lệ)
  relationship_events: list[{a, b, chapter_no, op:"relationship.set"|"address.change"}]   (từ StateDelta chương này + state, F09)
  present_character_ids: list[str]                         (ending_state N-1 + nhắc tên trong chương)
  declared_new_names: list[str]                            (plan.new_characters + new_entities của settle, F10)
LanguageFinding:
  check_id ("vi.address" …), kind (address|name|anachronism|slop|spelling|tone_mark_style|dialogue|lexicon),
  severity: "blocker"|"major"|"minor", confidence: "high"|"medium"|"low",
  paragraph_id, start, end, quote (≤ 200 ký tự), message_key, params: dict, suggestion: str|None,
  needs_confirmation: bool   (true → reviewer LLM F10 xác nhận)
GenrePreset: id, name, era: "co_trang"|"hien_dai"|"hon_hop", address_presets[{label, self_term, address_term, note}],
  default_dialogue_style, default_vocab_register, anachronism_lists[], han_viet_max_per_1000|None,
  extra_slop[], length_default{min, max}, recommended_methods[], notes
SlopEntry: id, pattern, is_regex, scope: "paragraph_start"|"anywhere", max_per_1000_units|None, note
```

## Workflow

### 1. Chuẩn hóa (`normalizer.py`)

1. `unicodedata.normalize("NFC")`; bỏ U+200B–U+200D, U+FEFF, U+00AD; thay NBSP bằng khoảng trắng thường; chuẩn xuống dòng `\r\n`→`\n`.
2. `mode="paste"`: chạy `legacy_encodings.detect(text)`: tính tỷ lệ âm tiết hợp lệ trước và sau khi giả định TCVN3/VNI; `confidence = valid_after − valid_before`; chỉ trả đề xuất khi vượt ngưỡng cấu hình (giả định, đo trên mẫu ở R2). Không tự đổi.
3. `mode="ai_output"` thêm:
   - Kiểu bỏ dấu (`accents.py`): chỉ với vần `oa`, `oe`, `uy` **cuối âm tiết, không có phụ âm cuối**, và không đứng sau `q` (`quý`, `quả` không đổi). Kiểu cũ đặt dấu trên nguyên âm đầu (`hoà`, `khoẻ`, `thuỷ`), kiểu mới trên nguyên âm sau (`hòa`, `khỏe`, `thủy`). Có phụ âm cuối (`hoàng`, `thuyền`) giống nhau ở hai kiểu. Bảng 3 vần × 5 thanh × hoa/thường.
   - Thoại: `dialogue_style="dash"` → đoạn mở bằng `-`, `–`, `—` + khoảng trắng đổi về `dialogue_dash_char`; `"quotes"` → cặp `"` thẳng đổi sang `quote_chars`. Không chuyển dash ↔ quotes (dễ sai), chỉ báo `vi.dialogue`.
   - Dấu câu: bỏ khoảng trắng trước `, . ; : ! ? … ) ”`; một khoảng trắng sau dấu câu khi theo sau là chữ; giữ `3,5`, `10:30`; `...`→`…` nếu `ellipsis="…"`; gộp khoảng trắng.
4. `for_compare`: NFC → casefold → gộp khoảng trắng → quy `oa/oe/uy` về kiểu mới. Dùng cho đối chiếu trích dẫn (F09), tên riêng, n-gram (F10).

### 2. Đếm độ dài (`length.py`) – spec dùng chung với FE

1. NFC; tách theo khoảng trắng Unicode.
2. Mỗi token: bỏ ký tự dấu câu/ký hiệu ở hai đầu (Unicode category `P*`, `S*`); rỗng → bỏ (gạch thoại, `…` đứng riêng không tính).
3. Token chứa `-` hoặc `/` giữa hai chữ cái (`ô-tô`, `và/hoặc`) → tách, mỗi phần không rỗng là một âm tiết.
4. Số (`2024`, `3,5`) tính 1. Ký tự CJK liền nhau: mỗi ký tự tính 1 (hiếm, để không đếm sai khi model lẫn chữ Hán).
5. `chars` = số code point sau NFC trừ `\n`; `chars_no_spaces` bỏ mọi khoảng trắng.
Bộ golden `tests/fixtures/language/vi/length_cases.json` (`{text, units, chars}`) chạy ở cả pytest và Vitest.

### 3. Tìm kiếm (`search.py`)

- `for_index`: NFC → `đ→d`, `Đ→D`. Phần bỏ dấu và hạ chữ do tokenizer `unicode61 remove_diacritics 2` làm (Plan §5; Review §7.3 đã chạy thử).
- `for_query`: như trên; tách term, bao mỗi term bằng `"…"` (escape `"` thành `""`) để chặn cú pháp FTS5 do người dùng nhập; `mode="prefix"` thêm `*`; `mode="phrase"` giữ thứ tự. Term < 3 ký tự không gửi sang bảng trigram.

### 4. Kiểm tra xác định (`checks.py`)

Mỗi kiểm tra là hàm thuần `(CheckContext) -> list[LanguageFinding]`, không I/O, chạy < 1 giây cho chương mục tiêu (giả định cần đo).

| `check_id` | Thuật toán | Mức mặc định |
|---|---|---|
| `vi.address` | (1) Tách lời thoại: đoạn mở bằng gạch thoại (phần chen " – … – " là lời dẫn) hoặc trong `quote_chars`. (2) Xác định người nói: lời dẫn cùng đoạn có tên/bí danh canon + động từ trong `speech_verbs.txt` hoặc `Tên:` → `high`; xen kẽ hai người khi cảnh chỉ có 2 nhân vật → `medium`; còn lại bỏ qua. (3) Người nghe: hô ngữ đầu/cuối câu thoại khớp tên/bí danh hoặc từ gọi chỉ thuộc một luật → `high`; cảnh 2 người → `medium`. (4) So khớp từ trong `pronouns.json` (cụm dài trước, ranh giới âm tiết; bỏ dạng ngôi ba như "ông ấy", "bà ta", "cha ta"). (5) Từ thuộc lexicon nhưng không thuộc tập `self_term ∪ address_term` của các luật hiệu lực (speaker→listener ở `chapter_no`) → vi phạm. (6) Có `address.change` cho cặp này trong `relationship_events` với từ mới khớp → hợp lệ; chỉ có `relationship.set` cùng chương → `minor` "cần cập nhật quy tắc xưng hô" | `high`+`high` → `blocker`; có `medium` → `major` + `needs_confirmation`; không có luật cho cặp → không báo |
| `vi.name_variant` | Từ `extract_name_candidates`: chuỗi 1–4 âm tiết viết hoa liên tiếp, bỏ đầu câu nếu chỉ 1 âm tiết, bỏ `common_capitalized.txt`. So với biến thể canon: khớp dạng không dấu nhưng khác dấu (`Lam Phong` vs `Lâm Phong`) → sai dấu; cùng chương gọi một nhân vật bằng cả bí danh `han_viet` và `thuan_viet` khi `allow_mixed_naming=false` (cột F06 của nhân vật) → trộn tên. Tên không có trong canon trả về cho kiểm tra chung `name.unknown` của `evaluators/deterministic.py` (F10) | sai dấu: `major`; trộn tên: `major` |
| `vi.lexicon` | (a) `era=co_trang`: khớp `anachronisms/*.txt` + từ Latin không phải âm tiết hợp lệ và không trong `foreign_allowlist`; bỏ qua mục trong `anachronism_allow`, bỏ qua thoại/độc thoại của nhân vật `is_transmigrator` (xuyên không). (b) Truyện hiện đại + `vocab_register="thuan_viet"`: mật độ từ `han_viet_common.txt`/1.000 âm tiết > `han_viet_max_per_1000` → một finding cấp chương kèm 5 từ nhiều nhất | (a) `major`; (b) `minor` |
| `vi.slop` | Danh sách hợp nhất (gói + app + truyện, BE gộp). `scope=paragraph_start`: khớp đầu đoạn sau gạch thoại/khoảng trắng → finding mỗi đoạn. `anywhere` có `max_per_1000_units`: đếm toàn chương, vượt ngưỡng → một finding liệt kê các đoạn | `major` |
| `vi.spelling` | Token chữ thường không phải tên/viết tắt/số: không có trong `syllables.txt` → thử `telex_decode` (`tieengs`→`tiếng`, `ddi`→`đi`) và `vni_decode` (`tie6ng1`); kết quả hợp lệ → `telex`/`vni` kèm gợi ý; không → `invalid`. Cụm 2 âm tiết khớp `hoi_nga_pairs.tsv` (`sữa chữa`→`sửa chữa`) → gợi ý | `minor` (chỉ cảnh báo, không tự sửa – Plan §6.6) |
| `vi.accent_mix` | Đếm âm tiết `oa/oe/uy` theo hai kiểu; kiểu khác `tone_mark_style` xuất hiện → một finding cấp chương, `params.count`, tối đa 5 đoạn ví dụ | `major` (văn bản AI đã được chuẩn hóa nên chỉ gặp ở văn bản người viết) |
| `vi.dialogue` | Đoạn thoại dùng kiểu khác `dialogue_style`, hoặc trộn `–`/`—`, hoặc ngoặc kép không cân | `minor` |

Mức độ do host gán theo bảng này (F10 không để LLM tự nâng/hạ). Finding `needs_confirmation=true` được đưa vào input reviewer F10; reviewer xác nhận → giữ mức, bác → `dismissed` kèm lý do.

### 5. Prompt (`prompt_env.py`, `prompts/manifest.json`)

- `ImmutableSandboxedEnvironment(undefined=StrictUndefined, autoescape=False, trim_blocks=True, lstrip_blocks=True)`. Loader chỉ đọc file có trong manifest qua `importlib.resources`. Văn bản truyện/chỉ dẫn của người dùng **chỉ** là biến, không bao giờ là nguồn template (chặn template injection).
- Filter cho phép: `paragraphs` (render `[p:<id>] nội dung`, Plan §23.1.B), `units` (số âm tiết), `bullets`, `tojson`.
- Manifest mỗi mục: `{id, version, file, sha256, role, layer, output_schema|null, variables[]}`. Khởi động kiểm checksum; lệch → lỗi build/test. Đổi nội dung bắt buộc tăng `version` (test CI so `sha256` với snapshot manifest).
- `prompt_version` = `"<id>@<version>#<sha256[:8]>"`, ghi vào `job_steps` và `context_traces` (F09).
- Mọi prompt viết bằng tiếng Việt, ví dụ tiếng Việt, khóa JSON tiếng Anh, giá trị văn bản tiếng Việt (Plan §6.6). Không dịch máy prompt InkOS; không sao chép prompt AGPL (Plan §12).

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| `common.system` | Nền chung: vai trò trợ lý sáng tác, an toàn dữ liệu, ngôn ngữ đầu ra tiếng Việt | 1 | — |
| `common.vi_rules` | Quy tắc tiếng Việt: NFC, kiểu bỏ dấu, thoại, dấu câu, đơn vị âm tiết | 1 | — |
| `common.slop_rules` | Danh sách cụm sáo có sẵn của gói (phần toàn app; bổ sung theo truyện nằm ở lớp 2) | 1 | — |
| `common.method` | Nhúng phương pháp (`methods/*.md`) theo vai trò | 1 | — |
| `common.json_fix` | Yêu cầu sửa JSON sai schema (một lần, Plan §23.3 #2) | 4 | JSON theo schema gốc |
| `longform.bible` | Story bible, dàn ý tổng, nhân vật chính, xưng hô, style anchor, cụm sáo riêng truyện | 2 | — |
| `longform.chapter_context` | State, summaries, hooks, handoff, `tail_text`, plan | 3 | — |
| `longform.planner`, `longform.writer`, `longform.writer_continue`, `longform.settler`, `longform.validator`, `longform.seam_check`, `longform.reviewer`, `longform.repair`, `longform.summary_chapter`, `longform.summary_arc`, `longform.synopsis`, `longform.outline_review` | Chỉ dẫn từng bước (đặc tả nội dung ở F09/F10) | 4 | Văn bản hoặc JSON (F10) |
| `eval.vi_writer_case`, `eval.vi_judge` | Bộ đánh giá model | 4 | Văn bản / JSON điểm |

## Model, effort, giới hạn

- Kiểm tra xác định và chuẩn hóa: không gọi model.
- Đánh giá model: sinh văn bằng model cần đo với cấu hình vai trò Viết (effort theo lựa chọn người dùng, ghim trong job); giám khảo dùng vai trò Mối nối & Review, effort `medium` (Plan §7.1); nên khác model đang đo để giảm thiên lệch tự chấm (UI cảnh báo khi trùng).
- Structured output của giám khảo: schema `VietJudgeScore{naturalness 1–5, genre_voice 1–5, coherence 1–5, issues[{quote, note}]}`; fallback theo Plan §23.3 #2.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal (đánh giá) | Ghi `metrics.refused=true` cho ca đó, không retry lặp; vẫn tính các ca còn lại |
| Bị cắt `max_tokens` | Ghi `truncated=true`; không viết tiếp trong đánh giá (giữ điều kiện so sánh như nhau) |
| JSON không hợp lệ (giám khảo) | `common.json_fix` một lần → Pydantic → vẫn lỗi: ca đó `judge=null` |
| Văn bản có chữ Hán/Cyrillic | `length` đếm từng ký tự CJK; `vi.lexicon` báo từ ngoại; đánh giá tính `foreign_script_count` |
| Tên riêng trùng từ thường ("Phong", "Lan") | Chỉ coi là tên khi viết hoa giữa câu; đầu câu 1 âm tiết bỏ qua |
| Truyện không có `address_rules` | `vi.address` không báo gì (không suy luận luật) |
| Âm tiết hợp lệ nhưng sai nghĩa (`dành`/`giành`) | Ngoài khả năng kiểm tra xác định; không báo |
| Regex người dùng chạy quá lâu | Giới hạn thời gian mỗi đoạn; quá hạn → bỏ mục đó, ghi finding `minor` "mẫu cụm sáo bị bỏ qua" |

## Đánh giá

- Bộ `ai/tests/fixtures/eval_vi/` (phiên bản `eval_set_version`): ít nhất 2 thể loại theo Plan §9 Giai đoạn 4 (tiên hiệp/kiếm hiệp; ngôn tình hoặc đô thị). Mỗi ca: nền rút gọn, nhân vật + bí danh, `address_rules`, `tail_text` mẫu, chỉ dẫn viết tiếp một cảnh có ≥ 3 nhân vật đối thoại.
- Chỉ số mỗi model (tính bằng chính các kiểm tra của gói): `address_violations` (high+medium), `invalid_syllable_rate`, `foreign_script_count`, `english_word_rate`, `slop_per_1000`, `length_ratio`, `tokens_per_syllable` (= output tokens provider trả / âm tiết; không suy diễn khi thiếu usage), điểm giám khảo.
- Gợi ý vai trò: model qua cổng xác định (0 vi phạm xưng hô, tỷ lệ âm tiết sai dưới ngưỡng cấu hình) rồi xếp theo điểm giám khảo; chỉ hiển thị, không tự đổi cấu hình. Không công bố số so sánh chung; kết quả phụ thuộc truyện mẫu và thời điểm.
- Chạy lại khi đổi prompt/model (Plan §23.3 #9); bản contract dùng mock provider với `scripted_outputs` có lỗi cài sẵn để kiểm bộ đo.

## Việc cần làm

- [ ] `base.py`, `registry.py`: Protocol + contract; test conformance cho mọi pack đăng ký.
- [ ] `normalizer.py` + `accents.py` + bảng 3 vần × 5 thanh × hoa/thường.
- [ ] `legacy_encodings.py` (TCVN3, VNI-Windows) với ngưỡng tin cậy.
- [ ] `length.py` + golden JSON chung FE/AI.
- [ ] `search.py` + test lặp lại bảng Review §7.3 trên SQLite thật.
- [ ] `names.py`, `telex.py`.
- [x] 7 kiểm tra trong `checks.py`, mỗi kiểm tra có fixture dương/âm.
- [ ] Chọn nguồn `syllables.txt`, `han_viet_common.txt`, `hoi_nga_pairs.tsv` có giấy phép phù hợp; ghi nguồn trong file.
- [x] Soạn `slop_list.txt` khởi tạo (ví dụ Plan §6.6: mở đoạn "Trong khoảnh khắc ấy", mật độ "không khỏi", "một cách") – tác giả bổ sung được.
- [x] `genres.json` cho 8 thể loại (xưng hô gợi ý, lớp từ, thoại mặc định); không ghi số liệu chưa đo.
- [ ] `prompt_env.py`, `manifest.json`, test checksum + snapshot render.
- [ ] `methods/` cho truyện dài: viết dài, review, khử sáo.
- [ ] `eval.py` + bộ ca + schema giám khảo.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | NFC, zero-width, kiểu bỏ dấu hai chiều (`hoà`↔`hòa`, `quý` không đổi, `hoàng` không đổi) | `ai/tests/unit/languages/vi/test_normalizer.py` |
| unit | Phát hiện TCVN3/VNI và không báo nhầm văn bản Unicode chuẩn | `ai/tests/unit/languages/vi/test_legacy_encodings.py` |
| unit | Golden đếm âm tiết | `ai/tests/unit/languages/vi/test_length.py` |
| unit | `for_query` escape cú pháp FTS5; FTS5 thật tìm `duong`/`nguyen`/`oc` | `ai/tests/unit/languages/vi/test_search.py` |
| unit | Mỗi `check_id` với fixture dương/âm, kể cả `address.change` hợp lệ và xuyên không | `ai/tests/unit/languages/vi/test_checks_*.py` |
| unit | Manifest checksum, StrictUndefined, chặn truy cập thuộc tính nguy hiểm trong sandbox | `ai/tests/unit/languages/vi/test_prompt_env.py` |
| unit | Snapshot prompt đã render với biến mẫu | `ai/tests/unit/languages/vi/test_prompt_snapshots.py` (+ `ai/tests/snapshots/prompts/`) |
| contract (mock provider) | `eval.py`: refusal, cắt output, JSON giám khảo hỏng → chỉ số đúng | `ai/tests/contract/languages/test_vi_eval.py` |

Luồng: [T13](../../tests/flows/T13-kiem-tra-tieng-viet.md), [T15](../../tests/flows/T15-loi-provider.md) (phần đánh giá).

## Tên mới đề xuất

- File/thư mục: `languages/registry.py`, `languages/vi/accents.py`, `legacy_encodings.py`, `names.py`, `telex.py`, `eval.py`, `messages.json`, `data/*`, `prompt_env.py`, `methods/viet_truyen_dai.md`, `review_truyen.md`, `khu_sao.md`, `ai/tests/fixtures/eval_vi/`.
- Contract: `NormalizeResult`, `LengthStats`, `StyleProfileView`, `CheckContext`, `LanguageFinding`, `GenrePreset`, `SlopEntry`, `NameMention`, `VietJudgeScore`, `TextNormalizer`, `LengthCounter`, `SearchNormalizer`, `NameTools`, `PromptRegistry`, `MethodRegistry`.
- `check_id`: `vi.address`, `vi.name_variant`, `vi.lexicon`, `vi.slop`, `vi.spelling`, `vi.accent_mix`, `vi.dialogue`.
- Loại finding mới ngoài danh sách Plan §5 (`fact/timeline/name/address/seam/POV/slop/craft`): `anachronism`, `lexicon`, `spelling`, `tone_mark_style`, `dialogue`.
- Cột `characters.is_transmigrator` (ngoại lệ lớp từ cho xuyên không); `aliases[].kind`, `allow_mixed_naming` dùng tên F06.
- Template ID: `common.system`, `common.vi_rules`, `common.slop_rules`, `common.method`, `common.json_fix`, `longform.*` (12 mục ở bảng Prompt), `eval.vi_writer_case`, `eval.vi_judge`; chuỗi `prompt_version` dạng `id@version#sha8`.
