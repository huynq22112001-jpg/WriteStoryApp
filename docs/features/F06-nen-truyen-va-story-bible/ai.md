# F06 — AI

## Module và file

```text
ai/src/writestory_ai/
  contracts/foundation.py               FoundationInput, FrameCoreOutput, CastOutput, AddressRulesOutput,
                                        EventOutlineVolumeOutput, HooksOutput, FoundationStageResult
  workflows/longform/foundation.py      run_stage(input, models, progress) → FoundationStageResult
  evaluators/foundation_checks.py       Kiểm tra xác định trên output (bổ trợ domain BE): độ phủ, trùng tên, xưng hô
  evaluators/structured_output.py       Dùng chung (F10): parse + một lần sửa JSON
  languages/vi/prompts/foundation/
    frame_core.j2, cast.j2, address_rules.j2, event_outline_volume.j2, hooks.j2, repair_json.j2
  languages/vi/prompts/manifest.json    id/version/checksum (Plan §23.3 #8)
ai/tests/unit/foundation/, ai/tests/contract/foundation/, ai/tests/fixtures/foundation/
```

AI không ghi DB; trả output có schema, BE validate và accept (Arch §6). `address_rules.j2` là bước trích xuất quy tắc xưng hô từ nhân vật + quan hệ + quy ước thể loại.

## Contract (Pydantic)

```text
FoundationInput:
  work_id, language="vi", genre, genre_label, brief, target_chapters, chapter_length_min/max,
  style: {vocab_register, dialogue_style, tone_mark_style, voice},
  stage: "frame" | "address_rules" | "event_outline", parts: list[str] | None,
  accepted: {frame_core?, cast?, address_rules?}          # phần đã nhận, dùng làm ngữ cảnh lớp 2
  previous_parts: dict[part, output]                       # từ checkpoint khi resume / tạo lại phần
  instruction: str | None, models: dict[role, ModelSelection]  # dùng role "planner"

FrameCoreOutput:  story_frame {premise, setting, tone, themes[], main_conflict, ending_direction},
                  volume_map [{volume_no, title, chapter_from, chapter_to, arc_goal}],
                  book_rules [{key, rule, kind: world|power_system|taboo|style, rationale}],
                  author_intent {long_term, current_focus}
CastOutput:       characters [{temp_id, name, aliases[{text, kind}], role_kind, is_main, description,
                               personality, goals, background, initial_condition, initial_location_temp_id}],
                  relationships [{a, b, kind, intensity 1–5}],
                  locations [{temp_id, name, aliases[]}],
                  opening {story_time_label, location_temp_id, present_character_ids[]}
AddressRulesOutput: rules [{speaker, listener, self_term, address_term, from_chapter, until_chapter?,
                            phase_label?, rationale}]
EventOutlineVolumeOutput: volume_no, events [{temp_id, summary, detail?, planned_chapter,
                            depends_on[temp_id], storyline?}]
HooksOutput:      hooks [{temp_id, title, description, opened_at_chapter, due_by_chapter, payoff_plan,
                          priority 1–3, related_event_temp_id?}]
FoundationStageResult: stage, parts: dict[part, output], warnings[{code, path, message}],
                       usage[], prompt_versions{part: "id@version"}
```

Khóa JSON tiếng Anh, mọi giá trị văn bản tiếng Việt (Plan §6.6). `temp_id` dạng `c1`, `l1`, `e12`, `h3`; BE ánh xạ sang ID thật khi accept.

## Workflow

1. **Chọn phần cần chạy:** `stage=frame` → `frame_core`, `cast`; `address_rules` → `address_rules`; `event_outline` → `events_v{n}` cho từng quyển của `volume_map` rồi `hooks`. Bỏ phần đã có trong `previous_parts` trừ khi nằm trong `parts` (tạo lại).
2. **Mỗi phần:** render template (Jinja2 sandbox) → gọi model vai trò `planner` qua adapter F04 với structured output (`output_config.format` khi `supports_structured_outputs`, nếu không: yêu cầu JSON + parse) → Pydantic validate → lỗi parse thì một lần `repair_json.j2` (Plan §23.3 #2) → vẫn lỗi: phần `failed` với `STRUCTURED_OUTPUT_INVALID`.
3. **Checkpoint** sau mỗi phần qua `ProgressSink` (BE lưu `job_steps`); phát tiến độ `parts_done/parts_total`.
4. **Ngữ cảnh nối giữa phần:** `cast` nhận `frame_core`; `address_rules` nhận nhân vật + quan hệ + `genre`; `events_v{n}` nhận frame, cast, `volume_map[n]` và **tóm tắt** sự kiện các quyển trước (chỉ `temp_id` + summary + chương) để giữ phụ thuộc xuyên quyển; `hooks` nhận toàn bộ sự kiện.
5. **Kiểm tra xác định** (`foundation_checks.py`, không gọi LLM): chương dự kiến nằm trong quyển; phụ thuộc trỏ tới `temp_id` tồn tại; không chu trình; mỗi cặp nhân vật chính có `relationships` thì có quy tắc xưng hô cả hai chiều; tên/bí danh không trùng sau fold; hooks `due_by_chapter ≤ target_chapters`; mật độ: chương không có sự kiện nào hoặc > 3 sự kiện → `warnings` (ngưỡng giả định, chỉnh sau thử nghiệm). Kết quả là `warnings`, không tự sửa.
6. Trả `FoundationStageResult`; BE đưa job sang `waiting_user` để tác giả sửa/nhận.

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| `vi.foundation.frame_core@1` | planner | Lớp 1: system + phương pháp viết truyện dài tiếng Việt; Lớp 4: brief, thể loại, style | `FrameCoreOutput` |
| `vi.foundation.cast@1` | planner | Lớp 1; Lớp 2: frame_core; Lớp 4: chỉ dẫn | `CastOutput` |
| `vi.foundation.address_rules@1` | planner | Lớp 1 + bảng quy ước xưng hô theo thể loại (tiên hiệp/kiếm hiệp: ta–ngươi, huynh–muội, sư phụ–đồ nhi; ngôn tình/đô thị: anh–em, tôi–cậu); Lớp 2: frame + cast | `AddressRulesOutput` |
| `vi.foundation.event_outline_volume@1` | planner | Lớp 1; Lớp 2: frame + cast + volume_map (giữ nguyên giữa các quyển để tái dùng cache); Lớp 4: quyển n + tóm tắt quyển trước | `EventOutlineVolumeOutput` |
| `vi.foundation.hooks@1` | planner | Lớp 1; Lớp 2 như trên; Lớp 4: danh sách sự kiện | `HooksOutput` |
| `vi.common.repair_json@1` | cùng vai trò bước lỗi | Lớp 4 | JSON đã sửa |

Yêu cầu chung trong prompt: viết tiếng Việt tự nhiên, không dịch máy; tên nhân vật theo thể loại (Hán Việt cho tiên hiệp/cung đấu, thuần Việt/hiện đại cho đô thị); bí danh liệt kê cả biến thể có/không dấu khi người đọc hay gọi tắt; sự kiện phân bổ đều theo `target_chapters`, không kết thúc truyện trước chương cuối; mỗi hook có kế hoạch trả (`payoff_plan`) và hạn hợp lý. Prompt là sáng tác mới cho văn học mạng Việt Nam, không chép prompt/Skill InkOS (Plan §12).

## Model, effort, giới hạn

- Vai trò (Plan §7.1): `planner` (Plan chưa có vai trò "architect" riêng). Effort gợi ý `high`; job ghim model + effort cho mọi phần (giữ cache giữa các quyển).
- `max_tokens`: lấy theo model; khởi điểm đề xuất 16.000 cho mỗi phần (giả định, điều chỉnh sau đo token thực tế của truyện mẫu). Chia dàn ý theo quyển để mỗi lần gọi có kích thước bị chặn.
- Streaming bật (output dài); không stream ra UI ngoài tiến độ phần.
- Structured output: schema JSON sinh từ Pydantic (`model_json_schema()`), `additionalProperties: false`; fallback JSON mode + một lần sửa.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Không retry lặp; phần chuyển `failed` với `PROVIDER_REFUSAL`, job `waiting_user` kèm gợi ý chỉnh brief/đổi model (Plan §23.3 #3) |
| Bị cắt `max_tokens` | JSON cắt dở không "viết tiếp" được: với `events_v{n}` tách quyển thành hai nửa chương và chạy lại một lần; phần khác → `OUTPUT_TRUNCATED`, giữ checkpoint các phần đã xong |
| JSON không hợp lệ | Một lần `repair_json`; vẫn lỗi → `STRUCTURED_OUTPUT_INVALID` cho đúng phần |
| Output không phải tiếng Việt / lẫn tiếng Trung | `warnings` `language_mismatch` (kiểm bằng tỷ lệ ký tự CJK/Latin không dấu – heuristic, F08 cung cấp hàm) |
| Thiếu quy tắc cho cặp nhân vật chính | `warnings` `address_missing_pair`; không chặn accept |
| Sự kiện phụ thuộc xuyên quyển trỏ sai | `warnings` `dangling_dependency`; BE từ chối accept nếu tác giả không sửa |
| Cancel giữa phần | Dừng request (cancel truyền tới HTTP), không lưu phần dở |

## Đánh giá

- Rubric tiếng Việt (LLM-judge + người đọc, Plan §23.3 #9): đầy đủ trường; tính nhất quán frame–nhân vật–sự kiện; độ tự nhiên tên/bí danh theo thể loại; xưng hô hợp lý theo quan hệ và thể loại; phân bổ sự kiện (không dồn đầu, không bỏ trống giữa); hooks có hạn và kế hoạch trả hợp lý.
- Chỉ số xác định: tỷ lệ output pass schema lần đầu; số `warnings` theo loại; số cặp nhân vật chính thiếu quy tắc xưng hô (mục tiêu 0 sau khi tác giả nhận).
- Bộ dữ liệu mẫu: `tests/fixtures/stories/` (một tiên hiệp/kiếm hiệp, một ngôn tình/đô thị) + brief tương ứng trong `ai/tests/fixtures/foundation/briefs/`.

## Việc cần làm

- [ ] `contracts/foundation.py` + JSON schema sinh tự động.
- [ ] `workflows/longform/foundation.py` (chọn phần, ngữ cảnh nối, checkpoint, chia quyển).
- [ ] 5 template + `repair_json`, đăng ký manifest id/version/checksum.
- [ ] `evaluators/foundation_checks.py`.
- [ ] Kịch bản mock provider: output cố định cho từng phần, `refusal_on`, `truncate_on`, `bad_json_on`.
- [ ] Snapshot test prompt đã render (Plan §23.3 #8).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | `foundation_checks`: chu trình, thiếu cặp xưng hô, trùng bí danh sau fold, mật độ sự kiện | `ai/tests/unit/foundation/test_foundation_checks.py` |
| unit | Chọn phần khi resume/tạo lại phần; ngữ cảnh nối giữa quyển | `ai/tests/unit/foundation/test_part_selection.py` |
| unit | Snapshot prompt đã render cho brief mẫu | `ai/tests/unit/foundation/test_prompt_snapshots.py` |
| contract (mock provider) | 3 giai đoạn thành công; `bad_json_on=cast` → sửa 1 lần; `truncate_on=events_v2` → chia đôi; `refusal_on=frame_core` | `ai/tests/contract/foundation/test_foundation_workflow.py` |
| contract (mock provider) | Model không hỗ trợ structured outputs → JSON mode + parse | `ai/tests/contract/foundation/test_structured_fallback.py` |

Luồng: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md), [T15](../../tests/flows/T15-loi-provider.md).

## Tên mới đề xuất

- File: `ai/src/writestory_ai/contracts/foundation.py`, `ai/src/writestory_ai/workflows/longform/foundation.py`, `ai/src/writestory_ai/evaluators/foundation_checks.py`, `ai/src/writestory_ai/languages/vi/prompts/foundation/*.j2`.
- Contract: `FoundationInput`, `FrameCoreOutput`, `CastOutput`, `AddressRulesOutput`, `EventOutlineVolumeOutput`, `HooksOutput`, `FoundationStageResult`.
- Template ID: `vi.foundation.frame_core@1`, `vi.foundation.cast@1`, `vi.foundation.address_rules@1`, `vi.foundation.event_outline_volume@1`, `vi.foundation.hooks@1`, `vi.common.repair_json@1`.
- Tên phần: `frame_core`, `cast`, `address_rules`, `events_v{n}`, `hooks`; mã cảnh báo `language_mismatch`, `address_missing_pair`, `dangling_dependency`.
