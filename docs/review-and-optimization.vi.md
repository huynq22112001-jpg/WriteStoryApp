# Rà soát thiết kế, kiểm chứng và phương án tối ưu WriteStoryApp

Ngày: 02/10/2026. Phạm vi: rà soát [implementation-plan.vi.md](./implementation-plan.vi.md) và [folder-architecture.vi.md](./folder-architecture.vi.md); đối chiếu mã nguồn InkOS tại `E:\Inke\inkos` (v2.0.0); kiểm chứng web các giả định kỹ thuật; đề xuất thiết kế cho hai yêu cầu:

1. **Chạy đồng thời nhiều truyện.**
2. **Trong một truyện, viết từng chương một, nội dung liên tiếp, không đứt mạch.**

Ký hiệu bằng chứng: **[Code]** đã đọc trong source InkOS; **[Web-đọc]** đã mở trang nguồn; **[Web-snippet]** chỉ thấy qua kết quả tìm kiếm; **[Suy luận]** là đề xuất thiết kế, chưa có nguồn sơ cấp.

---

## 1. Kết luận nhanh

| # | Vấn đề | Mức | Hướng xử lý |
|---|---|---|---|
| 1 | Mục 4.2 chỉ cho 1–2 tác vụ sinh văn bản → không đáp ứng "nhiều truyện cùng lúc" | Cao | Scheduler đa truyện: mỗi truyện một hàng đợi tuần tự, N worker chung, xoay vòng công bằng, limiter theo provider (mục 5) |
| 2 | Thiếu "hợp đồng nối chương": Writer của InkOS không nhìn thấy văn bản chương trước, bản thiết kế cũng chưa quy định | Cao | `chapter_handoff` có cấu trúc + đuôi chương nguyên văn vào Writer + kiểm tra mối nối (mục 4) |
| 3 | InkOS commit chương dù state không hợp lệ → sự kiện chương N mất khỏi state, chương N+1 vẫn chạy | Cao | Cổng chặn: chương N+1 chỉ chạy khi chương N `state_applied=true` (mục 4.4) |
| 4 | Chế độ `waiting_user` (duyệt tay) xung đột với auto-write nhiều chương | Trung bình | Chính sách rõ: auto-commit có cổng kiểm tra, hoặc dừng batch tại chương chờ duyệt (mục 4.5) |
| 5 | Data cạnh `.app` trên macOS bị App Translocation phá | Cao (macOS) | Chọn data-root lần đầu, lưu con trỏ; DMG kéo vào Applications (mục 7) |
| 6 | Review chỉ ghi nhận, không có vòng sửa có giới hạn | Trung bình | Review → revise cục bộ tối đa K vòng theo tiêu chí pass/fail (mục 4.3) |
| 7 | Validator chỉ dùng LLM | Trung bình | Thêm kiểm tra xác định (deterministic) trước LLM (mục 4.3) |
| 8 | Không tận dụng prompt caching → chi phí cao khi chạy nhiều truyện | Trung bình | Xếp prompt theo lớp tĩnh → động (mục 6) |
| 9 | Phạm vi 146 hạng mục, 33–45 tuần cho 1 người; MVP 10–13 tuần đã sát | Rủi ro | Khóa MVP vào truyện dài + đa truyện (mục 8) |
| 10 | Mục kiểm chứng web trong tài liệu cũ ghi "chưa xác minh" | — | Đã kiểm chứng lại, xem mục 7 |
| 11 | FTS5 mặc định bỏ sót chữ hai dấu (ộ, ễ…) và không gập `đ→d` (đã chạy thử) | Cao (tìm kiếm) | `remove_diacritics 2` + chuẩn hóa `đ→d` (mục 7.3) |
| 12 | Python 3.13 baseline, KDF Scrypt | Thấp | CPython 3.14, Argon2id (mục 7.1, 7.4) |
| 13 | macOS notarize lỗi vì `.dylib` của PyInstaller onedir không được Tauri ký | Trung bình | Ký từng file trong CI (mục 7.1) |
| 14 | Bộ gõ tiếng Việt trên Tiptap chưa có bằng chứng ổn định | Cao (UX) | Test bắt buộc ở R0 (mục 7.5) |

---

## 2. Luồng xử lý một truyện trong InkOS (đọc từ code)

Gốc: `E:\Inke\inkos\packages\core\src\`. Hàm chính `writeNextChapter` trong `pipeline/runner.ts:1170-1473`. **[Code]**

```text
Tạo sách (1 lần)
  Architect → story_frame.md, volume_map.md, book_rules.md/json
            → state/*.json (lastAppliedChapter = 0, hooks ban đầu)

Mỗi chương N (giữ .write.lock của sách)
  0. N = số chương liên tục trong chapters/index.json + 1
  1. Planner   ← author_intent, current_focus, brief, TOÀN VĂN chương N-1, context đã chọn
               → memo {goal, body, threadRefs}  (runtime/chapter-NNNN.intent.md)
  2. Composer  → ContextPackage: protected (memo, focus, intent, style, canon)
                                 + compressible (summaries, hooks, facts, outline)
               → nếu vượt ngân sách: LLM chọn section rồi nén phần compressible
  3. Writer    pha 1 (temp 0.7) viết {title, content}
               pha 2 settle (temp 0.3) → RuntimeStateDelta {factOps, hookOps, chapterSummary}
  4. Reviewer/ContinuityAuditor → observations (không chặn, không sửa)
  5. StateValidator (LLM, temp 0.1) → consistent? nếu không: reconcile đúng 1 lần
  6. Persist   commitAtomicFileSet: chapter.md, index.json, state/*.json, *.md projection,
               snapshots/N/  (journal + backup + rename)
  7. Đồng bộ artifacts, gửi notification
```

### 2.1 Cơ chế mang nội dung từ chương N sang N+1 trong InkOS

| Cơ chế | Ai nhận | Ghi chú |
|---|---|---|
| Toàn văn chương N-1 (`previousEndingExcerpt`, thực chất cả body) | **Chỉ Planner** | `utils/planning-materials.ts:20-51`, `agents/planner.ts:70-78`. Writer **không** nhận |
| Summary chương N-1 | Luôn được đưa vào | `utils/memory-retrieval.ts:261-265` |
| Summary cũ hơn, hooks chưa resolve | Qua FTS5/BM25 + LLM chọn | Index dựng lại mỗi chương, `limit: 200` |
| Facts có `validUntilChapter`, hooks có `status/lastAdvancedChapter` | Settler/Writer | `state/state-reducer.ts` |
| `current_focus`, `author_intent` | Khối bắt buộc đầu prompt Writer | `agents/writer.ts:466-478` |
| Ngân sách context | `(contextWindow − maxTokens)/2`; vượt thì LLM chọn + nén | `agents/composer.ts:368-389` |

### 2.2 Đồng thời trong InkOS

- Khóa theo sách bằng file `.write.lock` (O_EXCL, heartbeat 30 s, lease 3 phút), fail-fast trả `409 BOOK_BUSY`. `state/manager.ts:129-213`. **[Code]**
- `writeChapters` giữ lock suốt vòng `for` tuần tự; số chương bắt đầu phải đúng chương kế tiếp. `runner.ts:1191-1236`.
- Scheduler: `Promise.all(activeBooks.slice(0, maxConcurrentBooks))`, mặc định 3 sách, 1 chương/chu kỳ, quota 50 chương/ngày lưu trong RAM. `pipeline/scheduler.ts:160`, `models/project.ts:117-131`.
- **Không có semaphore/rate limiter LLM toàn cục**; chỉ retry 2 lần (800/1600 ms) cho 429/5xx. `llm/provider.ts:797-818`.

### 2.3 Điểm yếu InkOS mà bản Python phải sửa

1. **Commit chương khi state lỗi** (`pipeline/chapter-truth-validation.ts:99-127`): state giữ ở N-1, chương N vẫn lưu, chương N+1 vẫn được viết → sự kiện chương N biến mất khỏi bộ nhớ truyện. Đây là nguồn gây "đứt mạch" trực tiếp.
2. **Writer không thấy văn bản chương trước** → câu mở chương dễ lệch cảnh, lệch thời điểm, lặp lại tình tiết.
3. **Planner nhận toàn văn chương trước không cắt** → chương dài làm phần protected vượt ngân sách và throw.
4. **Review không có hiệu lực**: không có ngưỡng kích hoạt sửa.
5. **Sửa chương giữa không replay state** cho các chương sau, chỉ gắn cờ `upstream-revision`.
6. **Scheduler `slice(0, N)`** → truyện xếp sau bị bỏ đói; quota mất khi restart; cron xấp xỉ.
7. **Không giới hạn đồng thời theo provider**, không đọc `Retry-After`.
8. **Plan cũ được dùng lại khi retry** dù state có thể đã đổi.
9. **State lặp 3 nơi** (md, json, snapshot) và index FTS dựng lại mỗi chương.

---

## 3. Rà soát từng phần bản thiết kế hiện tại

| Mục tài liệu | Nhận xét | Đề xuất |
|---|---|---|
| §1 Phạm vi, §3.1 Data cạnh app | Đúng với Windows; **sai với macOS** khi app bị translocate | Xem mục 7, dòng App Translocation |
| §2 Python 3.13 baseline | Cần chốt theo hỗ trợ PyInstaller hiện tại | Xem mục 7 |
| §4.1 Phân loại công việc | Hợp lý | Giữ |
| §4.2 Concurrency "mặc định một tác vụ" | **Trái yêu cầu đa truyện** | Thay bằng mục 5 |
| §4.3 Job states | Thiếu trạng thái `blocked_needs_resync` cho chương lỗi state; thiếu khái niệm hàng đợi theo truyện | Bổ sung mục 5.3 |
| §5 `synchronous=FULL` | Đúng là bền hơn, nhưng mọi commit đều fsync | Giữ FULL cho bảng chương/state; đo; có thể NORMAL nếu chấp nhận mất giao dịch cuối khi mất điện (không hỏng DB) |
| §5 Bảng dữ liệu | Thiếu bảng nối chương, plan có hash đầu vào, ledger hook có hạn trả | Bổ sung mục 4.6 |
| §6 Quy trình viết | Có Review/Settle nhưng chưa có cổng chặn, chưa có handoff, chưa có kiểm tra xác định | Thay bằng pipeline mục 4.2 |
| §6 "Độ dài tiếng Việt đo theo quy ước minh bạch" | Chưa chốt quy ước | Đếm **âm tiết** (tách theo khoảng trắng sau chuẩn hóa Unicode NFC); hiển thị cả số ký tự |
| §7 API | Thiếu API hàng đợi/đa truyện | `/v1/queues`, `/v1/works/{id}/autowrite` (mục 5.5) |
| §9 Giai đoạn 4 | "Viết nhiều chương tuần tự" nhưng chưa có tiêu chí liền mạch đo được | Thêm chỉ số mục 4.7 |
| FL04 | Bước 5 "không áp một phần state" đúng, nhưng chưa nói chặn chương sau | Bổ sung cổng chặn |
| FL05 | Không đề cập chạy nhiều truyện | Bổ sung mục 5 |
| FL24 Scheduler | Đã có quota bền/timezone — tốt; cần xoay vòng công bằng | Mục 5.2 |
| §12 Giấy phép AGPL-3.0 | Đúng và quan trọng | Giữ; không chép prompt/Skill nguyên văn nếu phân phối đóng nguồn |
| §20 Lộ trình | Quá rộng cho một người | Mục 8 |

---

## 4. Thiết kế liền mạch giữa các chương

### 4.1 Nguyên tắc

- **Tuần tự tuyệt đối trong một truyện**: chương N+1 chỉ bắt đầu khi chương N đã commit **cùng** state hợp lệ. Lý do: chương sau phụ thuộc trạng thái kết thúc của chương trước. **[Suy luận, thống nhất với các hệ Re3/AgentWrite viết tuần tự]**
- **Kế hoạch theo sự kiện, phân bổ vào chương** (StoryWriter, DOME): dàn ý tổng chia thành sự kiện; mỗi chương nhận danh sách sự kiện phải xảy ra. Dàn ý được phép điều chỉnh sau mỗi chương. **[Web-đọc: arxiv 2506.16445, 2412.13575]**
- **State có cấu trúc gồm cả "việc tương lai bắt buộc"** (NstAgent, ConWriter): không chỉ lưu những gì đã xảy ra mà cả những gì phải xảy ra, kèm hạn. **[Web-đọc: arxiv 2609.35759, 2608.05169]**
- **Lỗi hay gặp nhất là sự kiện và thời gian, tập trung ở giữa truyện** (ConStory-Bench). → Kiểm tra fact/timeline là ưu tiên số một. **[Web-snippet: arxiv 2603.05890]**

### 4.2 Pipeline một chương (đề xuất)

```text
[Cổng vào] chương N-1 committed && state_applied && không có blocked_needs_resync
   │
1. Load handoff(N-1) + state snapshot(N-1) + event plan(N) + hooks đến hạn
2. Planner  → chapter_plan(N): mục tiêu, sự kiện bắt buộc, hook phải tiến/trả,
              cảnh mở đầu phải nối từ ending_state(N-1)
              lưu kèm input_hash (state rev + handoff rev + outline rev)
3. Composer → context theo lớp (mục 6): tĩnh → truyện → động
              BẢO VỆ (không nén): plan(N), handoff(N-1), đuôi nguyên văn N-1
4. Writer   → stream bản nháp; lưu partial theo checkpoint
5. Kiểm tra xác định (không gọi LLM):
     - độ dài trong khoảng mục tiêu
     - tên riêng: chỉ dùng tên/bí danh có trong canon (hoặc khai báo nhân vật mới)
     - nhân vật đã chết/vắng mặt không xuất hiện hành động
     - danh sách cụm sáo/cấm (anti-slop) – regex
     - không lặp lại nguyên văn đoạn dài của chương trước (n-gram overlap)
6. Settle   → state delta (facts, hooks, timeline, vị trí nhân vật) + ending_state(N)
7. Validator: (a) kiểm tra schema + ràng buộc xác định trên delta
              (b) LLM so state cũ/mới + bằng chứng trích dẫn
8. Seam check (kiểm tra mối nối): đoạn mở N có khớp ending_state(N-1)?
              (địa điểm, thời điểm, ai có mặt, trạng thái cảm xúc, hành động dở dang)
9. Review   → findings có bằng chứng; phân loại blocker / major / minor
10. Nếu có blocker hoặc seam fail: revise CỤC BỘ đoạn vi phạm, quay lại 5
    tối đa K vòng (mặc định 2); hết vòng → waiting_user, KHÔNG commit
11. Commit 1 transaction: chapter_revision + state_snapshot + handoff(N)
              + summary + hooks + FTS + job result
```

Khác biệt chính so với InkOS: (1) Writer nhận handoff và đuôi chương trước; (2) có cổng chặn và vòng sửa có giới hạn; (3) kiểm tra xác định trước LLM; (4) không bao giờ commit chương mà thiếu state.

### 4.3 Vòng review → revise có giới hạn

- Sửa cục bộ đoạn vi phạm thay vì viết lại cả chương (Re3 Edit, ConWriter). **[Web-snippet/Web-đọc]**
- Giới hạn số vòng và tổng token cho mỗi chương; ghi lý do dừng.
- Findings văn chương (nhịp, giọng) là `minor` → không chặn; findings fact/timeline/seam là `blocker`.

### 4.4 Cổng chặn và trạng thái

```text
chapter.status: drafting → checking → revising → committed
                                   └→ waiting_user (hết vòng sửa / cần tác giả quyết)
work.continuity_status: ok | blocked_needs_resync | stale_from(chapter K)
```

- `blocked_needs_resync`: không enqueue chương mới cho truyện này; các truyện khác vẫn chạy.
- Sửa tay chương K < chương mới nhất → `stale_from(K)`: UI đề xuất (a) resettle K..N tuần tự từ snapshot K-1, (b) bỏ qua có xác nhận. Không tự viết lại văn bản các chương sau.

### 4.5 Duyệt tay và auto-write

| Chế độ | Hành vi |
|---|---|
| `auto` | Commit khi qua mọi cổng; dừng batch nếu rơi vào `waiting_user` |
| `review_each` | Mỗi chương dừng ở `waiting_user`; chương sau chỉ chạy sau khi tác giả accept |
| `review_every_k` | Auto, nhưng dừng chờ duyệt mỗi K chương |

Không bao giờ viết N+1 dựa trên candidate chưa commit của N.

### 4.6 Dữ liệu bổ sung

| Bảng | Nội dung |
|---|---|
| `chapter_handoffs` | `work_id, chapter_no, revision_id, ending_state JSON` (địa điểm, thời điểm truyện, nhân vật có mặt + trạng thái, hành động dở dang, cảm xúc chủ đạo), `tail_text` (đoạn cuối nguyên văn, cắt theo token, khoảng 1.000–2.000 token), `open_threads[]`, `next_opening_requirements` |
| `story_events` | Sự kiện trong dàn ý: `id, summary, planned_chapter, status (planned/done/moved/dropped), depends_on[]` |
| `hooks` (mở rộng) | Thêm `due_by_chapter`, `payoff_plan`, `priority` → planner biết hook nào sắp đến hạn |
| `chapter_plans` | Thêm `input_hash`; retry chỉ dùng lại plan nếu hash khớp |
| `findings` (đã gộp với review findings, Plan §5) | Loại (fact/timeline/name/seam/POV/slop…), mức độ, trích dẫn, trạng thái xử lý |
| `timeline` | Mốc thời gian truyện theo chương để kiểm tra xác định |

### 4.7 Chỉ số nghiệm thu liền mạch (thay cho "viết được 10–20 chương")

- 0 chương committed có `state_applied=false`.
- Seam check pass ≥ 95% ở lần đầu hoặc sau ≤ 2 vòng sửa trên bộ truyện mẫu.
- 0 tên nhân vật ngoài canon chưa khai báo.
- Hook quá hạn `due_by_chapter` được báo cáo 100%.
- Tỷ lệ n-gram trùng giữa chương liền kề dưới ngưỡng cấu hình.
- Đánh giá người đọc trên truyện mẫu tiếng Việt 20 chương: chấm từng chương + cả truyện (theo kiểu EQ-Bench Longform). **[Web-đọc: github.com/EQ-bench/longform-writing-bench]**

---

## 5. Thiết kế chạy đồng thời nhiều truyện

### 5.1 Mô hình

```text
                ┌──────────── Global Scheduler (asyncio, 1 process) ────────────┐
Work A queue →  │  ready set: các truyện có job kế tiếp và không bị chặn       │
Work B queue →  │  chọn xoay vòng có trọng số (fair round-robin)               │→ Worker pool (N)
Work C queue →  │  mỗi truyện tối đa 1 job sinh văn bản đang chạy               │
                └───────────────────────────────────────────────────────────────┘
                                    │
               Provider limiter: concurrency + token bucket (RPM/TPM) + Retry-After
                                    │
                         Cloud API / Ollama / LM Studio
```

- **Trong một truyện**: hàng đợi FIFO, tối đa 1 job ghi (write/revise/resync/import) tại một thời điểm. Lock lưu trong SQLite (bảng `work_locks` có lease + heartbeat), **xếp hàng thay vì fail-fast** như InkOS.
- **Giữa các truyện**: chạy song song, số lượng = `min(N worker, giới hạn provider)`.
- **Công bằng**: xoay vòng theo truyện, không `slice(0, N)`. Có ưu tiên (truyện người dùng đang mở được ưu tiên).
- **Tác vụ phụ không phụ thuộc** (review chương đã commit, chấm điểm, research, dịch) chạy song song trong ngân sách riêng.

### 5.2 Giới hạn theo provider

| Tham số | Mặc định đề xuất | Ghi chú |
|---|---|---|
| `max_concurrent_requests` | Cloud: 3–4; local (Ollama/LM Studio): 1 | Người dùng chỉnh, app đề xuất theo phản hồi 429 |
| `rpm`, `tpm` | Theo tier tài khoản | Token bucket |
| Retry | 3 lần, exponential backoff + jitter, ưu tiên header `Retry-After` | Không retry 401/403/model-not-found |
| Ngân sách | Token/ngày và chi phí ước tính/ngày, theo truyện và toàn app | Lưu bền trong SQLite theo timezone cấu hình |

### 5.3 Trạng thái job bổ sung

```text
queued → waiting_slot (chờ provider/worker) → running → succeeded
                                                   ├→ waiting_user
                                                   ├→ blocked (needs_resync)
                                                   ├→ failed / cancelled
                                                   └→ interrupted (crash)
```

### 5.4 SQLite với nhiều truyện

- SQLite chỉ có **một writer tại một thời điểm**. **[Web-đọc: sqlite.org/wal.html]** Với nhiều truyện, giữ transaction ghi thật ngắn (chỉ lúc commit chương); không mở transaction trong lúc chờ AI.
- Có thể dùng một "writer queue" nội bộ (một task asyncio nhận lệnh commit) để tránh `database is locked`, kèm `busy_timeout`.
- Một chương commit gồm vài bảng → vài ms đến vài chục ms; với vài truyện song song, đây không phải nút cổ chai (nút cổ chai là API AI). **[Suy luận, cần đo ở R0]**

### 5.5 API và UI

```text
POST /v1/works/{id}/autowrite     {target_chapter | count, mode: auto|review_each|review_every_k, priority}
POST /v1/works/{id}/autowrite/pause | resume | cancel
GET  /v1/queues                   trạng thái mọi truyện: đang chạy, chờ slot, bị chặn, ETA
GET  /v1/providers/{id}/usage     RPM/TPM/chi phí hôm nay
```

UI: bảng "Phòng viết" liệt kê các truyện đang chạy, chương hiện tại, bước pipeline, trạng thái liền mạch, chi phí; mở một truyện bất kỳ để đọc/sửa trong khi các truyện khác vẫn chạy.

---

## 6. Tối ưu chi phí và tốc độ: prompt theo lớp và cache

Xếp prompt từ tĩnh nhất đến động nhất để provider cache được phần đầu:

```text
[Lớp 1 – toàn app, cache lâu]  system, phương pháp viết, quy tắc tiếng Việt, danh sách cụm cấm
[Lớp 2 – theo truyện]         story bible, dàn ý tổng, nhân vật chính, book rules
[Lớp 3 – theo chương]         state snapshot, summaries chọn lọc, hooks đến hạn, handoff, đuôi chương trước, plan
[Lớp 4]                       chỉ dẫn của lượt hiện tại
```

- **Anthropic**: cache theo prefix; tối đa 4 breakpoint; ghi cache 5 phút = 1,25× giá input, 1 giờ = 2×, đọc = 0,1×; cache chỉ dùng được sau khi response đầu tiên bắt đầu → với nhiều chương liên tiếp của cùng truyện, lớp 1–2 được tái sử dụng tự nhiên. **[Web-đọc: platform.claude.com/docs/en/build-with-claude/prompt-caching]**
- **Anthropic Batch API**: giảm 50%, cộng dồn với cache, đa số xong < 1 giờ, tối đa 24 giờ → phù hợp tác vụ không gấp (review lại hàng loạt, chấm điểm, dịch), **không** phù hợp chuỗi chương tuần tự. **[Web-đọc: …/batch-processing]**
- **OpenAI**: cache tự động theo prefix từ 1.024 token; có `prompt_cache_key` để định tuyến; tóm tắt lại lịch sử sẽ làm mất prefix. **[Web-đọc: developers.openai.com/api/docs/guides/prompt-caching]**
- **Gemini**: implicit caching bật mặc định từ 2.5; đặt nội dung chung lên đầu. **[Web-đọc: ai.google.dev/gemini-api/docs/caching]**; mức giảm giá explicit cache chưa xác minh.
- Hệ quả thiết kế: **không chỉnh sửa lớp 1–2 trong lúc chạy batch**; thay đổi story bible tạo revision mới và áp từ chương kế tiếp. Ghi `cache_read_tokens` vào usage để đo hiệu quả.

---

## 7. Kiểm chứng các giả định kỹ thuật

| Giả định trong thiết kế | Kết quả | Nguồn |
|---|---|---|
| SQLite WAL: một writer, reader không chặn writer | **Đúng** | [sqlite.org/wal.html](https://sqlite.org/wal.html) [Web-đọc] |
| WAL không chạy trên ổ mạng | **Đúng** – thiết kế cấm data trên network share là đúng | như trên |
| `synchronous=NORMAL` trong WAL | Có thể mất giao dịch gần nhất khi mất điện, **không hỏng DB**; FULL fsync mỗi commit | như trên |
| Data cạnh `.app` trên macOS | **Sai trong trường hợp app bị translocate** (mở từ Downloads/zip/DMG chưa kéo bằng Finder): app chạy từ đường dẫn ngẫu nhiên chỉ đọc. Apple khuyên app phải chạy đúng khi bị translocate | [Apple DTS – App Translocation Notes](https://developer.apple.com/forums/thread/724969), [Eclectic Light](https://eclecticlight.co/2021/04/19/ios-apps-are-translocated-when-run-in-macos/), [Synack](https://www.synack.com/blog/untranslocating-apps/) [Web-đọc/snippet] |

**Sửa thiết kế macOS:** lần chạy đầu hiển thị chọn data-root (mặc định gợi ý thư mục cạnh `.app` nếu ghi được, nếu không `~/Library/Application Support/WriteStoryApp`), lưu con trỏ data-root vào một file cấu hình nhỏ ở vị trí chuẩn; phát hành DMG có symlink `/Applications`; phát hiện đường dẫn translocate (`/AppTranslocation/`) và hướng dẫn người dùng.

### 7.1 Đóng gói, desktop và runtime

| Giả định | Kết quả | Hệ quả cho thiết kế | Nguồn |
|---|---|---|---|
| Tauri `externalBin` cần hậu tố target-triple | **Đúng** | Đặt tên launcher theo `-x86_64-pc-windows-msvc`, `-aarch64-apple-darwin` | [Tauri sidecar](https://v2.tauri.app/develop/sidecar/) |
| Đóng gói PyInstaller onedir bằng `bundle.resources` | **Đúng**, dùng `"dir/"` (đệ quy, giữ cấu trúc); `"dir/**"` lỗi; glob trong dạng map bị làm phẳng | Ghi rõ cú pháp trong `tools/packaging` | [Tauri resources](https://v2.tauri.app/develop/resources/) |
| PyInstaller onefile khởi động chậm | **Đúng**: giải nén vào `_MEIxxxx` mỗi lần chạy; còn sót thư mục tạm khi bị kill | Dùng **onedir** như thiết kế đã chọn | [PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html) |
| Tauri tự ký mọi binary lồng nhau trên macOS | **Sai một phần**: `.dylib/.so` trong `_internal/` của onedir đặt ở resources **không được ký tự động** → notarize lỗi | Thêm bước CI `codesign --options runtime --timestamp` từng file trước khi bundle | [tauri#8075](https://github.com/tauri-apps/tauri/issues/8075), [tauri#11992](https://github.com/tauri-apps/tauri/issues/11992) |
| WebView2 có chế độ cài offline | **Đúng**: `downloadBootstrapper` (mặc định, cần mạng), `embedBootstrapper` (~1,8 MB), `offlineInstaller` (~127 MB), `fixedRuntime` (~180 MB), `skip` | Portable offline → `offlineInstaller` hoặc `fixedRuntime` (tên `fixedRuntime` chưa xác nhận trong schema) | [Tauri Windows installer](https://v2.tauri.app/distribute/windows-installer/) |
| Tauri tự dừng backend khi thoát | **Một phần**: plugin-shell chỉ kill tiến trình con trực tiếp khi `RunEvent::Exit`; macOS có thể không phát `ExitRequested` | Giữ thiết kế: endpoint shutdown + xử lý cả `ExitRequested` và `Exit` + onedir (không có tiến trình bootloader trung gian) + Windows Job Object | [tauri#14360](https://github.com/tauri-apps/tauri/issues/14360) |
| WebView khác nhau giữa OS | **Đúng**: Windows WebView2 (Chromium tự cập nhật); macOS WKWebView **gắn phiên bản macOS** | Đặt phiên bản macOS tối thiểu; test editor trên macOS cũ nhất hỗ trợ | [Tauri webview versions](https://v2.tauri.app/reference/webview-versions/) |
| Python 3.13 làm baseline | **Nên đổi**: bản ổn định mới nhất là 3.14.8 (30/09/2026); PyInstaller 6.22.3 hỗ trợ 3.14 từ 6.15.0; free-threaded ở 3.14 vẫn tùy chọn (PEP 779); 3.15.0 chưa xác nhận phát hành | **Baseline CPython 3.14 bản GIL tiêu chuẩn**; chưa dùng 3.15 tới khi có vài bản vá | [python.org](https://www.python.org/downloads/), [PyInstaller changes](https://pyinstaller.org/en/stable/CHANGES.html), [PEP 779](https://peps.python.org/pep-0779/) |

### 7.2 Backend và dữ liệu

| Giả định | Kết quả | Hệ quả | Nguồn |
|---|---|---|---|
| FastAPI BackgroundTasks không phù hợp làm job bền | **Đúng**: chạy sau khi trả response, cùng process; docs không có persistence | Giữ job lưu SQLite + supervisor | [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) |
| Uvicorn nhận socket đã bind | **Đúng**: `Server.serve(sockets=[...])` | Giữ thiết kế cổng động | [uvicorn server.py](https://github.com/encode/uvicorn/blob/master/uvicorn/server.py) |
| SSE cần thư viện ngoài | **Đã thay đổi**: FastAPI ≥ 0.135.0 có `fastapi.sse.EventSourceResponse`, ping 15 s, hỗ trợ `Last-Event-ID` | Dùng SSE native; event cursor = `Last-Event-ID` | [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/) |
| EventSource không gửi được `Authorization` | **Đúng** | Giữ fetch streaming (hoặc `@microsoft/fetch-event-source`) | [whatwg/html#2177](https://github.com/whatwg/html/issues/2177) |
| AsyncSession không chia sẻ giữa task | **Đúng** | Mỗi job một session qua `async_sessionmaker` | [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) |
| aiosqlite là async thật | **Không**: chạy mỗi connection trên một thread nền; transaction cần cấu hình | Thêm writer queue (mục 5.4); kiểm tra cấu hình transaction (`autocommit=False` hoặc tự phát `BEGIN`) trong R1 | [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) |
| Backup DB đang chạy | **Đúng**: Backup API cho snapshot nhất quán nhưng **khởi động lại nếu có ghi xen giữa** (có thể không bao giờ xong khi ghi liên tục); `VACUUM INTO` cũng cho snapshot nhất quán | Ưu tiên `VACUUM INTO` ra file tạm rồi rename; hoặc Backup API với `step(-1)` | [SQLite backup](https://www.sqlite.org/backup.html), [VACUUM](https://www.sqlite.org/lang_vacuum.html) |
| uv workspace một lockfile | **Đúng**; `requires-python` là giao của các member | Giữ | [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) |

### 7.3 Tìm kiếm tiếng Việt (FTS5) – đã chạy thử

Chạy thử trên SQLite 3.51.3 (Node `node:sqlite`) với câu "Đường đi Nguyễn Văn Ộc người ơi":

| Truy vấn | `remove_diacritics 1` | `remove_diacritics 2` |
|---|---|---|
| `nguyen`, `oc`, `nguoi` | **0** (không tìm thấy) | 1 |
| `oi` | 1 | 1 |
| `Đường` (có dấu) | 1 | 1 |
| `duong`, `di` | **0** | **0** |

Kết luận **[đã chạy thử + [FTS5 docs](https://www.sqlite.org/fts5.html)]**:
- Bắt buộc `remove_diacritics 2`; giá trị mặc định 1 bỏ sót chữ mang hai dấu (ộ, ễ, ờ…), rất phổ biến trong tiếng Việt.
- **`đ/Đ` không được gập thành `d`** (U+0111 không có phân rã Unicode). Ứng dụng phải chuẩn hóa trước khi index và trước khi query: NFC → thay `đ→d`, `Đ→D` cho cột tìm kiếm không dấu. Giữ cột gốc có dấu để hiển thị.
- `bm25()` có sẵn, giá trị nhỏ hơn là khớp hơn, hỗ trợ trọng số cột.
- Trigram tokenizer hữu ích cho tìm chuỗi con/tên riêng; chuỗi < 3 ký tự không khớp.

### 7.4 Bảo mật vault

| Giả định | Kết quả | Hệ quả | Nguồn |
|---|---|---|---|
| `cryptography` có AES-GCM và Scrypt | **Đúng**; nonce 12 byte, không bao giờ dùng lại | Giữ | [cryptography AEAD](https://cryptography.io/en/latest/hazmat/primitives/aead/) |
| KDF nên dùng | `Argon2id` có từ cryptography 44.0.0 | **Đổi sang Argon2id** (OWASP: m=19 MiB, t=2, p=1 tối thiểu); Scrypt (N=2^17, r=8, p=1) làm phương án dự phòng | [cryptography KDF](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/), [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) |

### 7.5 Editor và bộ gõ tiếng Việt

- **Chưa tìm thấy** issue Tiptap/ProseMirror riêng về Telex/VNI/Unikey. Có nhiều lỗi composition tương tự với IME Nhật/Hàn trên Safari/WKWebView ([prosemirror#1190](https://github.com/ProseMirror/prosemirror/issues/1190)) và nhân đôi ký tự ([tiptap#2780](https://github.com/ueberdosis/tiptap/issues/2780)). prosemirror-view 1.41.9 (06/2026) sửa xử lý backspace trong composition trên Chrome — liên quan vì Unikey/EVKey hoạt động bằng cách gửi backspace rồi gõ lại ([changelog](https://prosemirror.net/docs/changelog/)).
- **Rủi ro cao, giữ trong R0**: test bằng Unikey, EVKey (Windows, cả chế độ "sửa lỗi gợi ý" bật/tắt) và Telex/VNI có sẵn của macOS; gõ trong đoạn có bold/italic, đầu/cuối mark, undo/redo; pin phiên bản `prosemirror-view` ≥ 1.41.9.
- Nếu WKWebView lỗi không khắc phục được trong ngân sách spike: đây là lý do cụ thể để chuyển sang Electron như kế hoạch §2 đã dự phòng.

---

## 8. Đề xuất phạm vi MVP

Giữ nguyên backlog 146 hạng mục, nhưng MVP chỉ gồm:

1. R0 spike (giữ nguyên, thêm kiểm tra translocation macOS và IME tiếng Việt).
2. R1 dữ liệu + editor.
3. R2 rút gọn: truyện dài với pipeline mục 4.2, handoff, cổng chặn, review/revise có giới hạn, **scheduler đa truyện mục 5**, export TXT/Markdown.
4. Bỏ khỏi MVP: chat/action engine đầy đủ (CHT06–CHT11), Skill import, forecast, analytics nâng cao.

Mục tiêu MVP đo được: chạy đồng thời 3 truyện, mỗi truyện 20 chương, không chương nào `state_applied=false`, đạt chỉ số mục 4.7.

---

## 9. Danh sách sửa vào implementation-plan.vi.md

**Trạng thái: đã áp toàn bộ vào [implementation-plan.vi.md](./implementation-plan.vi.md) và [folder-architecture.vi.md](./folder-architecture.vi.md) ngày 02/10/2026.**

1. §3.1: thêm xử lý macOS App Translocation và chọn data-root lần đầu.
2. §4.2: thay "mặc định một tác vụ" bằng mô hình mục 5.
3. §4.3: thêm `waiting_slot`, `blocked`, lock xếp hàng có lease.
4. §5: thêm bảng mục 4.6; quy ước đếm độ dài tiếng Việt theo âm tiết.
5. §6: thay bằng pipeline mục 4.2 (handoff, kiểm tra xác định, seam check, vòng sửa có giới hạn, cổng chặn).
6. §7: thêm API mục 5.5.
7. FL04/FL05/FL24: bổ sung cổng chặn, chế độ duyệt, xoay vòng công bằng.
8. §9 Giai đoạn 4 và §21: dùng chỉ số mục 4.7.
9. §14 và folder-architecture §2: cập nhật trạng thái kiểm chứng web theo mục 7.
10. §2 Stack: CPython **3.14** thay 3.13; SSE native của FastAPI ≥ 0.135; KDF **Argon2id** thay Scrypt; WebView2 `offlineInstaller`/`fixedRuntime` cho bản portable.
11. §5 Search: `unicode61 remove_diacritics 2` + chuẩn hóa `đ→d` ở tầng ứng dụng; backup bằng `VACUUM INTO` ra file tạm rồi rename.
12. §10 Đóng gói macOS: bước ký từng `.dylib/.so` của PyInstaller onedir trước khi Tauri bundle và notarize.
13. §9 Giai đoạn 0: test IME bằng Unikey/EVKey/Telex macOS, pin `prosemirror-view` ≥ 1.41.9.

---

## 10. Nguồn nghiên cứu viết truyện dài

| Nguồn | Ý dùng cho thiết kế | Bằng chứng |
|---|---|---|
| Re3 – [arxiv 2210.06774](https://arxiv.org/abs/2210.06774) | Plan/Draft/Rewrite/Edit; sửa cục bộ | Web-snippet |
| DOC – [arxiv 2212.10077](https://arxiv.org/abs/2212.10077) | Dàn ý chi tiết + controller bám dàn ý | Web-snippet |
| LongWriter/AgentWrite – [arxiv 2408.07055](https://arxiv.org/abs/2408.07055) | Lập kế hoạch đoạn + số từ, viết tuần tự | Web-snippet |
| StoryWriter – [arxiv 2506.16445](https://arxiv.org/abs/2506.16445) | Outline theo sự kiện, phân bổ vào chương, nén lịch sử theo sự kiện | Web-đọc |
| DOME – [arxiv 2412.13575](https://arxiv.org/abs/2412.13575) | Dàn ý động, temporal KG, phát hiện xung đột thời gian | Web-đọc |
| WriteHERE – [arxiv 2503.08275](https://arxiv.org/abs/2503.08275) | Lập kế hoạch và viết đan xen | Web-snippet |
| NstAgent – [arxiv 2609.35759](https://arxiv.org/abs/2609.35759) | State có cấu trúc + việc tương lai bắt buộc; ổn định 10k–100k từ | Web-đọc |
| ConWriter – [arxiv 2608.05169](https://arxiv.org/abs/2608.05169) | Ràng buộc + bộ nhớ động, kiểm tra transition, sửa cục bộ | Web-đọc |
| ConStory-Bench – [arxiv 2603.05890](https://arxiv.org/html/2603.05890v1) | Lỗi fact/timeline phổ biến nhất, dồn ở giữa truyện | Web-snippet |
| So sánh 7 framework – [arxiv 2608.26177](https://arxiv.org/abs/2608.26177) | Chấm dàn ý riêng; length collapse ~16k token; trôi thuộc tính | Web-đọc |
| Antislop – [arxiv 2510.15061](https://arxiv.org/abs/2510.15061) | Danh sách cụm cấm + sửa sau sinh | Web-đọc |
| EQ-Bench Longform – [GitHub](https://github.com/EQ-bench/longform-writing-bench) | Khung đánh giá theo chương + cả truyện | Web-đọc |

**Chưa có nguồn sơ cấp**: hiệu quả so sánh của "đuôi chương nguyên văn" và "hợp đồng mở chương"; so sánh retrieval với full-context cho truyện dài; chạy song song nhiều truyện. Các đề xuất tương ứng là **[Suy luận]** và cần đo trên bộ truyện mẫu ở R2.
