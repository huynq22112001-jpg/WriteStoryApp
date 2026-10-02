# F10 — Frontend

Nguyên tắc (UI §1, §6): AI không ghi thẳng vào editor; token đi vào `CandidateStream` riêng; mạch truyện nhìn thấy và sửa được ở tab "Nối"; trạng thái bị chặn luôn có lý do và hành động.

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/works/$workId?tab=ai&chapter=N` | Workspace → tab **AI** | Ô ý đồ chương/chỉ dẫn, nút "Viết tiếp", `PipelineProgress`, `CandidateStream`, card candidate |
| `/works/$workId?tab=handoff&chapter=N` | Workspace → tab **Nối** | Handoff của chương trước, kết quả seam của chương hiện tại, hook đến hạn (UI §5.2, Plan §23.4 #11) |
| `/works/$workId` (mọi tab) | `BlockedBanner` phía trên editor | Khi `blocked_needs_resync` (F10) hoặc `stale_from(K)` (F11 dùng chung component) |
| `/writing-room` (F12) | Cột "Pipeline" | Dùng `PipelineStepsCompact` của F10 |

## Component

```text
fe/src/features/ai_workspace/
  components/AiPanel.tsx
  components/WriteRequestForm.tsx
  components/PipelineProgress.tsx
  components/PipelineStepsCompact.tsx
  components/CandidateStream.tsx
  components/CandidateCard.tsx
  hooks/useWriteChapter.ts
  hooks/useCandidateStream.ts
  model/pipelineSteps.ts
fe/src/features/continuity/
  components/HandoffPanel.tsx
  components/EndingStateView.tsx
  components/HandoffEditForm.tsx
  components/TailTextPreview.tsx
  components/SeamResultCard.tsx
  components/DueHooksList.tsx
  components/BlockedBanner.tsx
  components/AcceptWithNoteDialog.tsx
  hooks/useContinuity.ts, useHandoff.ts, useSeamResult.ts
```

| Component | Trách nhiệm |
|---|---|
| `WriteRequestForm` | Ý đồ chương (brief), chỉ dẫn một lần, nút "Viết tiếp Ch.N" (`POST /v1/jobs {type:"write"}` + `idempotency_key`); vô hiệu khi `continuity_status ≠ ok` kèm lý do; hiển thị model/effort sẽ dùng cho vai trò Viết |
| `PipelineProgress` | Stepper dọc: Cổng vào ▸ Tải ▸ Kế hoạch ▸ Ngữ cảnh ▸ Viết ▸ Kiểm tra ▸ Settle ▸ Xác thực ▸ Mối nối ▸ Review ▸ Sửa ↻ k/K ▸ Tóm tắt ▸ Lưu; bước hiện tại đậm, bước lỗi ⛔ kèm `reason_code`, bước bỏ qua (dùng lại plan) ghi "dùng lại"; nút Dừng (`/jobs/{id}/cancel`) |
| `PipelineStepsCompact` | 6 nhóm như UI §5.3: Kế hoạch (gate, load, plan, compose) ▸ Viết ▸ Kiểm tra (check, settle, validate) ▸ Nối (seam) ▸ Review (review, repair ↻) ▸ Lưu (summarize, commit) |
| `CandidateStream` | Hiển thị văn bản đang sinh theo đoạn (Noto Serif, chỉ đọc); buffer ref + flush mỗi `requestAnimationFrame`/50–100 ms (UI §6); tự cuộn có thể tắt; khi repair: hiển thị bản mới, đoạn thay đổi được đánh dấu |
| `CandidateCard` | Sau `candidate.ready`: độ dài (âm tiết), số finding theo mức, seam ✓/⛔, `ContextTraceSummary` (F09) "Đã dùng ngữ cảnh: …", nút [Xem diff] [✓ Nhận] [✗ Bỏ] (F11) |
| `HandoffPanel` | Gộp `EndingStateView` + `TailTextPreview` + `SeamResultCard` + `DueHooksList`; nút "Sửa bản giao nối" |
| `EndingStateView` | 📍 địa điểm, 🕒 thời điểm truyện, 👥 nhân vật có mặt + tình trạng/cảm xúc/đang làm gì, ⏸ hành động dở dang, cảm xúc chủ đạo, POV; luồng mở (`open_threads`), yêu cầu mở chương sau |
| `HandoffEditForm` | react-hook-form + zod theo `EndingState`; chọn nhân vật/địa điểm từ canon; gửi `PUT /handoff` với `expected_handoff_revision`; ghi chú "Kế hoạch chương sau sẽ được lập lại"; nếu đổi vị trí nhân vật, hỏi có tạo thay đổi state kèm theo (F09 `/state/deltas`) |
| `TailTextPreview` | Đuôi chương trước nguyên văn (thu gọn), số token, nhãn "cắt trong đoạn" nếu có |
| `SeamResultCard` | 5 khía cạnh (địa điểm, thời điểm, người có mặt, cảm xúc, hành động dở dang): ✓ khớp / ↪ chuyển cảnh hợp lệ / ⚠ / ⛔ lệch, kèm trích dẫn → bấm nhảy đoạn; số vòng sửa |
| `DueHooksList` | Hook `due_by_chapter ≤ N` (+ sắp đến hạn), quá hạn có ⚠ (dữ liệu F09 `/memory`) |
| `BlockedBanner` | Nội dung theo `work.continuity` (UI §5.2): "⛔ Mạch truyện bị chặn ở Ch.N: <lý do> (k vòng sửa chưa đạt)" + [Xem lỗi] [Sửa tay rồi settle lại] [Chấp nhận kèm ghi chú] [Settle lại từ Ch.N] |
| `AcceptWithNoteDialog` | Liệt kê finding sẽ bỏ qua; bắt buộc ghi chú; nếu API trả `WORK_BLOCKED` `STATE_INVALID` → giải thích "State sau chương không hợp lệ, không thể chấp nhận; hãy sửa hoặc settle lại" |

## State và dữ liệu

- TanStack Query keys: `['works', workId, 'continuity']`, `['chapters', chapterId, 'handoff']`, `['chapters', chapterId, 'plan']`, `['chapters', chapterId, 'seam']`, `['chapters', chapterId, 'candidates']` (F11), `['jobs', jobId]`.
- Zustand (feature `jobs`, F01/F12): `useStreamStore` theo `workId` – `{jobId, step, round, maxRounds, candidateId, paragraphs (ref buffer), lastSeq}`; selector hẹp để chỉ `CandidateStream` của truyện đang mở re-render.
- API dùng: `POST /v1/jobs`, `POST /v1/jobs/{id}/cancel|resume`, `GET /v1/works/{id}/continuity`, `GET|PUT /v1/chapters/{id}/handoff`, `GET /v1/chapters/{id}/plan|seam`, `GET /v1/chapters/{id}/candidates`, `POST /v1/candidates/{id}/accept|reject`, `GET /v1/works/{id}/findings` (xem [be.md](./be.md#api)).
- Event SSE (`/v1/events?works=<workId>`):

| Event | Xử lý FE |
|---|---|
| `job.step` | Cập nhật `PipelineProgress`/`PipelineStepsCompact`; `round`/`max_rounds` cho "↻ k/K" |
| `token.delta` | Nối vào buffer theo `candidate_id`; bỏ delta có `offset` đã nhận (chống trùng khi reconnect) |
| `candidate.ready` | Thay buffer bằng bản đầy đủ từ `GET /candidates` (nguồn chuẩn), hiện `CandidateCard` |
| `finding.added` | Invalidate findings chương; badge số finding |
| `chapter.committed` | Invalidate chapters/continuity/handoff/state/memory; toast "Đã lưu Ch.N"; xóa stream store của job |
| `work.continuity` | Invalidate continuity; hiện/ẩn `BlockedBanner`; vô hiệu/kích hoạt nút Viết tiếp |

Reconnect: `token.delta` không được replay (Plan §23.1.C) → khi nối lại thấy `seq` hụt, gọi `GET /v1/chapters/{id}/candidates` lấy partial đã checkpoint rồi tiếp tục nhận delta mới.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton tab Nối/AI |
| Rỗng | Chương 1: tab Nối hiển thị "Mở đầu truyện – dựa trên nền truyện" thay cho handoff; chưa có candidate: hướng dẫn nhập ý đồ chương |
| Chờ | `waiting_slot` với lý do (provider đầy, hết ngân sách, khóa truyện, vault khóa) + đếm ngược khi có (Plan §23.2 #8) |
| Lỗi (`code`) | `WORK_BLOCKED` → banner; `CHAPTER_RANGE_CONFLICT` → "Chương kế tiếp là Ch.N" + nút chuyển; `PROVIDER_REFUSAL` → "Model từ chối viết đoạn này" + [Sửa chỉ dẫn] [Đổi model vai trò Viết]; `OUTPUT_TRUNCATED` → giữ partial + [Viết tiếp] (`resume continue`); `STRUCTURED_OUTPUT_INVALID` → [Thử lại] [Đổi model]; `CONTEXT_PROTECTED_OVER_BUDGET` → gợi ý chọn model context lớn hơn/rút gọn; `REVISION_CONFLICT` khi sửa handoff → tải lại |
| Thành công | Toast, tab Nối cập nhật handoff mới, `PipelineProgress` thu gọn |

## Tương tác, phím tắt, khả năng tiếp cận

- Ctrl+Enter / Esc trên `CandidateCard`: nhận / bỏ (UI §8, thực thi ở F11).
- Chương N-1 khi N đang viết: editor read-only + nút "Tạm dừng để sửa" (Plan §23.4 #3; F11 sở hữu, F10 cung cấp trạng thái job).
- `PipelineProgress` dùng `aria-live="polite"` thông báo đổi bước, không đọc từng token.
- Trạng thái luôn có icon + chữ (✓ / ⚠ / ⛔ / ⏳ / ↻).
- `CandidateStream` không giành focus; người dùng vẫn gõ trong editor khi stream chạy.

## Chuỗi giao diện (i18n)

Namespace `ai`, `continuity`, `jobs`. Ví dụ khóa:

- `ai:write.button` ("Viết tiếp Ch.{{chapter}}"), `ai:write.disabled.blocked`, `ai:candidate.length` ("{{units}} âm tiết"), `ai:candidate.accept`, `ai:candidate.reject`.
- `jobs:step.gate|load|plan|compose|write|check|settle|validate|seam|review|repair|summarize_chapter|commit` (vd. `jobs:step.seam` = "Mối nối"), `jobs:step.round` ("↻ vòng {{round}}/{{max}}"), `jobs:step.reused` ("dùng lại").
- `continuity:banner.blocked` ("Mạch truyện bị chặn ở Ch.{{chapter}}: {{reason}}"), `continuity:reason.REPAIR_EXHAUSTED` ("{{rounds}} vòng sửa chưa đạt"), `continuity:reason.STATE_INVALID`, `continuity:reason.PREV_CHAPTER_DIRTY`, `continuity:action.view_findings|edit_and_resettle|accept_with_note|resettle_from`.
- `continuity:handoff.location|time|present|unfinished|emotion|open_threads|next_requirements`, `continuity:seam.aspect.location|time|present|emotion|unfinished`, `continuity:seam.transition_ok` ("Chuyển cảnh hợp lệ").

## Việc cần làm

- [ ] `model/pipelineSteps.ts`: danh sách bước, nhãn, ánh xạ 13 bước ↔ 6 nhóm.
- [ ] `useWriteChapter`, `useCandidateStream` (buffer, chống trùng, resync khi hụt `seq`).
- [ ] `AiPanel`, `WriteRequestForm`, `PipelineProgress`, `PipelineStepsCompact`, `CandidateStream`, `CandidateCard`.
- [ ] Feature `continuity`: `HandoffPanel` và các thành phần con, `HandoffEditForm`, `BlockedBanner`, `AcceptWithNoteDialog`.
- [ ] Ánh xạ mã lỗi/lý do sang thông báo + nút hành động.
- [ ] Mock backend kịch bản: thành công, seam fail 2 vòng rồi pass, blocked, refusal, truncated.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Ánh xạ bước ↔ nhóm; nhãn vòng sửa | `fe/src/features/ai_workspace/model/pipelineSteps.test.ts` |
| component | `CandidateStream` gộp token, bỏ delta trùng, không re-render editor | `fe/src/features/ai_workspace/components/CandidateStream.test.tsx` |
| component | `BlockedBanner` hiển thị đúng lý do và 4 nút; nút gọi đúng API | `fe/src/features/continuity/components/BlockedBanner.test.tsx` |
| component | `HandoffEditForm` validate, gửi `expected_handoff_revision`, xử lý 409 | `fe/src/features/continuity/components/HandoffEditForm.test.tsx` |
| component | `SeamResultCard` 5 khía cạnh, nhảy đoạn | `fe/src/features/continuity/components/SeamResultCard.test.tsx` |
| e2e (mock backend) | Viết một chương: stream → candidate → commit → tab Nối hiện handoff mới | `fe/tests/e2e/write-chapter.spec.ts` |
| e2e (mock backend) | Seam fail hết vòng → banner → chấp nhận kèm ghi chú bị từ chối do `STATE_INVALID` → settle lại → mở chặn | `fe/tests/e2e/chapter-blocked.spec.ts` |
| e2e (mock backend) | Mất kết nối SSE giữa stream → nối lại, văn bản không lặp | `fe/tests/e2e/stream-reconnect.spec.ts` |

Luồng: [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md), [T17](../../tests/flows/T17-phong-viet-va-su-kien.md), [T15](../../tests/flows/T15-loi-provider.md).

## Tên mới đề xuất

- Component: `AiPanel`, `WriteRequestForm`, `PipelineProgress`, `PipelineStepsCompact`, `CandidateStream` (đã có trong UI), `CandidateCard`, `HandoffPanel`, `EndingStateView`, `HandoffEditForm`, `TailTextPreview`, `SeamResultCard`, `DueHooksList`, `BlockedBanner`, `AcceptWithNoteDialog`; hook `useWriteChapter`, `useCandidateStream`, `useContinuity`, `useHandoff`, `useSeamResult`; store `useStreamStore`.
- Khóa route `tab=handoff` đã có (UI §4); namespace i18n `continuity`, `jobs`.
- Nhãn nhóm bước cho Phòng viết (6 nhóm) và bảng ánh xạ 13 bước.
