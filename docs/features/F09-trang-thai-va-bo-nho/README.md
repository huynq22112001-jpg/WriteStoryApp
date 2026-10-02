# F09 — Trạng thái truyện và bộ nhớ

Giai đoạn: R2 (schema `StoryState`/`StateDelta` là hợp đồng **Chặn MVP**, Plan §23.5 #1 – phải chốt trước khi code R2). Trạng thái: planned.

## Mục tiêu

Truyện có một "bộ nhớ" có cấu trúc, kiểm chứng được và ổn định theo độ dài: sau mỗi chương có snapshot `StoryState` đầy đủ, mọi thay đổi đi qua `StateDelta` có bằng chứng `paragraph_id`, tóm tắt phân tầng giữ context không phình khi truyện 200+ chương, tìm kiếm FTS tiếng Việt có nguồn, và Composer dựng context theo lớp trong ngân sách của model thực dùng, lưu trace để tác giả xem "AI đã dùng ngữ cảnh nào".

## Phạm vi

- Trong phạm vi:
  - Contract `StoryState`, `StateDelta` (15 op của Plan §23.1.A + 2 op bổ sung đề xuất), `Evidence`, `EndingState` (dùng chung với F10 handoff).
  - Reducer thuần `apply_delta(state, delta) -> state` và validator xác định (luật V01–V15).
  - Bảng `story_states` (snapshot mỗi chương), sổ cái `facts`, `hooks`, `timeline`, `story_events` (cập nhật trạng thái), `summaries` (chương / arc / synopsis), `context_traces`.
  - Tóm tắt phân tầng và nhịp cập nhật (Plan §23.3 #1).
  - Projection FTS5 cho chương/fact/hook/summary/nhân vật, API tìm kiếm có provenance (MEM04, MEM05, MEM09).
  - Composer (`ai/context/`): lớp prompt Plan §6.4, phần bảo vệ/nén được, ngân sách từ `max_input_tokens`, chiến lược đếm token (Plan §23.3 #4), cắt `tail_text` 1.000–2.000 token theo ranh giới đoạn.
  - API đọc state theo chương, áp delta thủ công (cho Story Bible F06), trace, search, bộ nhớ của chương.
  - FE: hook dữ liệu cho thanh trượt state ở Story Bible, tab "Nhớ", UI tìm kiếm, trình xem trace "Đã dùng ngữ cảnh".
- Ngoài phạm vi:
  - Gọi settle/validate LLM và thứ tự bước pipeline (F10); F09 cung cấp contract, reducer, validator xác định, composer.
  - Màn hình Story Bible đầy đủ (F06); resync `stale_from` (F11).
  - Embeddings/vector search (NEW09, sau đánh giá lexical); tài liệu tham khảo (MEM06–07, R3).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F02 | SQLite WAL, writer queue, FTS5 `remove_diacritics 2`, unit of work |
| F08 | `search_normalizer`, `length_counter`, `normalizer.for_compare` cho kiểm bằng chứng, token ước lượng theo âm tiết |
| F07 | `paragraph_id` ổn định trong revision; plain-text projection theo đoạn |
| F04 | `max_input_tokens`, `max_tokens`, `tokens_per_syllable`, capability count tokens của model |
| F06 (song song) | Nhân vật, địa điểm, dàn ý sự kiện, state seed chương 0 |

Dùng F09: F10 (load/compose/settle/validate/commit), F06 (Story Bible), F11 (resync), F12 (ước tính token).

## Nguồn thiết kế

- Plan §23.1.A (schema v1), §23.1.B (`paragraph_id`), §23.3 #1 (tóm tắt phân tầng), #4 (đếm token), §6.2 (bước 1, 3, 6, 7, 11 và quy tắc `tail_text`), §6.4 (lớp prompt), §5 (bảng, ghi chú FTS), §7 API `/state`, `/trace`, `/search`, CRUD facts/hooks/timeline, §7.1 "Composer luôn lấy ngân sách từ `max_input_tokens`", §18 (`context_traces`, `summaries`).
- Arch §6 (`contracts/state.py`, `context/builder.py`, `budget.py`, `retrieval.py`, `evidence.py`, `workflows/longform/summaries.py`), §5 (`infrastructure/ai/context_adapter.py`, `db/fts.py`).
- UI §5.2 tab Nhớ + card "Đã dùng ngữ cảnh", §5.4 Story Bible, §5.8 thanh trượt state.
- Review §2.1 (cách InkOS mang nội dung, ngân sách `(contextWindow − maxTokens)/2`), §2.3 #3 (Planner nhận toàn văn → vượt ngân sách), #9 (state lặp 3 nơi, index dựng lại mỗi chương), §6 (cache theo lớp), §7.3 (FTS).
- Nghiên cứu: NstAgent ([arxiv 2609.35759](https://arxiv.org/abs/2609.35759)) – state có việc tương lai bắt buộc; StoryWriter ([arxiv 2506.16445](https://arxiv.org/abs/2506.16445)) – nén lịch sử theo sự kiện; DOME ([arxiv 2412.13575](https://arxiv.org/abs/2412.13575)) – xung đột thời gian; ConStory-Bench ([arxiv 2603.05890](https://arxiv.org/html/2603.05890v1)) – lỗi fact/timeline phổ biến nhất.
- Mã Plan §15: LNG06, LNG12, LNG13, LNG14, MEM01–MEM05, MEM08, MEM09.

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Bảng và migration, repository, áp delta trong transaction, projection FTS, API state/delta/summary/search/trace/memory, ContextPort adapter |
| FE | [fe.md](./fe.md) | `useStoryState` + thanh trượt chương, tab Nhớ, tìm kiếm có nguồn, `ContextTraceViewer` |
| AI | [ai.md](./ai.md) | Contract Pydantic đầy đủ, ngữ nghĩa op, reducer, validator V01–V15, tóm tắt phân tầng, Composer theo lớp, ngân sách và đếm token, `tail_text`, retrieval |

## Tiêu chí hoàn thành

- [ ] JSON Schema của `StoryState`/`StateDelta` xuất từ Pydantic, có version, snapshot trong `contracts/examples/`; FE sinh type từ OpenAPI.
- [ ] Reducer thuần: `apply_delta` deterministic (cùng input → cùng output, cùng `state_hash`).
- [ ] Validator bắt đủ các lỗi cài sẵn trong `tests/fixtures/state/` (ID không tồn tại, nhân vật chết hành động, thời gian lùi không đánh dấu hồi tưởng, hook đóng bị advance, dùng bí mật chưa `learn`, bằng chứng không khớp đoạn).
- [ ] Bất biến: chiếu sổ cái `facts`/`hooks` tại chương N bằng đúng `facts`/`hooks` trong snapshot N (test property trên truyện mẫu 20 chương).
- [ ] Composer: phần bảo vệ (plan, handoff, `tail_text`) không bao giờ bị nén; tổng token ước lượng ≤ ngân sách; kích thước context ổn định khi truyện tăng từ 20 lên 200 chương (T14).
- [ ] Tìm kiếm có/không dấu, `đ`/`d` đều ra kết quả kèm `chapter_no` + `paragraph_id` + snippet có dấu.
- [ ] `GET /v1/chapters/{id}/trace` hiển thị đủ nguồn, lớp, token, mục bị loại và lý do.
- [ ] Test luồng pass: [T14](../../tests/flows/T14-truyen-dai-va-ngu-canh.md); phần state/handoff của [T05](../../tests/flows/T05-viet-mot-chuong.md), [T06](../../tests/flows/T06-chuong-loi-va-bi-chan.md); phần tìm kiếm của [T13](../../tests/flows/T13-kiem-tra-tieng-viet.md).

## Rủi ro và câu hỏi mở

- Snapshot đầy đủ mỗi chương: Plan chọn vì đơn giản; với 200+ chương và nhiều fact có thể lớn – đo ở T14, chỉ chuyển sang delta + snapshot định kỳ khi số đo cần (Plan §23.1.A).
- Hai nơi lưu cùng thông tin (snapshot JSON và sổ cái `facts`/`hooks`): chính là điểm yếu InkOS #9 (Review §2.3). Thiết kế ở đây chốt snapshot là chuẩn, sổ cái là projection được cập nhật trong **cùng transaction** và có test bất biến; vẫn cần quyết định cuối cùng.
- `StateDelta` của Plan không có op thêm nhân vật/địa điểm, trong khi §6.2 cho phép "khai báo nhân vật mới" → đề xuất `character.add`, `location.add` (cần đồng bộ Plan).
- Plan yêu cầu mọi op có `evidence`, nhưng `event.move`/`event.drop`/`hook.defer` thường không có đoạn văn làm bằng chứng → đề xuất dùng `reason` thay `evidence` cho ba op này.
- Tỷ lệ token/âm tiết chưa đo cho từng model; trước khi đo dùng giá trị mặc định bảo thủ (giả định), biên 15% theo Plan.
- Chọn K tóm tắt chương gần nhất và số kết quả tìm kiếm mặc định là giả định cấu hình, tinh chỉnh bằng T14.
