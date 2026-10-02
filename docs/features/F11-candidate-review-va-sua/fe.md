# F11 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/works/$workId/review/$chapterNo?left=&right=` | Review/Diff (UI §5.5) | `left`/`right` = `rev:<id>` hoặc `cand:<id>`; mặc định bản hiện tại ↔ candidate `ready` mới nhất |
| `/works/$workId/history/$chapterNo` | Lịch sử phiên bản + candidate | Dùng chung `DiffView`; restore thuộc F07 |
| `/works/$workId?tab=review&chapter=N` | Tab Review panel phải (UI §5.2) | Findings của chương, bấm để nhảy tới đoạn |
| `/works/$workId?tab=ai&chapter=N` | Tab AI | Form sửa có phạm vi, CandidateStream (F10), nút Xem diff/Nhận/Bỏ |

## Component

```text
fe/src/features/review/
  pages/ReviewDiffPage.tsx, HistoryPage.tsx
  components/DiffToolbar.tsx, DiffView.tsx, ParagraphDiffRow.tsx, ChecksBar.tsx,
             AcceptBar.tsx, ConflictDialog.tsx, FindingsPanel.tsx, FindingItem.tsx,
             CandidateHistoryList.tsx
  workers/diff.worker.ts
  hooks/useParagraphDiff.ts, useAcceptCandidate.ts, useReviewShortcuts.ts
  api/candidates.ts, findings.ts
fe/src/features/ai_workspace/components/ReviseRequestForm.tsx
fe/src/features/continuity/components/ContinuityBanner.tsx, ResyncDialog.tsx,
                           ChapterStructureMenu.tsx
```

| Component | Trách nhiệm |
|---|---|
| `DiffToolbar` | Chọn hai bản so sánh (revision/candidate), Song song/Inline, mức Từ/Câu, tổng `+x / −y âm tiết` |
| `DiffView` | Danh sách đoạn ảo hóa (TanStack Virtual); ghép đoạn theo `paragraph_id`, đoạn chèn/xóa hiện riêng |
| `ParagraphDiffRow` | Diff mức từ trong một đoạn (`<ins>/<del>`), nút [✓] [✗] chọn nhận từng đoạn, cảnh báo "đoạn gốc có định dạng sẽ mất" |
| `diff.worker.ts` | jsdiff `diffWordsWithSpace` với `intlSegmenter: new Intl.Segmenter('vi', {granularity: 'word'})`, `diffSentences` khi mức Câu (UI §3) |
| `ChecksBar` | Tóm tắt `check_summary` + findings của candidate (⛔/⚠/✓ có chữ, không chỉ màu) |
| `AcceptBar` | [Nhận tất cả Ctrl+Enter] [Bỏ Esc] [Nhận các đoạn đã chọn] |
| `ConflictDialog` | Diff 3 bên cho từng `conflicts[]`: Gốc / Bản hiện tại / Candidate; chọn giữ bản nào hoặc sửa tay; nút "Nhận phần không xung đột" (`clean_paragraph_ids`) |
| `FindingsPanel` | Lọc theo mức/nguồn/trạng thái; Resolve, Dismiss (ghi chú bắt buộc với blocker), "Sửa lỗi này" (mở form revise `spot_fix` kèm `finding_ids`) |
| `ReviseRequestForm` | Phạm vi lấy từ selection editor: vùng chọn / các đoạn / cả chương; mode; chỉ dẫn; gửi `base_revision_id` |
| `ContinuityBanner` | Banner trên editor khi `blocked_needs_resync` hoặc `stale_from` (UI §5.2) với nút [Xem lỗi] [Sửa tay rồi settle lại] [Chấp nhận kèm ghi chú] [Settle lại từ Ch.K] |
| `ResyncDialog` | Gọi `resync` `dry_run` → hiện phạm vi K..N, ước tính chi phí; [Chạy resync] hoặc [Bỏ qua có xác nhận] (`continuity/acknowledge`) |
| `ChapterStructureMenu` | Chèn/xóa/đổi thứ tự trên cây chương; disable kèm tooltip khi truyện đang chạy; confirm nêu "các chương từ K cần đồng bộ lại" |
| `CandidateHistoryList` | Mọi candidate của chương với trạng thái, loại, mode, thời điểm; mở diff |

## State và dữ liệu

- TanStack Query keys: `['candidates', chapterId, status]`, `['candidate', candidateId]`, `['findings', workId, filters]`, `['continuity', workId]`, `['revisions', chapterId]` (F07), `['revisionDiff', chapterId, a, b]` (F07).
- Zustand `useReviewStore` (theo `chapterId`): `selectedParagraphIds`, `viewMode`, `granularity`, `focusedParagraphId`. Không lưu nội dung chương trong store.
- API dùng: `GET /v1/chapters/{id}/candidates`, `GET /v1/candidates/{id}`, `POST /v1/candidates/{id}/accept|reject`, `POST /v1/jobs` (`revise`, `review`), findings API, `GET /v1/works/{id}/continuity`, `POST /v1/works/{id}/resync`, `POST /v1/works/{id}/continuity/acknowledge`, cấu trúc chương.
- Event SSE dùng (`/v1/events`): `candidate.ready`, `candidate.updated` → invalidate `['candidates', …]`; `finding.added|updated` → invalidate findings; `work.continuity` → `['continuity', workId]` + banner; `chapter.committed` → revisions + editor reload; `token.delta` (CandidateStream, F10); `job.step` (tiến độ resync).

Luồng nhận candidate (`useAcceptCandidate`):

1. `await editor.flushAutosave()` (F07); nếu lỗi lưu → dừng, hiện lỗi.
2. Gửi `{expected_revision_id: currentRevisionId, paragraph_ids?}`.
3. 409 `REVISION_CONFLICT` → mở `ConflictDialog` với `detail`; gửi lại kèm `resolutions` và `expected_revision_id = detail.current_revision_id`.
4. Thành công → nạp revision mới vào editor bằng **một transaction** (UI §5.5) để Ctrl+Z hoàn tác được một bước; toast sonner "Đã nhận N đoạn"; nếu có `followup_job_id` hiện "Đang settle lại chương…".

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton danh sách đoạn; worker diff đang chạy → spinner nhỏ trên từng đoạn |
| Rỗng | "Chưa có bản AI nào cho chương này" + nút "Yêu cầu AI sửa" |
| Candidate `streaming` | Diff khóa, hiện "AI đang viết…"; nút Nhận disable |
| Candidate `partial` | Banner "Bản nháp dở (bị dừng)", chỉ xem/bỏ |
| Lỗi `REVISION_CONFLICT` | `ConflictDialog` |
| Lỗi `CHAPTER_IS_BASE` | "Chương này đang làm nền cho chương N" + nút "Tạm dừng để sửa" (F12) |
| Lỗi `WORK_RUNNING` | Toast + nút mở Phòng viết |
| Lỗi `WORK_BLOCKED` | Mở FindingsPanel lọc blocker |
| Thành công | Toast, editor cập nhật, candidate chuyển nhãn "Đã nhận" |

## Tương tác, phím tắt, khả năng tiếp cận

- Ctrl+Enter: nhận (tất cả, hoặc các đoạn đã chọn nếu có chọn); Esc: bỏ candidate – thực hiện sau 5 giây kèm toast "Hoàn tác" (gửi `reject` khi hết hạn) (UI §8).
- Đề xuất trong màn Review: `J`/`K` đoạn thay đổi kế/trước; `Space` chọn/bỏ chọn đoạn đang focus; `A` nhận đoạn đang focus; `X` bỏ đoạn đó. Scope phím theo panel (react-hotkeys-hook), không kích hoạt khi focus trong ô nhập.
- `aria-label` tiếng Việt cho [✓]/[✗]; diff dùng `<ins>/<del>` có `aria-label` "thêm"/"xóa"; trạng thái luôn có icon + chữ.
- Bấm finding → `?chapter=N` + cuộn editor tới `paragraph_id`, highlight đoạn 2 giây.

## Chuỗi giao diện (i18n)

Namespace `review`, `continuity`. Ví dụ khóa: `review.accept_all`, `review.accept_selected`, `review.reject_undo`, `review.conflict.title`, `review.conflict.take_current`, `review.conflict.take_candidate`, `review.format_loss_warning`, `continuity.banner.blocked`, `continuity.banner.stale`, `continuity.resync.estimate`, `continuity.acknowledge.confirm`. MVP chỉ có `vi`.

## Việc cần làm

- [ ] `diff.worker.ts` + hook `useParagraphDiff` (hủy job cũ khi đổi lựa chọn).
- [ ] `ReviewDiffPage` song song/inline, ảo hóa, chọn đoạn.
- [ ] `useAcceptCandidate` (flush → accept → conflict → reload một transaction).
- [ ] `ConflictDialog` 3 bên.
- [ ] `FindingsPanel` + dismiss có ghi chú + "Sửa lỗi này".
- [ ] `ReviseRequestForm` lấy selection Tiptap → `scope`.
- [ ] `ContinuityBanner`, `ResyncDialog`, `ChapterStructureMenu`.
- [ ] `HistoryPage` dùng chung `DiffView` với F07.
- [ ] Phím tắt + kiểm tra không xung đột với editor.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Ghép đoạn theo `paragraph_id`, đoạn chèn/xóa | `fe/src/features/review/hooks/useParagraphDiff.test.ts` |
| component | `ConflictDialog` chọn bản và gửi `resolutions` | `fe/src/features/review/components/ConflictDialog.test.tsx` |
| component | Esc hoàn tác trong 5 giây không gọi `reject` | `fe/src/features/review/components/AcceptBar.test.tsx` |
| component | Banner theo `continuity_status` | `fe/src/features/continuity/components/ContinuityBanner.test.tsx` |
| e2e (mock backend) | Nhận từng đoạn; sửa tay song song → 409 → giải quyết (T11) | `fe/tests/e2e/candidate-conflict.spec.ts` |
| e2e (mock backend) | Sửa chương cũ → banner stale → resync dry-run → chạy (T10) | `fe/tests/e2e/stale-resync.spec.ts` |

## Tên mới đề xuất

- Query param `left`/`right` của route Review/Diff.
- Component/hook: `ConflictDialog`, `ResyncDialog`, `ChapterStructureMenu`, `useAcceptCandidate`, `useReviewStore`.
- Phím tắt `J`/`K`/`Space`/`A`/`X` trong màn Review (chưa có ở UI §8).
- Namespace i18n `review`, `continuity`.
