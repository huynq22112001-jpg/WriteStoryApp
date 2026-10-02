# Rà soát phần đã có trong code

Ngày rà soát: 02/10/2026

Đối chiếu code hiện tại với các prompt trong `docs/prompts/` và ghi nhận những phần đã có dấu vết triển khai. Các file prompt mô tả công việc cần làm; chúng không thay đổi phạm vi yêu cầu của người dùng trong lần rà soát này.

## Kết luận

Đã có khung monorepo và code nền R0. Từ lần rà soát ban đầu, P001, P002, P003 và P005 đã được kiểm chứng và hoàn thành; P004 còn bị chặn ở kiểm tra FE. Các prompt khác chỉ được xem là đã làm khi đạt điều kiện riêng của chúng.

## Prompt đã hoàn thành

| Prompt | Bằng chứng |
|---|---|
| P001 | uv 0.12.22, uv-managed Python 3.14.8; `uv sync` tạo `.venv/` và `uv.lock`. |
| P002 | `uv run pytest ai/tests -q`: 25 passed; `uv run ruff check ai`: pass. |
| P003 | `uv run pytest be/tests -q`: 38 passed; `uv run ruff check be tools`: pass; bổ sung `PROVIDER_SERVER_ERROR` 502 retryable. |
| P005 | Backend dev health 200, thiếu token 401, mock SSE phát `token.delta` cho 3 truyện; server đã dừng. |

## Phần đã có trong repo

| Nhóm / prompt liên quan | Đã có | Còn thiếu hoặc chưa xác nhận |
|---|---|---|
| S01, P001 | Có `uv.lock`, `.venv/`, uv 0.12.22 và Python 3.14.8; `uv sync` thành công. | README gốc vẫn chưa có; thuộc P008. |
| P002, nền AI | Contracts, provider mock, LanguagePack tiếng Việt; 25 test pass, Ruff pass, test ranh giới pass. | Các tính năng tiếng Việt nâng cao P201–P204 chưa làm. |
| P003, nền BE | Bootstrap, bảo mật, EventBus, health/SSE và SQLite engine; 38 test pass, Ruff pass. | Chưa có migration/bảng, writer queue hay UnitOfWork. |
| P004, nền FE | Vite/React/TypeScript, API client, SSE, i18n và các trang nền; đã thêm khóa `PROVIDER_SERVER_ERROR`. | Typecheck/test/build chưa chạy: pnpm chặn `@asamuzakjp/dom-selector@9.2.3` và `@types/node@26.6.4` theo ngưỡng tuổi phát hành tối thiểu. |
| P005, dev health | Health 200, thiếu token 401, mock-runs 202 và nhận token delta từ ba truyện; server đã dừng. | Script chạy BE+FE và smoke UI thuộc P008 chưa làm. |
| P006, một phần xuất OpenAPI | Có `tools/contracts/export_openapi.py`; app factory gắn `ErrorResponse` làm phản hồi lỗi mặc định và đã có test unit kiểm tra schema lỗi. Model `EventEnvelope` cũng đã có. | Chưa có `contracts/openapi.json`, `api/openapi.py` để thêm EventEnvelope vào OpenAPI, hoặc contract snapshot test theo yêu cầu P006. |
| P201, nền ngôn ngữ tái sử dụng | Có LanguagePack tiếng Việt cơ bản (chuẩn hóa NFC, đếm âm tiết, fold tìm kiếm). | Chưa có bộ kiểm tra tiếng Việt mở rộng của P201–P204 như xưng hô, tên riêng/lớp từ, cụm sáo/chính tả/thoại. |

## Chưa thấy triển khai tính năng theo các prompt còn lại

- P007–P020: chưa có API types sinh tự động, script dev gốc/README gốc, Tauri desktop, editor Tiptap/IME, đóng gói hoặc nghiệm thu R0.
- P101–P129: chưa có Alembic/migrations, bảng và API dữ liệu, vault/provider CRUD, chương/revision/locks.
- P150–P167 và P270–P284: chưa có các màn hình tính năng tương ứng như onboarding/vault/settings/workspace/editor/history, Story Bible, review, auto-write, thông báo và nhật ký. Frontend hiện chủ yếu là shell/trạng thái hệ thống/thư viện cơ bản.
- P202–P252: chưa thấy pipeline viết truyện, state/delta, bộ nhớ, scheduler, job runner, export/backup, chi phí hoặc notification backend.
- P290 và P901–P908: chưa thấy desktop keep-awake, fixtures/harness nghiệm thu MVP.

## Dấu hiệu môi trường được kiểm tra

- Có `.python-version`, `uv.lock`, `.venv/`; uv/Python đã cài trong user profile. `pnpm` có sẵn.
- Chưa có `README.md` gốc, `contracts/openapi.json`, `tools/dev/run_dev.py`, thư mục `desktop/`, `tests/` gốc, hoặc `fe/src/shared/api/generated/schema.d.ts`.
- `docs/steps/TRANG-THAI.md` cũng ghi code nền là bản nháp chưa kiểm chứng và đánh dấu S07–S10/R1/R2 chưa làm.

## Bước tiếp theo

Tiếp tục P004 sau khi xử lý được chặn tuổi phát hành của pnpm; sau đó đi tiếp R0 theo cột phụ thuộc trong `docs/prompts/README.md`.
