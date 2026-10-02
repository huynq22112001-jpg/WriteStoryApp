# F09 — AI

Contract state là hợp đồng **Chặn MVP** (Plan §23.5 #1). AI sở hữu contract, reducer, validator xác định, Composer và workflow tóm tắt; không ghi DB (Arch §6). BE gọi các hàm thuần này và commit.

## Module và file

```text
ai/src/writestory_ai/
  contracts/state.py            StoryState, StateDelta, StateOp (union), Evidence, EndingState, KnowledgeUse
  contracts/context.py          ContextBlock, ContextLayer, ContextPackage, Budget, TraceItem, ContextTrace, TailText
  ports/context.py              ContextPort (BE triển khai bằng SQLite/FTS)
  ports/provider.py             + count_tokens(messages) khi provider hỗ trợ
  workflows/longform/state_reducer.py   apply_delta (thuần)
  evaluators/state_validator.py         validate_delta: luật V01–V15 (thuần)
  workflows/longform/summaries.py       summarize_chapter / summarize_arc / update_synopsis
  workflows/longform/handoff.py         cut_tail (tail_text), build_ending_state helpers (dùng chung F10)
  context/builder.py            Composer: chọn khối theo bước, xếp lớp, áp ngân sách
  context/budget.py             Budget, TokenCounter (exact | estimate), hiệu chỉnh tỷ lệ
  context/retrieval.py          Sinh truy vấn, gộp xếp hạng, đa dạng hóa
  context/evidence.py           verify_quote (so sánh qua normalizer.for_compare của F08)
```

## Contract (Pydantic)

Mọi model `extra="forbid"`, `schema_version=1`. Văn bản tiếng Việt NFC; ID dạng chuỗi (ULID do BE cấp, ID tạm `new:<loại>:<n>` trong delta).

```text
Evidence      = ParagraphEvidence | UserEvidence            (discriminator "kind")
ParagraphEvidence: kind="paragraph", chapter_no: int, paragraph_id: str, quote: str (1–200 ký tự, nguyên văn)
UserEvidence:      kind="user", note: str, at: datetime     (chỉ hợp lệ khi delta.source="user")

StoryTime:     label: str ("Đêm thứ ba sau trận Thanh Vân"), ordinal: float (đơn điệu tăng theo thời gian truyện),
               day_index: int | None, time_of_day: "sang"|"trua"|"chieu"|"toi"|"dem"|None
CharacterState: id, status: "alive"|"dead"|"missing"|"unknown", location_id: str|None, condition: str,
               goals: list[str], knowledge: list[str] (fact_id), inventory: list[str], in_last_scene: bool,
               last_seen_chapter: int|None
Relationship:  a: str, b: str (có hướng a→b), kind: str ("sư đồ", "kết nghĩa"…), category: "family"|"mentor"|"friend"|
               "romance"|"rival"|"enemy"|"political"|"other", intensity: int (−3..3), since_chapter: int
FactState:     id, subject, predicate, object, valid_from: int, valid_until: int|None, is_secret: bool, evidence: Evidence
HookState:     id, title, status: "open"|"progressing"|"deferred"|"resolved"|"superseded", opened_at: int,
               due_by: int|None, last_advanced: int|None, payoff_plan: str, priority: 1|2|3
EventState:    story_event_id, status: "planned"|"done"|"moved"|"dropped", planned_chapter: int|None, done_chapter: int|None   (↔ cột F06 `done_in_chapter`)
Location:      id, name, aliases: list[str]

StoryState:    schema_version, work_id, chapter_no (0 = seed), story_time: StoryTime,
               characters[CharacterState], relationships[Relationship], facts[FactState], hooks[HookState],
               events[EventState], locations[Location]

EndingState:   location_id: str|None, location_label: str, story_time: StoryTime,
               present: list[{character_id, condition, emotion, doing}], unfinished_actions: list[str],
               dominant_emotion: str, pov_character_id: str|None, last_scene_summary: str (≤ 80 âm tiết)
KnowledgeUse:  character_id, fact_id, evidence: ParagraphEvidence      (nhân vật hành động dựa trên dữ kiện)

StateDelta:    schema_version, work_id, chapter_no: int, base_state_chapter: int, base_state_hash: str,
               source: "pipeline"|"user", candidate_id: str|None, ops: list[StateOp],
               knowledge_uses: list[KnowledgeUse], ending_state: EndingState|None (bắt buộc khi pipeline)
StateOp (chung): op: str, evidence: Evidence|None, reason: str|None, in_flashback: bool = False
```

Giữ đúng 15 op của Plan §23.1.A (`hook.open|advance|resolve|defer` và `event.done|move|drop` tính tách từng op) và thêm 2 op đề xuất (ghi ở "Tên mới đề xuất"):

| Op | Trường riêng | Tiền điều kiện (validator) | Hiệu lực (reducer) |
|---|---|---|---|
| `character.update` | `character_id`, `status?`, `condition?`, `goals_set?`, `goals_add?`, `goals_remove?`, `inventory_add?`, `inventory_remove?`, `override_reason?` | Nhân vật tồn tại; đã `dead` thì chỉ được đổi `status` kèm `override_reason` | Ghi đè/ thêm/ bớt trường |
| `character.move` | `character_id`, `to_location_id` | Nhân vật `alive`; địa điểm tồn tại | `location_id` |
| `character.learn` | `character_id`, `fact_id` | Cả hai tồn tại | Thêm vào `knowledge` |
| `relationship.set` | `a`, `b`, `kind`, `category`, `intensity` | `a ≠ b`; `intensity` trong −3..3 | Thay quan hệ a→b, `since_chapter=N` |
| `address.change` | `speaker_id`, `listener_id`, `self_term`, `address_term` (theo cột F06 `address_rules`) | Có `relationship.set` cùng cặp trong delta này, hoặc quan hệ đã đổi sau `from_chapter` của luật hiện hành | Không đổi `StoryState`; BE đóng luật cũ (`until_chapter=N-1`) và chèn luật mới từ chương N |
| `fact.add` | `fact{id (tạm), subject, predicate, object, is_secret}` | Không trùng fact đang hiệu lực (so `for_compare`) | Thêm fact, `valid_from=N` |
| `fact.close` | `fact_id` | Fact đang hiệu lực | `valid_until=N` |
| `hook.open` | `hook{id (tạm), title, payoff_plan, due_by, priority}` | `due_by` > N nếu có | Thêm hook `open` |
| `hook.advance` | `hook_id`, `note` | Hook không `resolved`/`superseded` | `status=progressing`, `last_advanced=N` |
| `hook.resolve` | `hook_id`, `as_superseded: bool=false` | Như trên | `resolved` (hoặc `superseded` – chỉ nguồn `user`) |
| `hook.defer` | `hook_id`, `new_due_by`; dùng `reason` thay `evidence` | `new_due_by` > `due_by` hiện tại và > N | `deferred`, `due_by=new_due_by` |
| `event.done` | `story_event_id` | Chưa `done`; mọi `depends_on` đã `done` (tính cả op trước trong delta) | `done`, `done_chapter=N` |
| `event.move` | `story_event_id`, `to_chapter`; dùng `reason` | `to_chapter` > N | `moved`, `planned_chapter=to_chapter` |
| `event.drop` | `story_event_id`; dùng `reason` | Chưa `done` | `dropped` |
| `time.advance` | `to: StoryTime`, `flashback: bool` | `to.ordinal ≥ story_time.ordinal` trừ khi `flashback` | Không hồi tưởng: `story_time=to`; hồi tưởng: ghi timeline, không đổi hiện tại |
| `character.add` *(đề xuất)* | `character{id (tạm), name, aliases[], role_note}`, `location_id?` | Tên không trùng canon (so biến thể F08) | Thêm `alive` |
| `location.add` *(đề xuất)* | `location{id (tạm), name, aliases[]}` | Không trùng | Thêm địa điểm |

Op có `in_flashback=true`: được phép với nhân vật đã chết; `character.move/update` không đổi trạng thái hiện tại (chỉ ghi lịch sử); `fact.add` vẫn thêm.

## Workflow

### 1. Reducer `apply_delta(state, delta) -> StoryState`

1. Sao chép sâu `state`; bảng ánh xạ ID tạm.
2. Áp từng op theo thứ tự (bảng trên). Hàm thuần, không đọc giờ hệ thống, không ngẫu nhiên.
3. Sau op: `in_last_scene = id ∈ ending_state.present`; `last_seen_chapter=N` cho nhân vật có trong `ending_state.present` hoặc được nhắc trong bằng chứng op.
4. `chapter_no=N`; trả state mới. `state_hash` = sha256 của JSON chuẩn hóa (khóa sắp xếp, danh sách sắp theo `id`).

### 2. Validator xác định `validate_delta(state, delta, paragraphs, ctx) -> ValidationResult`

| Luật | Kiểm tra | Hậu quả |
|---|---|---|
| V01 | Pydantic schema + `extra=forbid` | `error` |
| V02 | `base_state_chapter == state.chapter_no` và `base_state_hash == hash(state)` | `error` (BE settle lại trên base mới) |
| V03 | ID tham chiếu tồn tại trong state hoặc là ID tạm khai báo ở op trước | `error` |
| V04 | Nhân vật `dead`/`missing` không `move`/`learn`/`update` (trừ `in_flashback`); `dead→alive` cần `override_reason` | thiếu lý do: `error`; có lý do: `warning` (finding `major` "hồi sinh") |
| V05 | Thời gian không lùi trừ `flashback=true` | `error` |
| V06 | Hook `resolved`/`superseded` không `advance`/`resolve`/`defer`; `defer` phải lùi hạn về sau N | `error` |
| V07 | Mỗi `knowledge_uses`: fact không bí mật, hoặc thuộc `knowledge` của nhân vật, hoặc được `learn` ở op trước | `error` ("lộ bí mật sớm", Plan §23.1.A) |
| V08 | Mỗi `ParagraphEvidence`: `chapter_no == N`, `paragraph_id` thuộc candidate, `verify_quote` đúng; op nguồn `pipeline` (trừ `hook.defer`, `event.move`, `event.drop`) bắt buộc có | `error` |
| V09 | `fact.close` trên fact đã đóng → `error`; `fact.add` trùng fact hiệu lực → `warning` | |
| V10 | `event.done` lặp/`depends_on` chưa xong; `event.move` về quá khứ | `error` |
| V11 | `address.change` không kèm sự kiện quan hệ (bảng op) | `error` |
| V12 | `character.move` tới địa điểm không tồn tại/không được `location.add` | `error` |
| V13 | `ending_state.present` ⊆ nhân vật `alive` sau khi áp; `ending_state.story_time == story_time` sau khi áp → `error`; địa điểm của người có mặt ≠ `ending_state.location_id` → `warning` | |
| V14 | Hook có `due_by < N`, chưa `resolved`/`superseded`, không `defer` trong delta | finding `major` "hook quá hạn" (báo 100% – Plan §9), không chặn commit |
| V15 | `relationship.set` có `a == b`, `intensity` ngoài khoảng | `error` |

`ValidationResult{ok: bool, issues: [ValidationIssue{rule, op_index|None, severity: "error"|"warning", message_key, params}], report_findings: [...]}`. Có `error` → không được commit (Plan §6.2). LLM validator (F10 bước 7b) chạy sau, chỉ khi xác định đã `ok`.

### 3. Tóm tắt phân tầng (`summaries.py`, Plan §23.3 #1)

| Hàm | Đầu vào | Đầu ra (structured) | Ghi chú |
|---|---|---|---|
| `summarize_chapter` | Đoạn cuối cùng của candidate (có `paragraph_id`), op của delta làm gợi ý, mục tiêu plan | `ChapterSummary{text, key_points[≤7], characters[], hooks_touched[]}` | Độ dài mục tiêu cấu hình theo âm tiết (giả định, chỉnh ở T14) |
| `summarize_arc` | Tóm tắt chương của arc (+ bản arc đang chạy trước đó nếu có) | `ArcSummary{text, key_points, unresolved_threads[]}` | Không đọc toàn văn chương: độ dài đầu vào ổn định |
| `update_synopsis` | Synopsis cũ + các bản arc cuối | `Synopsis{text, key_points}` | Viết lại hoàn toàn, không nối thêm |

Mọi tóm tắt chỉ dựa trên văn bản/state đã commit; không đưa nội dung dàn ý chưa xảy ra vào tóm tắt (tránh "nhớ" việc chưa xảy ra).

### 4. Composer (`context/builder.py`)

Đầu vào `ComposeRequest{work_id, chapter_no, step, model: ModelProfile{model_id, max_input_tokens, max_output_tokens, tokens_per_syllable|None, supports_count_tokens}, soft_cap_tokens, plan?, candidate_paragraphs?, findings?, instruction}`; dữ liệu lấy qua `ContextPort`. Đầu ra `ContextPackage{layers[ContextLayer{n, blocks[ContextBlock], cache_breakpoint}], budget: Budget, trace: ContextTrace}`.

**Lớp (Plan §6.4)** – thứ tự khối cố định để giữ prefix cache:

| Lớp | Khối | Bảo vệ? | Cache |
|---|---|---|---|
| 1 – toàn app | `common.system`, `common.vi_rules`, `common.method` theo vai trò, `common.slop_rules` (F08) | Có (tĩnh) | Breakpoint 1 |
| 2 – theo truyện | Premise + book rules; dàn ý tổng (rút gọn ổn định); thẻ nhân vật chính; `address_rules` các cặp chính; 1–2 đoạn **style anchor** (Plan §23.3 #7, chọn cố định theo `bible_revision`); cụm sáo riêng truyện | Lõi bảo vệ; thẻ nhân vật phụ nén được | Breakpoint 2; ghim theo `bible_revision` lúc bắt đầu job |
| 3a – chương, dùng chung các bước | Synopsis → tóm tắt arc hiện tại → K tóm tắt chương gần nhất → state lọc (nhân vật có mặt, hook đến hạn, sự kiện của N) → kết quả tìm kiếm → `handoff(N-1)` → `tail_text(N-1)` | handoff, tail, state nhân vật có mặt, hook đến hạn, sự kiện bắt buộc: **bảo vệ**; còn lại nén được | Breakpoint 3 (giống nhau cho planner/writer/reviewer cùng chương – [Suy luận], đo bằng `cache_read_tokens`) |
| 3b – theo bước | `plan(N)` (writer, settler, reviewer, repair); đoạn candidate có `[p:id]` (settler, validator, seam, reviewer, repair) | Bảo vệ | — |
| 4 – lượt hiện tại | Template bước (`longform.*`) + chỉ dẫn một lần của tác giả | Bảo vệ | — |

Khối theo bước (nhận ✓): planner – 1, 2, 3a, 4 (chưa có plan); writer – 1, 2, 3a, plan, 4; settler/validator – 1 (rút gọn), state N-1 đầy đủ phần liên quan, candidate, 4; seam – `ending_state(N-1)`, 3 đoạn cuối của `tail_text`, cửa sổ mở chương N; reviewer – 1, 2, 3a, plan, candidate, finding `needs_confirmation`, 4; repair – 1, 2 (style anchor), plan, đoạn đích ± 1 đoạn kề, finding, 4.

**Ngân sách (`budget.py`):**

```text
input_limit = min(model.max_input_tokens, soft_cap_tokens)
margin      = 15% × input_limit nếu đếm ước lượng (Plan §23.3 #4); dự phòng nhỏ cho schema/tool khi đếm chính xác (giả định cấu hình)
available   = input_limit − margin
```

`max_input_tokens` lấy từ `provider_models` của model **thực dùng** (Plan §7.1); trống (OpenAI-compatible) → yêu cầu người dùng điền, tạm dùng giá trị mặc định bảo thủ trong cấu hình và ghi chú trong trace (giả định). `soft_cap_tokens` (cấu hình theo truyện) giữ context ổn định và chi phí dự đoán được dù model có 1M token. Khác InkOS: không chia đôi `(contextWindow − maxTokens)/2` (Review §2.1).

**Đếm token:**

1. `estimate(text) = ⌈units × tokens_per_syllable⌉ + overhead(markup, [p:id], JSON)`; `units` từ `length_counter` F08. `tokens_per_syllable` của model trong `provider_models`; chưa đo → mặc định của gói `vi` (giả định).
2. `exact`: `provider.count_tokens` khi model hỗ trợ (Anthropic có endpoint đếm token – Plan §23.3 #4) và (ước lượng ≥ ngưỡng gần ngân sách, mặc định 85% – giả định) hoặc model chưa có tỷ lệ đo.
3. Sau mỗi request: so ước lượng với `input_tokens` provider trả; cập nhật tỷ lệ bằng trung bình trượt; BE ghi `tokens_per_syllable` (`source=measured`). Không suy diễn khi provider không trả usage.

**Nén khi vượt ngân sách** (xác định, không gọi LLM ở MVP; thứ tự): (1) bỏ kết quả tìm kiếm hạng thấp; (2) giảm K tóm tắt chương xuống 1 (giữ N-1); (3) bỏ fact không liên quan nhân vật có mặt; (4) bỏ state nhân vật không có mặt; (5) sự kiện tương lai xa chỉ còn tiêu đề; (6) tóm tắt arc → `key_points`; (7) synopsis → `key_points`; (8) thẻ nhân vật phụ ở lớp 2 → tên + một dòng. Quyết định nén lớp 2 được tính **một lần theo (`bible_revision`, model)** và tái dùng, để prefix không đổi giữa các chương. Vẫn vượt: thu `tail_text` về tối thiểu 1.000 token (theo đoạn); vẫn vượt → lỗi `CONTEXT_PROTECTED_OVER_BUDGET` (không bao giờ cắt phần bảo vệ – Plan §23.3 #4; InkOS cũng từ chối nén phần bảo vệ, `agents/composer.ts`).

### 5. `tail_text` (`handoff.py: cut_tail`)

1. Lấy đoạn của revision committed N-1 theo thứ tự; duyệt từ cuối lên, cộng token.
2. Dừng khi thêm đoạn kế sẽ vượt `tail_max` (mặc định 2.000) và tổng đã ≥ `tail_min` (mặc định 1.000) (Plan §6.2).
3. Đoạn cuối cùng tự nó > `tail_max`: cắt trong đoạn tại ranh giới câu, giữ phần cuối, `cut_inside_paragraph=true`.
4. Chương ngắn hơn `tail_min`: lấy cả chương.
5. Trả `TailText{paragraph_ids, text ([p:id] …), tokens, counted_for_model, cut_inside_paragraph}`; BE lưu vào `chapter_handoffs`. Chương N+1 dùng model khác → đếm lại, nếu vượt thì bỏ đoạn đầu (vẫn ≥ min khi có thể).

Planner và Writer đều nhận cùng bản cắt (Plan §6.2), không nhận toàn văn chương trước (sửa Review §2.3 #2, #3).

### 6. Retrieval (`retrieval.py`)

1. Truy vấn sinh xác định từ: tên chuẩn nhân vật có mặt, tiêu đề hook đến hạn/phải tiến, tóm tắt sự kiện bắt buộc của N, nhãn địa điểm `ending_state`, (writer/reviewer) cụm danh từ trong beat của plan.
2. `ContextPort.search(q, kinds=[chapter, fact, summary, hook], before_chapter=N-1, limit)` – loại chương N-1 vì đã có handoff/tail.
3. Gộp bằng reciprocal rank fusion, trọng số theo loại; khử trùng theo (`source_id`, `paragraph_id`); tối đa 2 đoạn mỗi chương; trần `retrieval_max_items` (giả định cấu hình).
4. Mỗi kết quả thành `ContextBlock` nén được kèm provenance. Chọn ngữ nghĩa bằng LLM trên ứng viên lexical (MEM05) để sau, khi T14 cho thấy cần.

### 7. Trace

`TraceItem{source_type: "system"|"rules"|"method"|"slop"|"bible"|"character_card"|"address_rules"|"style_anchor"|"outline"|"synopsis"|"summary_arc"|"summary_chapter"|"state"|"fact"|"hook"|"story_event"|"retrieval"|"handoff"|"tail_text"|"plan"|"candidate"|"finding"|"instruction", source_id, source_revision, chapter_no?, paragraph_ids?, layer, protected, tokens_est, included, dropped_reason?: "over_budget"|"low_rank"|"duplicate"|"not_relevant", preview (≤ 200 ký tự)}`. `ContextTrace` gồm `step`, `round`, `model_id`, `effort`, `prompt_versions`, `budget`, `estimated_input_tokens`, `counted_input_tokens?`, `count_method`, `items`, `notes`; BE bổ sung usage thực nhận.

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| `longform.bible` | Khung lớp 2 | 2 | — |
| `longform.chapter_context` | Khung lớp 3a | 3 | — |
| `longform.summary_chapter` | Tóm tắt | 4 | `ChapterSummary` JSON |
| `longform.summary_arc` | Tóm tắt | 4 | `ArcSummary` JSON |
| `longform.synopsis` | Tóm tắt | 4 | `Synopsis` JSON |

Template settle/validator dùng contract ở đây nhưng thuộc F10. Tất cả qua manifest F08.

## Model, effort, giới hạn

- Composer, reducer, validator xác định: không gọi model (trừ `count_tokens`).
- Tóm tắt: vai trò Tóm tắt (Plan §7.1), effort `low`; `max_tokens` đủ cho JSON tóm tắt (cấu hình).
- Structured output: JSON Schema xuất từ Pydantic; fallback theo Plan §23.3 #2 (JSON mode + parse + một lần `common.json_fix` + Pydantic; vẫn lỗi → `STRUCTURED_OUTPUT_INVALID`).

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal (tóm tắt) | Không retry lặp; tóm tắt chương thiếu → F10 chuyển `waiting_user` (cần cho commit); arc/synopsis → `stale`, không chặn |
| Bị cắt `max_tokens` | Tóm tắt: tăng `max_tokens` một lần trong giới hạn vai trò; vẫn cắt → xử lý như JSON hỏng |
| JSON không hợp lệ | `common.json_fix` một lần → Pydantic → `STRUCTURED_OUTPUT_INVALID` |
| Phần bảo vệ vượt ngân sách | `CONTEXT_PROTECTED_OVER_BUDGET`, gợi ý: chọn model context lớn hơn, tăng `soft_cap_tokens`, rút gọn plan/bible |
| Model không có `max_input_tokens` | Mặc định bảo thủ + ghi chú trace + cảnh báo ở Cài đặt |
| Delta trống (chương không đổi gì) | Hợp lệ nếu có `ending_state` và `time.advance` không bắt buộc; validator vẫn chạy V13/V14 |
| Trích dẫn có `…` | `verify_quote` tách theo `…`, các phần phải xuất hiện đúng thứ tự trong cùng đoạn |

## Đánh giá

- `tests/fixtures/state/`: state + delta lỗi cho từng luật V01–V15 (Plan tests README); tỷ lệ bắt = 100% là điều kiện pass.
- T14 (truyện mẫu 200+ chương sinh bằng mock provider có `scripted_outputs`): kích thước context từng bước theo chương phải ổn định (không tăng tuyến tính); dữ kiện "gài" ở chương đầu và cần ở chương rất sau phải xuất hiện trong context (retrieval recall trên tập gài); sai số ước lượng token so với usage thực (chỉ với `live`).
- Độ trung thành của tóm tắt: LLM-judge rubric tiếng Việt (Plan §23.3 #9) trên mẫu nhỏ, chạy khi đổi prompt/model.

## Việc cần làm

- [ ] `contracts/state.py`, `contracts/context.py` + xuất JSON Schema vào `contracts/examples/` (Chặn MVP).
- [ ] `state_reducer.py` + test tính tất định.
- [ ] `state_validator.py` V01–V15 + fixture từng luật.
- [ ] `evidence.py` `verify_quote`.
- [ ] `summaries.py` + 3 template + schema.
- [ ] `budget.py`: ngân sách, `TokenCounter`, hiệu chỉnh tỷ lệ.
- [ ] `builder.py`: bảng khối theo bước, thứ tự lớp, nén xác định, cache breakpoint.
- [ ] `handoff.py: cut_tail`.
- [ ] `retrieval.py`.
- [ ] `ContextPort` Protocol + fake in-memory cho test AI không cần BE.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Reducer: từng op, ID tạm, hồi tưởng, hash ổn định | `ai/tests/unit/state/test_reducer.py` |
| unit | Validator: mỗi luật một ca đúng/sai từ `tests/fixtures/state/` | `ai/tests/unit/state/test_validator_rules.py` |
| unit | Property: áp chuỗi delta hợp lệ ngẫu nhiên không bao giờ sinh state vi phạm V04/V05/V06 | `ai/tests/unit/state/test_reducer_properties.py` |
| unit | `cut_tail`: biên 1.000/2.000, đoạn quá dài, chương ngắn | `ai/tests/unit/context/test_cut_tail.py` |
| unit | Composer: phần bảo vệ không bị nén; thứ tự nén; lỗi khi bảo vệ vượt; prefix lớp 1–2 giống hệt giữa các chương cùng `bible_revision` | `ai/tests/unit/context/test_builder_budget.py` |
| unit | Retrieval: RRF, khử trùng, loại chương N-1 | `ai/tests/unit/context/test_retrieval.py` |
| contract (mock provider) | Tóm tắt: refusal, cắt, JSON hỏng; `count_tokens` có/không | `ai/tests/contract/longform/test_summaries.py` |
| contract | JSON Schema snapshot của `StoryState`/`StateDelta` | `ai/tests/contract/test_state_schema_snapshot.py` |

Luồng: [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md), [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md), [T15](../../tests/flows/T15-loi-provider.md).

## Tên mới đề xuất

- Op `character.add`, `location.add`; trường chung op `reason`, `in_flashback`; `character.update.override_reason`; `hook.resolve.as_superseded`.
- `StateDelta.knowledge_uses` + `KnowledgeUse`; `StateDelta.source`, `base_state_chapter`, `base_state_hash`, `candidate_id`.
- Trường `StoryState` ngoài Plan: `CharacterState.last_seen_chapter`, `Relationship.category`, `FactState.is_secret`, `HookState.title/priority`, `EventState.planned_chapter/done_chapter`, `StoryTime.day_index/time_of_day`.
- `EndingState` (cấu trúc của `ending_state`), `TailText`, `ContextBlock`, `ContextLayer`, `ContextPackage`, `Budget`, `ModelProfile`, `ComposeRequest`, `TraceItem`, `ContextTrace`, `ValidationResult`, `ValidationIssue`, `ChapterSummary`, `ArcSummary`, `Synopsis`.
- File `workflows/longform/state_reducer.py`, `evaluators/state_validator.py`, `contracts/context.py`.
- Luật `V01`–`V15`; mã lỗi `CONTEXT_PROTECTED_OVER_BUDGET`; cấu hình `soft_cap_tokens`, `tail_min`, `tail_max`, `retrieval_max_items`, `k_recent_summaries`.
