# F10 — AI

Pipeline một chương Plan §6.2 / FL04, chạy trong package AI, nhận dữ liệu qua `ContextPort` và trả `PipelineResult`. AI không ghi DB; BE commit (be.md). Ý tưởng tham khảo InkOS (`pipeline/runner.ts`, `agents/*`) – AGPL, không chép code/prompt.

## Module và file

```text
ai/src/writestory_ai/
  contracts/generation.py        GenerationInput, PinnedRoles, WriteSettings, ResumePoint, PipelineResult, DraftCandidate
  contracts/longform.py          ChapterPlan, SettleOutput, LLMValidation, SeamResult, ReviewResult, RepairOps, OutlineProposal, PacingBudget
  contracts/paragraphs.py        Paragraph, ParagraphOp, apply_ops (thuật toán dùng chung với BE)
  contracts/events.py            TokenDelta, StepProgress, CheckpointPayload
  workflows/longform/
    pipeline.py                  run_chapter(): điều phối bước 1–11, vòng sửa, resume
    planner.py                   Bước 2 + kiểm tra plan
    writer.py                    Bước 4: stream, tách đoạn, viết tiếp khi bị cắt
    settlement.py                Bước 6: StateDelta + ending_state + phân loại tên mới
    reviewer.py                  Bước 7b (LLM validator) và 9 (review); xác minh trích dẫn
    seam_check.py                Bước 8
    repair.py                    Bước 10
    handoff.py                   (F09) cut_tail, open_threads/next_opening_requirements
    pacing.py                    Ngân sách sự kiện/chương, chống kết thúc sớm
    outline_review.py            Xét lại dàn ý mỗi K chương
    summaries.py                 (F09) tóm tắt chương/arc/synopsis
  evaluators/
    deterministic.py             Bước 5: độ dài, tên riêng, nhân vật chết/vắng, n-gram, dấu hiệu kết truyện, rò meta; gọi pack.deterministic_checks (F08)
    state_validator.py           (F09) V01–V15
    structured_output.py         Gọi có schema / JSON mode / json_fix / Pydantic
  policies/
    retry.py                     Retry transport (429/5xx, Retry-After) – không retry refusal/401
    limits.py                    Trần vòng sửa, trần token sửa, số lần viết tiếp
```

## Contract (Pydantic)

```text
WriteSettings:   (BE dựng từ works.chapter_length_min/max, max_repair_rounds, target_chapters của F05 + works.writing_config)
                 length_min=2500, length_max=3500 (âm tiết, UI §5.6.3), length_tolerance, length_hard_floor_ratio,
                 max_repair_rounds=2, repair_token_cap, repair_max_changed_ratio, repair_include_major=true,
                 max_continuations=2, tail_min=1000, tail_max=2000, seam_opening_window_units,
                 ngram_n, ngram_max_overlap, verbatim_run_units, hooks_due_lookahead,
                 outline_review_every_k=10, arc_summary_every=10, strict_new_characters=false,
                 allow_early_ending=false, target_chapters
                 (giá trị không có trong Plan là giả định cấu hình, chỉnh bằng T05/T14)
PinnedRoles:     planner|writer|checker|reviewer|summary → {provider_id, model_id, effort|None, max_tokens, capabilities}
GenerationInput: work_id, chapter_no, job_id, pinned: PinnedRoles, bible_revision, prompt_manifest_version,
                 settings: WriteSettings, brief|None, instruction|None, mode: "auto"|"review_each"|"review_every_k",
                 resume: ResumePoint|None
ResumePoint:     step, round, plan_id?, candidate_id?, settle_ref?, reason

ChapterPlan:     title, goal, pov_character_id|None,
                 opening: {continue_from: str, location_id, story_time_label, present_character_ids[],
                           unfinished_actions: [{action, handling: "continue"|"resolve"|"defer_explicit"}],
                           transition: "none"|"time_skip"|"scene_change", transition_note|None},
                 beats: [{order, summary, required_event_ids[], hook_ids[], target_units}],
                 required_event_ids[], hooks_to_advance[], hooks_to_resolve[],
                 hook_deferrals: [{hook_id, new_due_by, reason}],
                 new_characters: [{name, role, reason}], must_avoid[], ending_hint,
                 allowed_ending: bool, target_length: {min, max}, pacing: PacingBudget
PacingBudget:    events_remaining, chapters_remaining, ratio, recommended_events: [min, max],
                 assigned_events, warning: "none"|"crowded"|"dragging"|"no_material"
DraftCandidate:  candidate_id, kind: "draft"|"repair"|"author", parent_id|None, round,
                 paragraphs: [Paragraph{paragraph_id, text}], stop_reason, continuations, length: LengthStats
SettleOutput:    ops: [StateOp], knowledge_uses: [KnowledgeUse], ending_state: EndingState,
                 new_entities: [{name, type: "character"|"location"|"organization"|"item"|"technique"|"other", op_index|None, paragraph_id}],
                 open_threads[], next_opening_requirements[]
LLMValidation:   issues: [{type: "missing_change"|"wrong_change"|"unsupported_change"|"contradiction_with_state"|"timeline_conflict"|"secret_leak",
                           op_index|None, paragraph_id, quote, explanation}]
SeamResult:      aspects: {location|time|present_characters|emotion|unfinished_actions:
                           {verdict: "match"|"transition_ok"|"mismatch"|"not_addressed", paragraph_id?, quote?, expected, found}},
                 verdict: "pass"|"fail", notes
ReviewResult:    findings: [{kind, paragraph_id, quote, explanation, suggestion}],
                 confirmations: [{finding_id, confirmed: bool, reason}],
                 plan_coverage: {events: [{id, covered, paragraph_id?}], hooks: [{id, action_seen}]},
                 premature_ending: bool
RepairOps:       ops: [ParagraphOp{paragraph_id, action: "replace"|"insert_after"|"delete", text|None}], notes
OutlineProposal: changes: [{change_id, story_event_id|None, action: "move"|"drop"|"add"|"edit", to_chapter?, summary?, reason}],
                 pacing_assessment
PipelineResult:  status: "ready"|"needs_user", reason_code|None, candidate: DraftCandidate, delta: StateDelta|None,
                 summary: ChapterSummary|None, seam: SeamResult|None, findings: [Finding], plan_id,
                 measurements: {...}, usage_by_step
```

Mức độ (`severity`) **do host gán** theo loại, LLM chỉ đề xuất (Plan §6.2: fact/timeline/seam/tên riêng là `blocker`, nhịp/giọng `minor`):

| Loại (`kind`) | Mức |
|---|---|
| `fact`, `timeline`, `seam`, `name` (chưa khai báo), `ending` (kết truyện sớm), `repetition` (chép nguyên văn/vượt ngưỡng n-gram), `missing_event` (sự kiện bắt buộc không xảy ra và không được `event.move`), `meta_leak` | `blocker` |
| `address` | `blocker` khi độ tin cậy cao hoặc reviewer xác nhận; `major` khi chưa xác nhận |
| `POV`, `ooc`, `slop`, `anachronism`, `name_variant`, `tone_mark_style`, `length` (ngoài khoảng), `new_character_unplanned`, `hook_overdue`, `pacing` | `major` (`length` dưới sàn cứng → `blocker`; `new_character_unplanned` → `blocker` khi `strict_new_characters`) |
| `craft`, `voice`, `spelling`, `dialogue`, `lexicon` (mật độ Hán Việt) | `minor` |

## Workflow

### Tổng quan

```text
run_chapter(input, ctx: ContextPort, provider, progress: ProgressSink, ckpt: CheckpointSink, cancel)
 1 load → 2 plan → 3 compose → 4 write → [5 check → 6 settle → 7 validate → 8 seam → 9 review]
   → có blocker/seam fail? → 10 repair (round ≤ K, ≤ token cap) → quay lại 5
   → hết vòng: needs_user(REPAIR_EXHAUSTED)
   → không blocker: summarize_chapter → PipelineResult(ready)   (BE: 11 commit)
```

Mọi bước kiểm `cancel` trước khi gọi provider và truyền hủy xuống HTTP (Plan §6.6 cuối). Mỗi bước gọi `progress.step(started|completed|failed)` và `ckpt.save(step, payload)`.

### Bước 1 – Load

- Vào: `ContextPort`. Ra: `LoadedContext{state(N-1), state_hash, handoff(N-1){ending_state, tail_text, open_threads, next_opening_requirements, revision}, events_for_N (planned_chapter = N + quá hạn chưa done), hooks_due (due_by ≤ N + hooks_due_lookahead, chưa đóng), pacing inputs, bible_revision view, address_rules hiệu lực}`.
- Chương 1: state seed + handoff mở đầu (không `tail_text`).
- Checkpoint: `{state_hash, handoff_revision}` (rẻ, luôn chạy lại khi resume).

### Bước 2 – Plan (`planner.py`)

1. `input_hash = sha256(state_hash ‖ handoff_id:revision ‖ outline_revision ‖ story_events_revision ‖ bible_revision ‖ brief_hash ‖ planner prompt_version)`; Plan §5 chỉ nêu ba thành phần đầu, phần còn lại là mở rộng (Tên mới đề xuất).
2. Có plan `active` cùng `input_hash` (kể cả plan tác giả đã sửa) → dùng lại, `job.step skipped`. Khác → lập mới (sửa điểm yếu InkOS #8).
3. `pacing.compute(...)` → `PacingBudget` (mục "Nhịp truyện").
4. Gọi vai trò Lập kế hoạch: context lớp 1, 2, 3a (synopsis, arc, K tóm tắt, state lọc, retrieval, `handoff(N-1)`, `tail_text(N-1)`) + `longform.planner`. Structured output `ChapterPlan`.
5. Kiểm tra xác định plan: `required_event_ids` ⊆ `events_for_N`; mọi hook `due_by == N` nằm trong `hooks_to_resolve` hoặc `hook_deferrals` có lý do; `opening.present_character_ids` ⊆ nhân vật `alive`; `opening.location_id` khớp `ending_state(N-1)` trừ khi `transition ≠ none`; `allowed_ending = (N ≥ target_chapters) or allow_early_ending`; `target_length` trong `WriteSettings`. Sai → một lần sửa kèm danh sách lỗi (`common.json_fix`) → vẫn sai: `STRUCTURED_OUTPUT_INVALID`.
- Ra/checkpoint: `plan_id`, `input_hash`.

### Bước 3 – Compose

Composer F09 (`context/builder.py`) theo bước; `plan(N)`, `handoff(N-1)`, `tail_text(N-1)` là **bảo vệ**. Ghi `ContextTrace` cho từng bước gọi model. Lỗi `CONTEXT_PROTECTED_OVER_BUDGET` → `needs_user`.

### Bước 4 – Write (`writer.py`)

1. Vai trò Viết; lớp 1, 2 (gồm style anchor), 3a, `plan(N)`, lớp 4 `longform.writer` (chỉ dẫn: viết văn xuôi tiếng Việt, mở cảnh nối trực tiếp `ending_state`, xử lý từng hành động dở dang theo `opening.unfinished_actions`, theo beats, độ dài mục tiêu bằng âm tiết, không tiêu đề/không lời dẫn meta, đoạn cách nhau một dòng trống).
2. Stream: gửi `TokenDelta` cho `ProgressSink` (BE gộp 50–100 ms). Tách đoạn ở dòng trống; đoạn hoàn tất được cấp `paragraph_id` (bộ sinh ID do BE inject, cùng định dạng Tiptap UniqueID – Plan §23.1.B) và `ckpt.save_partial` (mỗi đoạn hoặc vài giây).
3. `stop_reason`:
   - kết thúc bình thường → hoàn tất;
   - `max_tokens` → `longform.writer_continue` (cùng prefix lớp 1–3a để giữ cache + phần cuối đã viết + "viết tiếp đúng từ chỗ dừng, không lặp"), tối đa `max_continuations=2` (Plan §23.3 #3); ghép: nếu bị cắt giữa đoạn, phần tiếp nối vào đoạn đó; cắt phần trùng lặp đầu (so `for_compare` câu cuối); ghi số lần vào trace. Vẫn cắt → `needs_user(OUTPUT_TRUNCATED)`, giữ partial;
   - refusal → `needs_user(PROVIDER_REFUSAL)`, không retry lặp, kèm gợi ý sửa chỉ dẫn/đổi model (§23.3 #3).
4. Hậu xử lý: bỏ dòng meta đầu/cuối khớp mẫu ("Dưới đây là…", tiêu đề markdown); `normalizer.normalize(mode="ai_output")` (F08: kiểu bỏ dấu, thoại, dấu câu).
- Ra: `DraftCandidate(kind=draft, round=0)`; event `candidate.ready` do BE phát sau khi lưu.

### Bước 5 – Check xác định (`evaluators/deterministic.py`, không gọi LLM)

| Kiểm tra | Cách làm | Ra |
|---|---|---|
| Độ dài | `length_counter` so `plan.target_length` ± `length_tolerance`; dưới `length_hard_floor_ratio × min` | `length` |
| Tên riêng | `names.extract_name_candidates` (F08) trừ canon/bí danh/biến thể và `plan.new_characters` → danh sách `pending_names` (chuyển sang bước 6 phân loại); sai dấu/trộn tên do `vi.name_variant` | `name_variant`; `pending_names` |
| Nhân vật chết/vắng | Tên nhân vật `dead`/`missing` làm chủ ngữ câu có động từ hành động, ngoài thoại và ngoài đoạn có dấu hiệu hồi tưởng | `fact` `major` + `needs_confirmation` (reviewer xác nhận → `blocker`) |
| Lặp chương trước | n-gram âm tiết (`ngram_n`) của N so toàn văn N-1: tỷ lệ chung > `ngram_max_overlap` hoặc chuỗi chép liền ≥ `verbatim_run_units` | `repetition` + đoạn liên quan |
| Kết truyện sớm | Mẫu "Hết", "Toàn văn hoàn", "Kết thúc truyện" ở cuối khi `allowed_ending=false` | `ending` |
| Rò meta | Câu kiểu "Là một mô hình AI…", nhắc tới prompt | `meta_leak` |
| Tiếng Việt | `pack.deterministic_checks` (F08): xưng hô, lớp từ, cụm sáo, chính tả, kiểu bỏ dấu, thoại | các loại F08 |

Ra: `Finding[]` (`source=check`). Chạy lại mỗi vòng sửa.

### Bước 6 – Settle (`settlement.py`)

- Vào: state N-1 (nhân vật có mặt/được nhắc + fact/hook liên quan + sự kiện của N), `plan`, đoạn candidate `[p:id]`, `pending_names`. Vai trò Kiểm tra/Settle; `longform.settler`; structured `SettleOutput`.
- Ghép `StateDelta{base_state_chapter=N-1, base_state_hash, source="pipeline", candidate_id, ops, knowledge_uses, ending_state}`.
- Tên: tên trong `pending_names` không được phân loại → `name` `blocker` ("tên chưa khai báo"); phân loại `character` → phải có `character.add` (op đề xuất F09); không nằm trong `plan.new_characters` → `new_character_unplanned`.
- `open_threads`, `next_opening_requirements` đi vào handoff(N).

### Bước 7 – Validate

1. **(a) Xác định** – `state_validator` V01–V15 (F09). Phân loại lỗi:
   - Lỗi do settle ghi sai (V01–V03, V06, V08–V13, V15) → **settle lại** một lần trong vòng hiện tại, kèm danh sách lỗi làm phản hồi.
   - Lỗi do văn bản mâu thuẫn state (V04 nhân vật chết hành động, V05 thời gian lùi không phải hồi tưởng, V07 dùng bí mật chưa biết) với bằng chứng hợp lệ → finding `fact`/`timeline` `blocker` gắn `paragraph_id` → sửa văn bản.
   - V14 → `hook_overdue` `major` (báo cáo, không chặn).
2. **(b) LLM** – chỉ khi (a) không còn lỗi: `longform.validator` so state cũ/delta/văn bản, trả `LLMValidation`. Host xác minh `quote` thuộc đúng đoạn (F09 `verify_quote`), loại bỏ issue không xác minh được (ghi `unverified` vào trace). `missing_change`/`wrong_change`/`unsupported_change` → settle lại (dùng chung lượt settle lại ở trên, tối đa 1/vòng); `contradiction_with_state` → `fact` `blocker`; `timeline_conflict` → `timeline` `blocker`; `secret_leak` → `fact` `blocker`.
3. Settle lại xong vẫn lỗi xác định → coi như `blocker` của vòng này (`kind=fact`, nguồn `validator`).

### Bước 8 – Seam check (`seam_check.py`)

- Vào: `ending_state(N-1)`, 3 đoạn cuối của `tail_text(N-1)`, `plan.opening`, cửa sổ mở chương = các đoạn đầu cho tới ≥ `seam_opening_window_units` âm tiết.
- Vai trò Mối nối & Review; `longform.seam_check`; structured `SeamResult`; host xác minh trích dẫn.
- Quy tắc host: `location`/`time`/`present_characters` = `mismatch` → fail; `transition_ok` chỉ hợp lệ khi `plan.opening.transition ≠ none` **và** có trích dẫn tín hiệu chuyển cảnh đã xác minh (vd. "Ba ngày sau,"); `unfinished_actions` = `not_addressed` → fail trừ khi plan ghi `defer_explicit` và văn bản có nhắc; `emotion` = `mismatch` → `major` (không fail).
- Fail → finding `seam` `blocker` trên các đoạn của cửa sổ mở. Chỉ chạy lại ở vòng sau khi cửa sổ mở thay đổi hoặc vòng trước fail.

### Bước 9 – Review (`reviewer.py`)

- Vào: plan, state lọc, handoff, candidate, finding `needs_confirmation` (bước 5 + F08). `longform.reviewer`; structured `ReviewResult`.
- Host: xác minh trích dẫn (FL06 bước 2 – thiếu nguồn → bỏ, ghi `unverified`); gán mức theo bảng; áp `confirmations`; `plan_coverage.events` chưa xảy ra và không có `event.move` trong delta → `missing_event` `blocker`; `premature_ending=true` khi `allowed_ending=false` → `ending` `blocker`.
- Vòng sửa ≥ 1: chế độ "tập trung" – chỉ đoạn đã đổi ± 1 đoạn kề và các blocker còn mở cần xác nhận đã hết.
- Review không khả dụng (provider lỗi sau retry) → `needs_user(REVIEW_UNAVAILABLE)` (Plan §21 "review unavailable"), không tự commit.

### Bước 10 – Sửa cục bộ (`repair.py`)

1. Điều kiện: có `blocker` (mọi nguồn) hoặc seam fail.
2. Giới hạn: `round ≤ max_repair_rounds` (mặc định 2) **và** token đã dùng cho sửa + ước lượng vòng tới ≤ `repair_token_cap`. Vượt → `needs_user(REPAIR_EXHAUSTED)` (Plan §6.2 bước 10: không commit; BE đặt `blocked_needs_resync`).
3. Tập đoạn đích: đoạn của blocker; cửa sổ mở (seam); đoạn lặp (n-gram); đoạn cuối (kết truyện sớm). Thêm đoạn có finding `major` nằm trong tập đích khi `repair_include_major` (gồm cụm sáo – cách gộp yêu cầu "sửa cục bộ" của Plan §6.6 mà không tạo vòng riêng). `missing_event`/`length` dưới sàn cho phép `insert_after` ở bất kỳ đoạn nào.
4. Gọi vai trò **Viết** (giữ giọng văn; model/effort đã ghim) với `longform.repair`: lớp 1, 2 (style anchor), plan, đoạn đích ± 1 đoạn kề (chỉ đọc), finding + gợi ý; đầu ra `RepairOps`.
5. Host áp `apply_ops`: `replace`/`delete` chỉ trên đoạn đích; `insert_after` chỉ khi được phép; văn bản chèn qua `normalize(ai_output)`; ID mới cho đoạn chèn; đoạn ngoài phạm vi giữ nguyên từng byte (Plan §23.1.B); tỷ lệ đoạn thay đổi ≤ `repair_max_changed_ratio`, vượt → bỏ kết quả vòng đó, `needs_user(REPAIR_SCOPE_EXCEEDED)`.
6. Candidate mới `kind=repair`, `parent_id`, `round+1` → quay lại bước 5; settle (6) luôn chạy lại vì `paragraph_id`/bằng chứng có thể đổi; seam (8) và review (9) theo quy tắc chạy lại ở trên.

### Hoàn tất

Không còn blocker → `summarize_chapter` (F09) trên candidate cuối → `PipelineResult(ready)`. BE commit (bước 11) hoặc chờ accept theo chế độ.

### Nhịp truyện và chống kết thúc sớm (`pacing.py`, Plan §23.3 #5)

- `events_remaining` = số `story_events` `planned`/`moved` (không tính `dropped`); `chapters_remaining = target_chapters − N + 1`; `ratio = events_remaining / chapters_remaining`; `recommended_events = [⌊ratio⌋, ⌈ratio⌉]`.
- `warning`: `crowded` khi sự kiện gán cho N vượt `⌈ratio⌉ + 1`; `dragging` khi `ratio` dưới ngưỡng thấp cấu hình; `no_material` khi `events_remaining = 0` mà `chapters_remaining > 1` → planner phát triển từ hook đang mở, phát finding `pacing` `major` một lần và kích hoạt xét lại dàn ý.
- Không kết thúc sớm: chặn ở 3 lớp – `plan.allowed_ending` (bước 2), dấu hiệu kết truyện (bước 5), `premature_ending` (bước 9).

### Xét lại dàn ý mỗi K chương (`outline_review.py`, Plan §23.3 #6)

- Kích hoạt sau commit chương N khi `N % outline_review_every_k == 0` (mặc định 10) hoặc ≥ 2 sự kiện chuyển `moved` từ lần xét trước. Dàn ý động theo DOME.
- Vào: synopsis, tóm tắt arc, toàn bộ `story_events` (trạng thái, `locked`), hook mở, `PacingBudget`. Vai trò Lập kế hoạch; structured `OutlineProposal`.
- Áp: `auto` → BE áp thay đổi không đụng sự kiện `locked`, phần còn lại `pending`; `review_each`/`review_every_k` → toàn bộ `pending`, batch dừng `waiting_user` lý do `OUTLINE_REVIEW` (F12). Mọi thay đổi tạo `outline_revision` mới → `input_hash` plan N+1 đổi.

### Style anchor (Plan §23.3 #7)

- Lớp 2 chứa 1–2 đoạn mẫu: ưu tiên `style_profile.voice_samples` (F05, tối đa 2); không có thì đoạn tác giả chọn từ chương đã duyệt. Cố định theo `bible_revision` (không đổi giữa các chương → không phá cache).
- Model Viết đã ghim khác `writer_model_id` của chương N-1 (`chapter_measurements`) → finding `voice` `minor` "đổi model Viết giữa truyện" + `backend.notice`.

### Bước job, checkpoint và điểm resume

| Bước | Checkpoint lưu | Resume |
|---|---|---|
| `gate`, `load` | Cấu hình ghim; `state_hash`, `handoff_revision` | Chạy lại; `state_hash` khác bản ghim → bỏ plan/candidate cũ |
| `plan` | `plan_id`, `input_hash` | Dùng lại nếu hash khớp |
| `compose` | Trace | Chạy lại (xác định) |
| `write` | Candidate `partial`/`ready`, đoạn đã xong, `stop_reason` | `ready` → bỏ qua; `partial` ≥ 1 đoạn và cùng model ghim → `writer_continue` từ partial; không → viết lại (candidate cũ `superseded`) |
| `check` | Findings | Chạy lại |
| `settle` | `SettleOutput` gắn `candidate_id` | Dùng lại nếu candidate không đổi |
| `validate`, `seam`, `review` | Kết quả gắn `candidate_id`, `round` | Dùng lại nếu candidate không đổi |
| `repair` | Candidate `repair` + `round` + token sửa đã dùng | Tiếp từ vòng đã ghi; không reset bộ đếm vòng |
| `summarize_chapter` | Tóm tắt gắn `candidate_id` | Dùng lại |
| `commit` (BE) | — | Idempotent theo `candidate_id` |

Không hứa resume chính xác từng token hoặc tính phí đúng một lần (Plan §4.3).

### Bảo đảm liền mạch N → N+1

| # | Cơ chế | Nơi thực thi |
|---|---|---|
| 1 | N+1 chỉ chạy khi N committed + `state_applied` + `continuity_status=ok`; scheduler chỉ enqueue sau commit; không bao giờ viết trên candidate chưa commit (Plan §4.2) | BE `gate.py`, F12 |
| 2 | `ending_state(N)` sinh ở settle, kiểm V13, lưu cùng transaction với chương; `tail_text(N)` cắt theo đoạn 1.000–2.000 token | Bước 6, F09 `cut_tail`, BE commit |
| 3 | Planner **và** Writer nhận `handoff(N)` + `tail_text(N)` trong phần bảo vệ; plan buộc `opening` nối từ `ending_state` và xử lý từng hành động dở dang | Bước 2–4, F09 Composer |
| 4 | Seam check độc lập đối chiếu 5 khía cạnh; chuyển cảnh phải được plan khai báo và có tín hiệu trong văn bản | Bước 8 |
| 5 | State là việc đã xảy ra **và** việc phải xảy ra (sự kiện của chương, hook đến hạn) – thiếu sự kiện bắt buộc là `blocker` | Bước 1, 2, 9 |
| 6 | Validator xác định trước LLM; mọi op có bằng chứng `paragraph_id`; lỗi fact/timeline/seam/tên riêng chặn commit | Bước 5, 7 |
| 7 | Sửa cục bộ ≤ K vòng, hết vòng thì dừng hẳn (`blocked_needs_resync`) thay vì lưu chương lỗi | Bước 10, BE |
| 8 | Commit nguyên tử; sửa handoff/state/chương cũ của tác giả làm `input_hash` đổi hoặc `stale_from(K)` | BE, F09, F11 |

### Khác biệt so với InkOS

| Điểm yếu InkOS (Review §2.3) | InkOS (đọc code) | WriteStoryApp |
|---|---|---|
| #1 Commit chương khi state lỗi | `pipeline/chapter-truth-validation.ts:99-127`: giữ state N-1, vẫn lưu chương N, N+1 vẫn chạy | Không commit khi validator xác định lỗi; `blocked_needs_resync`; accept kèm ghi chú cũng không vượt được lỗi state |
| #2 Writer không thấy văn bản chương trước | Chỉ Planner nhận (`utils/planning-materials.ts`, `agents/planner.ts:70-78`) | Writer nhận `handoff` + `tail_text` (bảo vệ) |
| #3 Planner nhận toàn văn, vượt ngân sách | Phần bảo vệ quá lớn → throw (`agents/composer.ts`) | `tail_text` có trần 2.000 token; ngân sách từ `max_input_tokens` + soft cap |
| #4 Review không có hiệu lực | Observations không chặn, không sửa | Mức độ do host gán; blocker kích hoạt sửa cục bộ có giới hạn |
| #5 Sửa chương giữa không replay state | Chỉ gắn cờ `upstream-revision` | `stale_from(K)` + resync tuần tự (F11) |
| #8 Plan cũ dùng lại khi retry | Plan không gắn đầu vào | `input_hash`; khác hash → lập lại |
| Validator chỉ dùng LLM, reconcile đúng 1 lần (`agents/state-validator.ts`) | LLM temp thấp | V01–V15 xác định trước, LLM sau, settle lại tối đa 1 lần/vòng |
| Ngân sách `(contextWindow − maxTokens)/2` | `agents/composer.ts:368-389` | `min(max_input_tokens, soft_cap) − biên` (F09) |
| #6, #7, #9 (scheduler, limiter, state 3 nơi) | — | F12 (scheduler/limiter), F09 (snapshot chuẩn + sổ cái cùng transaction) |

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| `longform.planner` | Lập kế hoạch | 4 (sau 1, 2, 3a) | `ChapterPlan` |
| `longform.writer` | Viết chương | 4 (sau 1, 2, 3a, 3b plan) | Văn xuôi theo đoạn |
| `longform.writer_continue` | Viết chương | 4 | Văn xuôi nối tiếp |
| `longform.settler` | Kiểm tra/Settle | 4 (sau 1 rút gọn, 3b candidate) | `SettleOutput` |
| `longform.validator` | Kiểm tra/Settle | 4 | `LLMValidation` |
| `longform.seam_check` | Mối nối & Review | 4 | `SeamResult` |
| `longform.reviewer` | Mối nối & Review | 4 (sau 1, 2, 3a, 3b) | `ReviewResult` |
| `longform.repair` | Viết chương | 4 | `RepairOps` |
| `longform.outline_review` | Lập kế hoạch | 4 | `OutlineProposal` |
| `common.json_fix` | Theo bước gốc | 4 | JSON theo schema gốc |
| `longform.summary_chapter` | Tóm tắt (F09) | 4 | `ChapterSummary` |

Tất cả tiếng Việt, đăng ký trong manifest F08; đoạn văn render dạng `[p:<id>] …`; `prompt_version` ghi vào `job_steps` và trace.

## Model, effort, giới hạn

- Vai trò (Plan §7.1): Lập kế hoạch (plan, outline_review) – model mạnh, effort `high`; Viết chương (write, continue, repair) – model mạnh, `high`; Kiểm tra/Settle (settle, validate) – cân bằng, `medium`; Mối nối & Review (seam, review) – cân bằng, `medium`; Tóm tắt – rẻ, `low`. Giá trị gợi ý, chỉnh sau bộ đánh giá tiếng Việt (F08).
- Model + effort ghim tại `gate` cho cả job (không đổi giữa các bước/vòng → giữ cache, Plan §7.1).
- `max_tokens` vai trò Viết ≥ `length_max × tokens_per_syllable × hệ số dư` (+ phần suy nghĩ nếu effort cao); hệ số là giả định cấu hình. Bị cắt vẫn có viết tiếp.
- Nhiệt độ: chỉ gửi khi model cho phép; mặc định viết cao hơn bước có cấu trúc (giả định, không gửi khi provider không nhận tham số).
- Structured output (Plan §23.3 #2): `capabilities.structured_outputs` → JSON Schema/tool-use; không có → JSON mode + parse + một lần `common.json_fix` + Pydantic; vẫn lỗi → bước thử lại một lần từ checkpoint, rồi `needs_user(STRUCTURED_OUTPUT_INVALID)`.

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Không retry lặp; `needs_user(PROVIDER_REFUSAL)` + gợi ý sửa chỉ dẫn/đổi model; giữ partial (nội dung nhạy cảm vốn có trong kiếm hiệp, trinh thám – §23.3 #3) |
| Bị cắt `max_tokens` | Viết: tiếp tối đa 2 lần rồi `OUTPUT_TRUNCATED`; bước JSON: tăng `max_tokens` một lần trong giới hạn vai trò, rồi xử lý như JSON hỏng |
| JSON không hợp lệ | `common.json_fix` một lần → Pydantic → thử lại bước một lần → `STRUCTURED_OUTPUT_INVALID` |
| Output rỗng | Coi như lỗi transient: thử lại bước một lần; vẫn rỗng → `needs_user(EMPTY_OUTPUT)` |
| 429/5xx/mất mạng | `policies/retry.py` (backoff + jitter, `Retry-After`); hết lượt → BE `waiting_slot` (không fail job) |
| Trích dẫn LLM không khớp văn bản | Bỏ finding/issue, ghi `unverified` (không để LLM bịa bằng chứng làm chặn chương) |
| Delta tham chiếu đoạn bị repair xóa | V08 lỗi → settle lại (bước 6 luôn chạy lại sau repair) |
| Tác giả sửa plan rồi plan vi phạm ràng buộc | Từ chối ở API (BE) bằng cùng kiểm tra bước 2 |
| `settle_author_text` (tác giả sửa candidate) | Candidate `kind=author`, chạy từ bước 5; không gọi repair tự động trên văn bản tác giả – blocker còn lại → `needs_user` |
| Chương 1 | Seam đối chiếu `opening` của nền truyện; không kiểm n-gram |

## Đánh giá

- Chỉ số Plan §9 Giai đoạn 4, tính từ `chapter_measurements`/`findings` trên 3 truyện mẫu × 20 chương (`tests/fixtures/stories/`, ít nhất một tiên hiệp/kiếm hiệp và một ngôn tình hoặc đô thị):

| Chỉ số | Cách tính |
|---|---|
| 0 chương committed `state_applied=false` | Đếm `chapters` committed có `state_applied=false` |
| Seam pass ≥ 95% (sau ≤ 2 vòng) | Số chương seam `pass` ở vòng cuối ≤ 2 / tổng chương |
| 0 tên nhân vật ngoài canon chưa khai báo | Finding `name` (chưa khai báo) còn tồn tại trên revision committed |
| 0 lỗi xưng hô không có sự kiện; không trộn kiểu bỏ dấu | Finding `address` mức cao trên revision committed; `accent_mixed` |
| 100% hook quá hạn được báo | Hook có `due_by < N` chưa đóng ↔ finding `hook_overdue` tương ứng |
| n-gram chương kề dưới ngưỡng | `ngram_overlap_prev` ≤ `ngram_max_overlap` |
| Người đọc chấm từng chương và cả truyện | Phiếu theo kiểu EQ-Bench Longform; ghi tay, không tự động |

- Bộ chạy xác định (CI) dùng mock provider với `scripted_outputs` (kể cả seam fail, refusal, cắt output, JSON hỏng – theo tests README); bộ `live` chạy khi cấu hình rõ. Không công bố số liệu trước khi đo.
- Theo dõi thêm (không phải tiêu chí): số vòng sửa trung bình, token theo bước, `cache_read_tokens`, tỷ lệ finding bị tác giả bác (báo nhầm).

## Việc cần làm

- [ ] Contract `generation.py`, `longform.py`, `paragraphs.py` (`apply_ops` dùng chung BE).
- [x] `pipeline.py` điều phối 11 bước, checkpoint/resume, cancel và limiter; phần persistence thuộc host.
- [ ] `planner.py` + kiểm tra plan + `input_hash`.
- [ ] `writer.py`: stream, tách đoạn, viết tiếp, lọc meta, chuẩn hóa.
- [ ] `evaluators/deterministic.py` (độ dài, tên, nhân vật chết, n-gram, kết truyện, meta) + nối F08.
- [x] `settlement.py`, `reviewer.py` (validator LLM + review, xác minh trích dẫn), `seam_check.py`.
- [x] `repair.py` + giới hạn vòng/token/phạm vi.
- [x] `pacing.py`, `outline_review.py` (chọn style anchor còn mở).
- [ ] `evaluators/structured_output.py` + fallback.
- [ ] 10 template `longform.*` + snapshot test.
- [ ] Kịch bản mock provider cho T05/T06/T15 và bộ chỉ số §9.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | `input_hash` đổi khi một thành phần đổi; dùng lại plan khi khớp | `ai/tests/unit/longform/test_plan_hash.py` |
| unit | Kiểm tra plan: hook đến hạn, `allowed_ending`, `opening` | `ai/tests/unit/longform/test_plan_checks.py` |
| unit | Tách đoạn khi stream; ghép viết tiếp giữa đoạn; cắt trùng | `ai/tests/unit/longform/test_writer_stream.py` |
| unit | Kiểm tra xác định bước 5 (từng mục, dương/âm) | `ai/tests/unit/evaluators/test_deterministic_chapter.py` |
| unit | `apply_ops`: đoạn ngoài phạm vi giữ nguyên, ID mới, trần tỷ lệ | `ai/tests/unit/longform/test_repair_ops.py` |
| unit | Quy tắc seam: `transition_ok` cần plan + tín hiệu; cảm xúc chỉ `major` | `ai/tests/unit/longform/test_seam_rules.py` |
| unit | Gán mức độ theo loại; LLM không nâng/hạ được | `ai/tests/unit/longform/test_severity_policy.py` |
| unit | `pacing.compute` các trường hợp crowded/dragging/no_material | `ai/tests/unit/longform/test_pacing.py` |
| contract (mock provider) | Thành công 1 vòng; seam fail → sửa → pass; hết vòng → `REPAIR_EXHAUSTED` | `ai/tests/contract/longform/test_pipeline_paths.py` |
| contract (mock provider) | Refusal, cắt `max_tokens` 1/3 lần, JSON hỏng, output rỗng, mất kết nối giữa stream | `ai/tests/contract/longform/test_pipeline_provider_errors.py` |
| contract (mock provider) | Resume từ từng checkpoint cho kết quả tương đương | `ai/tests/contract/longform/test_pipeline_resume.py` |
| integration | 3 truyện × 20 chương (mock, song song với F12) → chỉ số §9 | `tests/integration/test_continuity_metrics.py` |

Luồng: [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md), [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md), [T15](../../tests/flows/T15-loi-provider.md), [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md), [T07](../../tests/flows/T07-auto-write-mot-truyen.md), [T08](../../tests/flows/T08-da-truyen-dong-thoi.md).

## Tên mới đề xuất

- File: `contracts/longform.py`, `evaluators/structured_output.py` (đã có trong Arch) dùng như mô tả; `policies/limits.py` mở rộng.
- Contract: `WriteSettings`, `PinnedRoles`, `ResumePoint`, `PipelineResult`, `ChapterPlan`, `PacingBudget`, `SettleOutput`, `LLMValidation`, `SeamResult`, `ReviewResult`, `RepairOps`, `ParagraphOp`, `OutlineProposal`, `LoadedContext`.
- Loại finding mới: `ending`, `repetition`, `missing_event`, `meta_leak`, `ooc`, `voice`, `pacing`, `length`, `hook_overdue`, `new_character_unplanned` (Plan §5 chỉ có `fact/timeline/name/address/seam/POV/slop/craft`).
- Mã lý do: `REPAIR_EXHAUSTED`, `REPAIR_SCOPE_EXCEEDED`, `REVIEW_UNAVAILABLE`, `EMPTY_OUTPUT`, `OUTLINE_REVIEW`.
- Cấu hình: các khóa `WriteSettings` ngoài Plan (`length_tolerance`, `length_hard_floor_ratio`, `repair_token_cap`, `repair_max_changed_ratio`, `repair_include_major`, `max_continuations`, `seam_opening_window_units`, `ngram_n`, `ngram_max_overlap`, `verbatim_run_units`, `hooks_due_lookahead`, `strict_new_characters`).
- Template: `longform.writer_continue`, `longform.validator`, `longform.repair`, `longform.outline_review` (ngoài các vai trò Plan nêu).
- Thành phần mở rộng của `input_hash`: `story_events_revision`, `bible_revision`, `brief_hash`, `prompt_version`.
- `GenerationRequest.response_schema` và `GenerationRequest.json_mode` chuyển schema JSON khi provider hỗ trợ hoặc bật JSON mode khi fallback.
