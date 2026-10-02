# Prompt triển khai – mỗi file một prompt

Có 136 prompt, mỗi prompt nằm trong **một file riêng** `Pxxx-<tên>.md`, là một task nhỏ (khoảng nửa ngày đến một ngày). Cách dùng: mở một cửa sổ Claude Code mới tại `E:\pm\WriteStoryApp`, mở file prompt, dán nguyên khối `text` trong file đó.

Đánh số: `P0xx` R0, `P1xx` R1, `P2xx` R2, `P9xx` dữ liệu test và nghiệm thu.

## Quy tắc chung

Mọi prompt yêu cầu agent làm theo mục này.

1. **Đọc trước khi code:** [docs/README.md](../README.md), [docs/steps/TRANG-THAI.md](../steps/TRANG-THAI.md), bảng quyết định Plan §24 trong [implementation-plan.vi.md](../implementation-plan.vi.md), và các file mà prompt liệt kê. Spec tính năng là nguồn chuẩn; §24 thắng khi có mâu thuẫn.
2. **Phụ thuộc:** chỉ bắt đầu khi các prompt phụ thuộc đã `done` trong bảng Tiến độ; nếu chưa, dừng và báo người dùng.
3. **Phạm vi file:** chỉ sửa/tạo file trong "Phạm vi file". Cần sửa file ngoài phạm vi (ví dụ thêm mã lỗi vào `be/src/writestory_be/core/errors.py`, đăng ký router trong `main.py`) thì sửa tối thiểu và ghi rõ trong báo cáo – cửa sổ khác có thể đang làm song song.
4. **Tên:** bảng, cột, endpoint, mã lỗi, event, file dùng đúng tên trong Plan §5/§7/§23/§24 và spec. Tên mới phải ghi vào mục "Tên mới đề xuất" của file spec tương ứng.
5. **Lệnh:** Python luôn qua `uv run …` (không dùng alias `python` của Windows Store); JS qua `pnpm --filter fe …`; Rust qua `cargo` trong `desktop/src-tauri`. Không cài công cụ hệ thống khi chưa hỏi người dùng.
6. **Ranh giới:** package AI không import BE/FastAPI/SQLAlchemy; FE không chứa prompt hay API key; transaction DB không bao quanh lời gọi AI (Arch §6, Plan §4.2).
7. **Test:** viết test theo bảng "Test" của spec và kịch bản trong `docs/tests/flows/Txx`. Không gọi AI thật trong test mặc định (dùng mock provider). Task chỉ xong khi test liên quan pass – báo đúng kết quả, kể cả khi fail.
8. **Kết thúc task:** tick `- [x]` mục đã làm trong checklist `be.md`/`fe.md`/`ai.md` của tính năng; đổi trạng thái prompt trong bảng Tiến độ dưới đây (đọc lại file ngay trước khi sửa, chỉ sửa dòng của mình); cập nhật `docs/steps/TRANG-THAI.md`; trả lời bằng tiếng Việt: file đã đổi, lệnh test + kết quả, tên mới phát sinh, việc còn dở.
9. **Migration DB:** làn BE chạy tuần tự để chuỗi Alembic không xung đột. Tên file `NNNN_fxx_<mô_tả>.py`, `down_revision` trỏ migration mới nhất đang có.
10. **Không tự commit/push** trừ khi người dùng yêu cầu trong cửa sổ đó.

## Làn chạy song song

| Làn | Thư mục chính | Cách chạy |
|---|---|---|
| **BE** | `be/` | Tuần tự (dùng chung chuỗi migration) |
| **AI** | `ai/` | Song song với BE; chỉ dựa vào contracts |
| **FE** | `fe/` | Song song; API chưa có thì dùng types OpenAPI + dữ liệu giả trong `fe/tests/mocks/` |
| **DESKTOP** | `desktop/`, `tools/packaging/` | Song song |
| **TEST** | `tests/`, fixtures | Song song |

## Gợi ý mở cửa sổ

1. Chạy **P001** một mình (cài uv + Python, cần bạn đồng ý).
2. Mở song song **P002** (AI), **P003** (BE), **P004** (FE).
3. Sau đó mỗi làn một cửa sổ, đi theo cột Phụ thuộc:
   - BE: P005 → P006 → P101 → P102 → … → P129 → P230 → …
   - AI: P118 → P119 → P120 → P121 → P201 → … → P222
   - FE: P007 → P014 → P015 → P150 → … → P167 → P270 → …
   - DESKTOP: P009 → P010 → P011 → P012 → P017 → P018 → P290
   - TEST: P901 → P902 → P904 → P905 → P906 → P907
4. Kết thúc bằng **P020** (nghiệm thu R0) và **P908** (nghiệm thu MVP).

## Tiến độ

Trạng thái: `todo` · `doing` · `done` · `blocked (lý do)`.

### R0 – kiểm chứng base, hợp đồng, desktop, editor, đóng gói

| Prompt | Làn | Tính năng | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| [P001](./P001-cai-moi-truong-uv-python.md) Cài uv + Python 3.14 và uv sync | Tất cả | S00 | — | todo |
| [P002](./P002-kiem-chung-ai-base.md) Kiểm chứng code base AI | AI | S02 | P001 | todo |
| [P003](./P003-kiem-chung-be-base.md) Kiểm chứng code base BE | BE | S03 | P001 | todo |
| [P004](./P004-kiem-chung-fe-base.md) Kiểm chứng code base FE | FE | S04 | — | todo |
| [P005](./P005-chay-thu-dev-health.md) Chạy thử backend dev + health | BE | S06 | P003 | todo |
| [P006](./P006-xuat-openapi.md) Xuất OpenAPI có ErrorResponse + EventEnvelope | BE | F01 / S05 | P003 | todo |
| [P007](./P007-sinh-types-ts.md) Sinh types TS từ OpenAPI + check_contracts | FE | F01 / S05 | P006, P004 | todo |
| [P008](./P008-script-dev-va-readme.md) Script chạy dev BE+FE và README gốc | Tất cả | S06 | P005, P004 | todo |
| [P009](./P009-tauri-scaffold.md) Scaffold desktop Tauri 2 | DESKTOP | F00 / S07 | P004 | todo |
| [P010](./P010-rust-data-root-lock.md) Rust: data-root + khóa instance | DESKTOP | F00 | P009 | todo |
| [P011](./P011-rust-spawn-backend.md) Rust: spawn backend + readiness | DESKTOP | F00 | P010, P003 | todo |
| [P012](./P012-rust-shutdown-commands.md) Rust: tắt sạch + commands cho FE | DESKTOP | F00 | P011 | todo |
| [P013](./P013-fe-boot-gate.md) FE: BootGate và màn khởi động | FE | F00 | P012, P004 | todo |
| [P014](./P014-spike-tiptap.md) Spike editor Tiptap + paragraph_id | FE | F07 / S08 | P004 | todo |
| [P015](./P015-paste-nfc-dem-am-tiet-ts.md) Paste NFC + đếm âm tiết TS | FE | F07 / F08 | P014 | todo |
| [P016](./P016-checklist-ime.md) Chuẩn bị kiểm tra bộ gõ tiếng Việt | FE | F07 / S08 | P015, P013 | todo |
| [P017](./P017-pyinstaller-onedir.md) PyInstaller onedir cho backend | DESKTOP | F00 / S09 | P003 | todo |
| [P018](./P018-gan-backend-vao-tauri.md) Gắn backend vào bundle Tauri + installer Windows | DESKTOP | F00 / S09 | P017, P012 | todo |
| [P019](./P019-script-ky-macos.md) Script ký backend cho macOS | DESKTOP | F00 / S09 | P017 | todo |
| [P020](./P020-nghiem-thu-r0.md) Nghiệm thu R0 + ADR | Tất cả | S10 | P008, P013, P016, P018 | todo |

### R1 – nền dữ liệu, vault, thư viện, cấu hình AI, editor

| Prompt | Làn | Tính năng | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| [P101](./P101-alembic-setup.md) Cài đặt Alembic async | BE | F02 | P003 | todo |
| [P102](./P102-migration-baseline.md) Migration baseline: settings, jobs, events | BE | F02 / F01 | P101 | todo |
| [P103](./P103-prepare-database.md) Hook prepare_database khi khởi động | BE | F02 | P102 | todo |
| [P104](./P104-writer-queue-uow.md) Writer queue + UnitOfWork | BE | F02 | P102 | todo |
| [P105](./P105-work-locks.md) Khóa truyện có lease + heartbeat | BE | F02 | P104 | todo |
| [P106](./P106-reconcile-retention.md) Reconcile khi khởi động + retention | BE | F02 | P105 | todo |
| [P107](./P107-fts-tim-kiem.md) Hạ tầng tìm kiếm FTS5 tiếng Việt | BE | F02 | P102 | todo |
| [P108](./P108-eventbus-db.md) EventBus lưu DB + replay | BE | F01 | P104 | todo |
| [P109](./P109-stream-tail-payload.md) stream.tail, jobs/{id}/events, payload có kiểu | BE | F01 | P108 | todo |
| [P110](./P110-idempotency.md) Idempotency-Key cho POST | BE | F01 | P104 | todo |
| [P111](./P111-vault-crypto.md) Vault: mã hóa file secrets.enc | BE | F03 | P003 | todo |
| [P112](./P112-secret-store.md) SecretStore + key theo phiên + che log | BE | F03 | P111 | todo |
| [P113](./P113-vault-api.md) API vault + secrets + event vault.status | BE | F03 | P112, P108 | todo |
| [P114](./P114-onboarding-api.md) API trạng thái onboarding | BE | F03 | P102 | todo |
| [P115](./P115-works-crud.md) Bảng works + CRUD tác phẩm | BE | F05 | P104 | todo |
| [P116](./P116-style-profile-languages.md) Style profile + ngôn ngữ + thể loại | BE | F05 | P115 | todo |
| [P117](./P117-library-badge-search.md) Badge thư viện + tìm theo tiêu đề | BE | F05 | P116, P107 | todo |
| [P118](./P118-adapter-anthropic.md) AI: adapter Anthropic | AI | F04 | P002 | todo |
| [P119](./P119-adapter-openai-compatible.md) AI: adapter OpenAI-compatible / Ollama | AI | F04 | P002 | todo |
| [P120](./P120-list-models.md) AI: liệt kê và chuẩn hóa model | AI | F04 | P118, P119 | todo |
| [P121](./P121-retry-limiter-port.md) AI: chính sách retry + ProviderLimiterPort | AI | F04 / F12 | P118 | todo |
| [P122](./P122-providers-crud.md) BE: CRUD provider | BE | F04 | P113 | todo |
| [P123](./P123-discovery-service.md) BE: tự lấy danh sách model + merge | BE | F04 | P122, P120 | todo |
| [P124](./P124-models-roles-resolver.md) BE: thứ tự model, vai trò, model_resolver | BE | F04 | P123, P115 | todo |
| [P125](./P125-limiter-provider.md) BE: limiter theo provider | BE | F04 / F12 | P121, P122 | todo |
| [P126](./P126-chapters-crud.md) BE: bảng chương + tạo/xóa/sắp xếp | BE | F07 | P115 | todo |
| [P127](./P127-working-copy-revision.md) BE: working copy autosave + quy tắc revision | BE | F07 | P126 | todo |
| [P128](./P128-revision-diff-restore.md) BE: diff, restore, xung đột 409 | BE | F07 | P127 | todo |
| [P129](./P129-paragraph-lock-index.md) BE: paragraph projection, khóa chương nền, index | BE | F07 | P128, P107, P105 | todo |
| [P150](./P150-shadcn-base-ui.md) FE: shadcn/ui trên Base UI | FE | UI | P004 | todo |
| [P151](./P151-font-theme.md) FE: font tiếng Việt offline + theme | FE | UI | P150 | todo |
| [P152](./P152-app-shell.md) FE: AppShell ribbon/header/status bar | FE | UI | P151 | todo |
| [P153](./P153-error-empty-states.md) FE: ErrorState, EmptyState, Skeleton, toast | FE | F01 | P150 | todo |
| [P154](./P154-event-bus-fe.md) FE: event bus toàn cục + banner kết nối | FE | F01 | P152 | todo |
| [P155](./P155-hotkeys-palette.md) FE: phím tắt + command palette | FE | UI | P152 | todo |
| [P156](./P156-playwright-mock.md) FE: Playwright + backend giả | FE | Test | P152 | todo |
| [P157](./P157-onboarding-ui.md) FE: luồng lần chạy đầu | FE | F03 | P153, P156 | todo |
| [P158](./P158-vault-ui.md) FE: mở khóa vault + trang Bảo mật | FE | F03 | P153 | todo |
| [P159](./P159-library-ui.md) FE: trang Thư viện | FE | F05 | P153 | todo |
| [P160](./P160-wizard-skeleton.md) FE: khung wizard tạo truyện | FE | F05 | P159 | todo |
| [P161](./P161-settings-models-connection.md) FE: Cài đặt Mô hình AI – kết nối + lấy danh sách | FE | F04 | P153 | todo |
| [P162](./P162-settings-model-list.md) FE: danh sách model kéo thả + effort | FE | F04 | P161 | todo |
| [P163](./P163-settings-roles-concurrency.md) FE: vai trò & effort, đồng thời & ngân sách | FE | F04 / F12 | P161 | todo |
| [P164](./P164-workspace-chapter-tree.md) FE: workspace 3 cột + cây chương | FE | F07 | P152, P014 | todo |
| [P165](./P165-editor-autosave.md) FE: editor đầy đủ + autosave | FE | F07 | P164, P015 | todo |
| [P166](./P166-editor-readonly-focus.md) FE: chương nền chỉ đọc + chế độ tập trung | FE | F07 | P165 | todo |
| [P167](./P167-history-diff.md) FE: lịch sử phiên bản + diff mức từ | FE | F07 | P165 | todo |

### R2 – tiếng Việt, trạng thái/bộ nhớ, viết chương liền mạch, review, đa truyện

| Prompt | Làn | Tính năng | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| [P201](./P201-language-pack-mo-rong.md) AI: mở rộng LanguagePack + dữ liệu tiếng Việt | AI | F08 | P002 | todo |
| [P202](./P202-kiem-tra-xung-ho.md) AI: kiểm tra xưng hô vi.address | AI | F08 | P201 | todo |
| [P203](./P203-kiem-tra-ten-lop-tu.md) AI: kiểm tra tên riêng + lớp từ | AI | F08 | P201 | todo |
| [P204](./P204-kiem-tra-slop-chinh-ta.md) AI: cụm sáo, chính tả, kiểu bỏ dấu, thoại | AI | F08 | P201 | todo |
| [P205](./P205-prompt-loader.md) AI: nạp prompt Jinja2 + manifest | AI | F08 | P201 | todo |
| [P206](./P206-storystate-contracts.md) AI: contract StoryState + StateDelta | AI | F09 | P002 | todo |
| [P207](./P207-apply-delta-v01-v08.md) AI: apply_delta + validator V01–V08 | AI | F09 | P206 | todo |
| [P208](./P208-validator-v09-v15.md) AI: validator V09–V15 | AI | F09 | P207 | todo |
| [P209](./P209-paragraph-ops.md) AI: văn bản theo đoạn + ParagraphOps | AI | F09 / F10 | P002 | todo |
| [P210](./P210-composer-context.md) AI: Composer ngữ cảnh theo lớp | AI | F09 | P206, P205 | todo |
| [P211](./P211-token-tail-text.md) AI: đếm token + cắt tail_text | AI | F09 | P210 | todo |
| [P212](./P212-summaries.md) AI: tóm tắt phân tầng | AI | F09 | P210, P205 | todo |
| [P213](./P213-planner-pacing.md) AI: bước Planner + nhịp truyện | AI | F10 | P210, P118 | todo |
| [P214](./P214-writer-step.md) AI: bước Writer (nối chương) | AI | F10 | P213, P211 | todo |
| [P215](./P215-settlement-step.md) AI: bước Settle (delta + ending_state) | AI | F10 | P214, P207 | todo |
| [P216](./P216-validate-seam.md) AI: validator LLM + kiểm tra mối nối | AI | F10 | P215 | todo |
| [P217](./P217-reviewer-step.md) AI: bước Review | AI | F10 | P216, P202, P203, P204 | todo |
| [P218](./P218-repair-loop.md) AI: vòng sửa cục bộ | AI | F10 | P217, P209 | todo |
| [P219](./P219-pipeline-orchestration.md) AI: điều phối pipeline một chương | AI | F10 | P218, P212, P121 | todo |
| [P220](./P220-outline-review.md) AI: xét lại dàn ý mỗi K chương | AI | F10 | P219 | todo |
| [P221](./P221-revise-workflow.md) AI: workflow sửa theo yêu cầu tác giả | AI | F11 | P219 | todo |
| [P222](./P222-foundation-workflow.md) AI: workflow nền truyện | AI | F06 | P206, P205 | todo |
| [P230](./P230-language-be.md) BE: gói ngôn ngữ khi lưu + API kiểm tra | BE | F08 | P129, P204 | todo |
| [P231](./P231-memory-tables.md) BE: bảng trạng thái và bộ nhớ | BE | F09 | P126 | todo |
| [P232](./P232-apply-delta-transaction.md) BE: áp StateDelta trong một transaction | BE | F09 | P231, P208 | todo |
| [P233](./P233-memory-api-context-port.md) BE: API trạng thái/bộ nhớ + ContextPort | BE | F09 | P232, P107 | todo |
| [P234](./P234-longform-tables.md) BE: bảng handoff, plan, candidate, findings | BE | F10 / F11 | P231 | todo |
| [P235](./P235-write-job-runner.md) BE: job viết chương chạy pipeline | BE | F10 | P234, P233, P219, P124, P125 | todo |
| [P236](./P236-commit-gate.md) BE: cổng vào + commit một transaction | BE | F10 | P235 | todo |
| [P237](./P237-continuity-api.md) BE: API liền mạch + chỉ số | BE | F10 | P236 | todo |
| [P238](./P238-candidate-accept.md) BE: nhận candidate (cả chương / từng đoạn) | BE | F11 | P236 | todo |
| [P239](./P239-findings-api.md) BE: findings resolve/dismiss | BE | F11 | P238 | todo |
| [P240](./P240-revise-resync.md) BE: job sửa + stale_from + resync | BE | F11 | P239, P221 | todo |
| [P241](./P241-chapter-structure-rules.md) BE: chèn/xóa/sắp xếp chương giữa truyện | BE | F11 | P240 | todo |
| [P242](./P242-scheduler-fair.md) BE: scheduler đa truyện xoay vòng công bằng | BE | F12 | P236 | todo |
| [P243](./P243-waiting-budget.md) BE: lý do chờ + ngân sách | BE | F12 | P242 | todo |
| [P244](./P244-autowrite-api.md) BE: API auto-write 3 chế độ | BE | F12 | P243 | todo |
| [P245](./P245-estimate-queues.md) BE: ước tính chi phí + API hàng đợi | BE | F12 | P244 | todo |
| [P246](./P246-foundation-job.md) BE: job nền truyện + seed state | BE | F06 | P232, P222 | todo |
| [P247](./P247-story-bible-crud.md) BE: CRUD Story Bible + bible_revisions | BE | F06 | P246 | todo |
| [P248](./P248-export.md) BE: xuất TXT/Markdown/EPUB | BE | F13 | P129 | todo |
| [P249](./P249-backup-restore.md) BE: sao lưu + khôi phục | BE | F13 | P104 | todo |
| [P250](./P250-usage-cost.md) BE: ghi usage + chi phí | BE | F14 | P235 | todo |
| [P251](./P251-notifications-be.md) BE: notification outbox + event | BE | F14 | P108 | todo |
| [P252](./P252-logs-storage.md) BE: log AI debug + lưu trữ + dọn dẹp | BE | F14 | P235 | todo |
| [P270](./P270-language-style-ui.md) FE: cài đặt ngôn ngữ + style profile | FE | F08 | P153 | todo |
| [P271](./P271-memory-ui.md) FE: tab Nhớ + tìm kiếm + trace | FE | F09 | P164 | todo |
| [P272](./P272-ai-tab-stream.md) FE: tab AI + CandidateStream | FE | F10 | P164, P154 | todo |
| [P273](./P273-noi-tab-banner.md) FE: tab Nối + banner bị chặn | FE | F10 | P272 | todo |
| [P274](./P274-review-diff-ui.md) FE: màn Review/Diff | FE | F11 | P167 | todo |
| [P275](./P275-findings-conflict-resync.md) FE: findings, xung đột, resync | FE | F11 | P274 | todo |
| [P276](./P276-writing-room-table.md) FE: Phòng viết – bảng truyện | FE | F12 | P154 | todo |
| [P277](./P277-writing-room-log-cost.md) FE: Phòng viết – log, chi phí, chỉ báo header | FE | F12 / F14 | P276 | todo |
| [P278](./P278-autowrite-dialog.md) FE: hộp thoại auto-write + ước tính | FE | F12 | P276 | todo |
| [P279](./P279-story-bible-characters.md) FE: Story Bible – nhân vật, xưng hô, facts, hooks | FE | F06 | P271 | todo |
| [P280](./P280-story-bible-timeline.md) FE: Story Bible – dàn ý, timeline, đồ thị, thanh trượt | FE | F06 | P279 | todo |
| [P281](./P281-wizard-foundation-steps.md) FE: wizard – nền truyện, xưng hô, dàn ý | FE | F06 / F05 | P160, P279 | todo |
| [P282](./P282-export-backup-ui.md) FE: hộp thoại xuất + trang sao lưu | FE | F13 | P153 | todo |
| [P283](./P283-notifications-ui.md) FE: trung tâm thông báo + thông báo native | FE | F14 | P154 | todo |
| [P284](./P284-logs-storage-ui.md) FE: trang Nhật ký/chi phí + Lưu trữ | FE | F14 | P153 | todo |
| [P290](./P290-keep-awake.md) DESKTOP: giữ máy thức khi auto-write | DESKTOP | F14 | P012 | todo |

### TEST – dữ liệu mẫu, harness, nghiệm thu

| Prompt | Làn | Tính năng | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| [P901](./P901-fixture-truyen-mau.md) TEST: truyện mẫu tiên hiệp + đô thị | TEST | tests | P001 | todo |
| [P902](./P902-fixture-220-chuong.md) TEST: truyện tổng hợp 220 chương | TEST | tests | P901 | todo |
| [P903](./P903-fixture-state.md) TEST: StoryState mẫu + delta sai | TEST | tests | P206 | todo |
| [P904](./P904-fixture-vi-checks.md) TEST: ca kiểm tra tiếng Việt | TEST | tests | P001 | todo |
| [P905](./P905-mock-provider-mo-rong.md) TEST: mở rộng mock provider | TEST | tests | P002 | todo |
| [P906](./P906-harness-tich-hop.md) TEST: harness tích hợp + marker luồng | TEST | tests | P905, P003 | todo |
| [P907](./P907-map-kich-ban.md) TEST: ánh xạ kịch bản → file test (xfail) | TEST | tests | P906 | todo |
| [P908](./P908-nghiem-thu-mvp.md) Nghiệm thu MVP: 3 truyện × 20 chương | Tất cả | Plan §9 G4 | P245, P241, P247 | todo |

