# F11 — AI

## Module và file

```text
ai/src/writestory_ai/
  contracts/paragraphs.py          ParagraphText, ParagraphOp, ParagraphOps (§23.1.B) – dùng chung F10
  contracts/revise.py              ReviseInput, ReviseOutput, ReviseScope
  contracts/review.py              ReviewInput, FindingDraft, ReviewOutput
  contracts/resettle.py            ResettleInput, ResettleOutput (dùng StateDelta của F09)
  workflows/longform/revise.py     Sửa có phạm vi theo yêu cầu tác giả
  workflows/longform/reviewer.py   Review-only (chung với bước 9 của F10)
  workflows/longform/resettle.py   Settle lại văn bản có sẵn cho resync
  workflows/longform/repair.py     Sửa cục bộ trong pipeline (F10) – chung định dạng ops
  languages/vi/prompts/longform/   revise.j2, review.j2, resettle.j2
```

## Contract (Pydantic)

```text
ReviseScope:   type: "selection" | "paragraphs" | "chapter"
               paragraph_ids: list[str]
               selection?: {paragraph_id, start, end}      # chỉ khi vùng chọn nằm trong 1 đoạn
ReviseInput:   work_id, chapter_no, language, mode: spot_fix|polish|rewrite|rework,
               scope: ReviseScope, author_instruction,
               paragraphs: list[{paragraph_id, text, editable: bool}],
               findings: list[{id, kind, severity, message, evidence}],
               state_before: StoryState (snapshot K-1), handoff_prev: Handoff(K-1),
               next_opening?: str (đầu chương K+1 nếu K không phải chương mới nhất),
               style_profile, address_rules, length_target, pinned: PinnedModel
ReviseOutput:  ops: list[ParagraphOp{paragraph_id, action: replace|insert_after|delete, text}],
               selection_replacement?: str,
               addressed_finding_ids: list[str], new_entities: list[{name, kind, note}],
               rationale: str (tiếng Việt, ngắn), usage: Usage
ReviewInput:   chapter paragraphs [p:id], state_before, handoff_prev, plan?, canon slice, rubric
ReviewOutput:  findings: list[FindingDraft{kind, severity, message, evidence[{paragraph_id, quote}],
               suggestion?}], usage
ResettleInput: paragraphs, state_before, handoff_prev, story_events của chương
ResettleOutput: delta: StateDelta, ending_state, open_threads, next_opening_requirements, usage
```

AI không biết revision ID hay DB; BE ghim revision và dịch kết quả thành candidate/findings (Arch §6).

## Workflow

Revise (Plan §6.3, FL06 bước 3–4):

1. BE dựng `ReviseInput`; toàn chương gửi dạng `[p:abc123] nội dung…`, đoạn ngoài phạm vi đánh dấu `[khóa]` để giữ mạch đọc nhưng không được sửa.
2. Context theo lớp (Plan §6.4): lớp 1–2 như pipeline (giữ cache); lớp 3: `state_before`, `handoff_prev`, `next_opening` (bảo vệ, không nén) và findings mục tiêu; lớp 4: chỉ dẫn tác giả + mode.
3. `scope.type = selection` trong một đoạn → yêu cầu `selection_replacement` (chỉ đoạn chữ thay thế); BE ghép `prefix + replacement + suffix`. Vùng chọn nhiều đoạn → mở rộng thành `paragraphs`.
4. Gọi model vai trò **Viết chương** (writer) với structured output `ReviseOutput`.
5. Hậu kiểm trong AI (`evaluators/deterministic.py` + `languages/vi/checks.py`): op chỉ trên `editable`; không trùng `paragraph_id`; `rework` phải giữ các `story_events` đã done của chương (so với `state_before` + delta cũ do BE cung cấp) và đoạn kết tương thích `next_opening` nếu có. Vi phạm → một lần yêu cầu sửa; vẫn sai → BE loại op vi phạm (be.md).

Review-only (FL06 bước 2): vai trò **Mối nối/Review**; mỗi finding bắt buộc `evidence` có `paragraph_id` + quote ngắn; BE xác minh quote. Không được sinh văn bản sửa (review-only không ngầm sửa prose).

Resettle (resync, Plan §6.2): vai trò **Kiểm tra/Settle**; giống bước Settle của F10 nhưng đầu vào là văn bản đã commit; sau đó BE chạy validate xác định + seam (vai trò Mối nối) + tóm tắt (vai trò Tóm tắt) bằng workflow của F10/F09. Không có bước Write/Repair.

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| `longform.revise` (biến thể theo mode) | writer | Lớp 1–2 chung pipeline; lớp 3 theo chương | `ReviseOutput` JSON |
| `longform.review` | seam/review | Lớp 1–2; lớp 3 state + handoff | `ReviewOutput` JSON |
| `longform.resettle` | checker/settle | Lớp 1–2; lớp 3 state K-1 | `ResettleOutput` JSON |

Template Jinja2 sandbox, manifest id/version/checksum trong `languages/vi/prompts/` (Plan §23.3 #8); version ghi vào `job_steps`.

## Model, effort, giới hạn

- Vai trò (Plan §7.1): revise → writer (gợi ý effort `high`); review → seam/review (`medium`); resettle → checker/settle (`medium`), tóm tắt → summary (`low`). Model + effort ghim lúc job bắt đầu (§7.1).
- `max_tokens`: revise phạm vi đoạn ≈ 2× độ dài phạm vi; `rework`/cả chương ≥ độ dài mục tiêu chương + phần suy nghĩ khi effort cao (giả định, chỉnh sau đo).
- Structured output: dùng structured outputs/tool-use khi `capabilities.structured_outputs`; nếu không: JSON mode + parse + một lần yêu cầu sửa; vẫn lỗi → `STRUCTURED_OUTPUT_INVALID` (Plan §23.3 #2).

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | Không retry lặp; trả `PROVIDER_REFUSAL`, job `waiting_user` kèm gợi ý chỉnh chỉ dẫn/đổi model (§23.3 #3) |
| Bị cắt `max_tokens` | Revise: viết tiếp tối đa 2 lần rồi ghép ops; JSON bị cắt → yêu cầu lại phần còn thiếu theo `paragraph_id`; vẫn lỗi → `OUTPUT_TRUNCATED` |
| JSON không hợp lệ | Một lần sửa; sau đó `STRUCTURED_OUTPUT_INVALID` |
| Op tham chiếu `paragraph_id` không tồn tại | Loại op, ghi trace |
| Review trả finding không có evidence | Loại finding (không lưu nhận xét không bằng chứng) |
| Resettle trả delta vi phạm validator | Không tự sửa văn bản; BE ghi findings `validator` và chặn |

## Đánh giá

- Chỉ số: tỉ lệ op ngoài phạm vi (mục tiêu 0 sau hậu kiểm); tỉ lệ finding có quote xác minh được; sau revise `spot_fix`, finding mục tiêu không còn khi chạy lại check; độ dài thay đổi trong ngưỡng mode.
- Bộ dữ liệu mẫu: `tests/fixtures/stories/` (chương có lỗi xưng hô, tên riêng, seam cài sẵn), `tests/fixtures/state/`.

## Việc cần làm

- [ ] `contracts/paragraphs.py`, `revise.py`, `review.py`, `resettle.py`.
- [ ] `workflows/longform/revise.py` với 4 mode và xử lý vùng chọn.
- [ ] `reviewer.py` review-only dùng chung với F10.
- [ ] `resettle.py`.
- [ ] Template `revise.j2`, `review.j2`, `resettle.j2` tiếng Việt + snapshot test.
- [ ] Hậu kiểm phạm vi/`rework` trong evaluator.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Kiểm tra op chỉ trên đoạn editable; ghép vùng chọn | `ai/tests/unit/longform/test_revise_scope.py` |
| unit | Snapshot prompt đã render cho 4 mode | `ai/tests/unit/prompts/test_revise_snapshot.py` |
| contract (mock provider) | Revise: JSON hỏng → sửa một lần; refusal; cắt `max_tokens` | `ai/tests/contract/test_revise_workflow.py` |
| contract (mock provider) | Review trả finding thiếu evidence bị loại | `ai/tests/contract/test_review_workflow.py` |
| contract (mock provider) | Resettle trả `StateDelta` hợp lệ trên chương mẫu | `ai/tests/contract/test_resettle_workflow.py` |

## Tên mới đề xuất

- Contract: `ReviseScope`, `ReviseInput`, `ReviseOutput`, `ReviewInput`, `ReviewOutput`, `FindingDraft`, `ResettleInput`, `ResettleOutput`; trường `selection_replacement`, `next_opening`.
- File: `contracts/revise.py`, `contracts/review.py`, `contracts/resettle.py`, `workflows/longform/revise.py`, `workflows/longform/resettle.py`.
- Template ID: `longform.revise`, `longform.review`, `longform.resettle`.
