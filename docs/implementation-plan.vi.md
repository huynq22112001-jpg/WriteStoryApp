# Kế hoạch xây dựng WriteStoryApp

Ngày lập/cập nhật: 02/10/2026 (bản sửa sau rà soát). Trạng thái: kế hoạch đề xuất, đã đối chiếu mã nguồn InkOS 2.0 và kiểm chứng web các giả định kỹ thuật chính; chưa triển khai hoặc đo benchmark.

Phần 1–13 là kiến trúc desktop/Python/local và lộ trình MVP. Phần 14–21 bổ sung phạm vi toàn bộ tính năng và luồng của InkOS, mapping sang WriteStoryApp, dữ liệu mở rộng, lộ trình đầy đủ và tiêu chí nghiệm thu. Chỉ mục nguồn để kiểm tra lại: [inkos-source-inventory.json](./inkos-source-inventory.json).

Phần 22 cập nhật yêu cầu tách `fe/`, `be/`, `ai/` thành các thư mục riêng. Thiết kế chi tiết và danh mục nguồn chính thức: [folder-architecture.vi.md](./folder-architecture.vi.md). **Rà soát 02/10/2026:** kết quả kiểm chứng web (có URL nguồn), phân tích luồng chương InkOS, thiết kế đa truyện và liền mạch chương nằm tại [review-and-optimization.vi.md](./review-and-optimization.vi.md). Các thay đổi đã được áp vào tài liệu này: §2 stack, §3.1 data-root macOS, §4.2–4.3 đồng thời đa truyện, §5 dữ liệu/search, §6 pipeline chương, §7 API, §9 giai đoạn và tiêu chí, §10 ký macOS, FL04/FL05/FL24 và §21. Bố cục giao diện và thư viện React: [ui-design.vi.md](./ui-design.vi.md).

Tài liệu triển khai chia nhỏ theo tính năng (BE/FE/AI riêng) tại [features/](./features/README.md) và test theo luồng tại [tests/](./tests/README.md).

Hai yêu cầu cốt lõi được ưu tiên trong MVP: **(1) chạy đồng thời nhiều truyện; (2) trong một truyện viết tuần tự từng chương, nội dung liên tiếp, không đứt mạch.**

Bản bổ sung hiện chia thành 146 hạng mục chức năng trong 15 nhóm, 26 luồng nghiệp vụ và 20 nhóm phương pháp sáng tác. Đây là phân rã backlog của WriteStoryApp từ bề mặt nguồn đã rà soát, không phải số tính năng đã triển khai trong WriteStoryApp.

## 1. Phạm vi đã chốt

- App desktop tự chứa, dùng cá nhân, chạy trên Windows và macOS.
- Cập nhật theo yêu cầu: gom toàn bộ dữ liệu ứng dụng vào một thư mục `data`. Windows portable: cạnh phần mềm. macOS: thư mục người dùng chọn ở lần chạy đầu vì App Translocation (§3.1). Không phân tán dữ liệu sang nhiều nơi.
- Frontend React; backend và phần xử lý AI bằng Python chạy trên máy người dùng.
- Tham khảo kiến trúc InkOS tại `E:\Inke\inkos`, nhưng thiết kế dữ liệu và đóng gói phù hợp app desktop.
- Tác phẩm, chương, thiết lập, lịch sử và tác vụ lưu local; không cần tài khoản hoặc server của nhà phát triển.
- Có thể gọi AI cloud bằng API key của người dùng. App local không đồng nghĩa AI offline: AI cloud vẫn cần internet và gửi ngữ cảnh truyện tới nhà cung cấp được chọn.
- AI offline là tùy chọn mở rộng qua Ollama/LM Studio chạy trên máy. Không tự tải model lớn hoặc đóng gói model vào installer mặc định.
- **Đa ngôn ngữ về kiến trúc, tiếng Việt làm trước.** Cả giao diện và nội dung truyện đi qua cơ chế ngôn ngữ chung: UI dùng i18n, mỗi tác phẩm có trường ngôn ngữ, phần xử lý phụ thuộc ngôn ngữ nằm trong **gói ngôn ngữ** (§6.6). MVP chỉ bật và hoàn thiện gói `vi`; ngôn ngữ khác (ví dụ tiếng Anh) thêm sau bằng gói mới, không sửa pipeline.

MVP tập trung truyện dài: thư viện, nền truyện, dàn ý, nhân vật, editor, viết chương bằng AI, review/revise, lịch sử và export. Phạm vi đầy đủ bao gồm toàn bộ nhóm chức năng InkOS trong phần 15: truyện ngắn, fanfic/ngoại truyện/phong cách, kịch bản, storyboard, film phân nhánh, Play, ảnh, dịch thuật, nghiên cứu, tự động hóa và các kênh điều khiển. Các nhóm ngoài MVP có giai đoạn thực hiện cụ thể trong phần 20, không bị loại khỏi kế hoạch.

## 2. Stack đề xuất

| Tầng | Lựa chọn | Lý do |
|---|---|---|
| Desktop shell | Tauri 2, Rust | Tận dụng webview hệ điều hành; Rust quản lý cửa sổ, đường dẫn dữ liệu và vòng đời Python |
| FE | React, TypeScript, Vite | Phù hợp UI nhiều panel và editor; build frontend thành tài nguyên local |
| UI | Tailwind CSS v4, shadcn/ui trên Base UI, Lucide; react-resizable-panels (3 cột kéo giãn/thu gọn); sonner; cmdk | Base UI là mặc định của shadcn từ 07/2026; chi tiết và lý do chọn tại [ui-design.vi.md](./ui-design.vi.md) |
| Router, form, i18n | TanStack Router (hash history), react-hook-form + zod 4, i18next + react-i18next | Route có type cho `?chapter=&tab=`; thông báo lỗi form theo ngôn ngữ. MVP chỉ có resource `vi`; thêm ngôn ngữ UI bằng file JSON mới |
| Danh sách, cây, diff, biểu đồ | TanStack Virtual, react-arborist, dnd-kit, jsdiff (diff mức từ trong Web Worker), Recharts, React Flow (lazy) | Hàng nghìn chương; kéo thả cây chương và hàng đợi; diff văn xuôi; chi phí; đồ thị quan hệ |
| Font | Fontsource: Be Vietnam Pro / Inter (UI), Noto Serif (đọc/viết), subset vietnamese | Đóng gói offline, không phụ thuộc Google Fonts |
| Editor | Tiptap/ProseMirror với extension cộng đồng; pin `prosemirror-view` ≥ 1.41.9 | Chỉnh sửa chương, selection, undo/redo, JSON document; không cần extension thương mại trong MVP. Bản 1.41.9 sửa xử lý backspace trong composition trên Chrome, liên quan cơ chế gõ của Unikey/EVKey; IME tiếng Việt phải test ở R0 |
| State UI | Zustand | Trạng thái panel, lựa chọn tác phẩm và tùy chọn giao diện |
| Dữ liệu API | TanStack Query | Cache, invalidation và đồng bộ dữ liệu từ backend |
| BE | Python FastAPI, Pydantic 2 | API có schema rõ, async phù hợp gọi AI và streaming |
| HTTP server | Uvicorn | Chạy một backend local, một process API trong MVP |
| Python/dependency | CPython 3.14 (bản GIL tiêu chuẩn) làm baseline, uv, lockfile | 3.14.8 là bản ổn định mới nhất (30/09/2026), PyInstaller hỗ trợ 3.14 từ 6.15.0; free-threaded ở 3.14 vẫn tùy chọn (PEP 779) nên không dùng; chưa dùng 3.15 tới khi có vài bản vá |
| HTTP tới AI | httpx.AsyncClient và adapter cho SDK nhà cung cấp | Async, timeout, connection pool và thống nhất output giữa các provider |
| Workflow AI | State machine Python rõ ràng, Pydantic contracts | Kiểm soát từng bước, checkpoint, retry và version; chưa cần framework orchestration lớn |
| Tác vụ nền | asyncio: scheduler đa truyện + hàng đợi theo truyện + limiter theo provider + jobs/checkpoints trong SQLite | Nhiều truyện chạy song song, chương trong một truyện tuần tự; phục hồi sau crash (§4.2) |
| DB | SQLite WAL, SQLAlchemy 2 async, aiosqlite, Alembic | Dùng local, không cần cài DB riêng. aiosqlite chạy mỗi connection trên thread nền, không phải I/O non-blocking thật; cấu hình transaction tường minh và commit qua writer queue |
| Search MVP | SQLite FTS5 `unicode61 remove_diacritics 2`, BM25, chuẩn hóa `đ→d` ở tầng app | Đã chạy thử: giá trị mặc định 1 bỏ sót chữ hai dấu (ộ, ễ…), và FTS5 không gập `đ→d` |
| Secret | Vault `data/secrets.enc`, Python cryptography ≥ 44, AES-GCM + Argon2id (Scrypt dự phòng) | Argon2id theo OWASP (tối thiểu m=19 MiB, t=2, p=1); nonce 12 byte không dùng lại; khóa chỉ giữ trong RAM khi mở vault |
| Streaming FE | SSE: BE dùng `fastapi.sse.EventSourceResponse` (FastAPI ≥ 0.135), FE đọc bằng fetch streaming | Native SSE có ping và `Last-Event-ID` làm event cursor; fetch giữ được Authorization header (EventSource không gửi được) |
| Đóng gói Python | PyInstaller **onedir**, đưa vào Tauri qua `bundle.resources` dạng `"dir/"`; launcher sidecar có hậu tố target-triple | Onefile giải nén vào `_MEIxxxx` mỗi lần chạy và sinh thêm tiến trình bootloader khó dừng; onedir tránh cả hai |
| Test | pytest, pytest-asyncio, React Testing Library/Vitest; E2E phù hợp mỗi OS | Kiểm tra logic, async, UI và bản installer thực tế |
| Chất lượng code | Ruff, type checker Python; TypeScript/ESLint | Kiểm tra chất lượng trước build |
| Phát hành | GitHub Actions theo OS/architecture | Build, test, ký và xuất installer theo từng nền tảng |

FastAPI vừa là BE vừa gọi AI Python, giúp giảm một tầng IPC/service. Rust chỉ xử lý tích hợp desktop và vòng đời tiến trình. Không dùng Redis/Celery/Docker trong runtime của MVP.

Tauri là lựa chọn có điều kiện: webview của Windows/macOS khác nhau. Tuần đầu phải thử editor, IME tiếng Việt, streaming và installer. Nếu các lỗi webview không thể xử lý trong ngân sách spike, chuyển desktop shell sang Electron; FE và BE vẫn giữ nguyên. Tổng dung lượng app cần đo vì Python bundle có thể chiếm phần lớn installer.

## 3. Kiến trúc runtime

```text
Tauri desktop application
  ├─ Rust: single-instance, process manager, paths, dialogs
  ├─ React: library, editor, AI panel, task progress
  └─ Python bundled backend
       ├─ FastAPI trên loopback, cổng được cấp động
       ├─ AI workflow supervisor / asyncio
       ├─ SQLite: tác phẩm, phiên bản, trạng thái, jobs, events
       ├─ Asset files: ảnh và file nhập; exports/backups
       └─ AI adapters → cloud API hoặc Ollama/LM Studio local
```

Vòng đời mở app:

1. Rust xác định đường dẫn tuyệt đối tới thư mục `data` theo chế độ chạy, kiểm tra quyền ghi và giành single-instance/data-root lock.
2. Sinh token ngẫu nhiên cho phiên backend, khởi chạy binary Python đã bundle bằng đường dẫn tuyệt đối. Windows không mở cửa sổ console phụ.
3. Truyền cấu hình bootstrap qua pipe, bao gồm data-root tuyệt đối; không đưa token vào URL hoặc log. Python và Rust dùng chung data-root, không tự suy ra từ working directory.
4. Python bind loopback vào cổng trống bằng socket do OS cấp, chạy migration, báo readiness với port/protocol version. Giữ socket đã bind khi trao cho Uvicorn để tránh tranh chấp cổng.
5. Rust kiểm tra readiness rồi FE kết nối qua client API chung.
6. FE stream sự kiện bằng fetch có Authorization header. Không dùng native EventSource theo cách phải đặt token trong query string.
7. Khi đóng app, gọi endpoint shutdown để Python checkpoint và dừng có thời hạn; sau đó terminate child nếu cần. Xử lý cả `RunEvent::ExitRequested` và `RunEvent::Exit` (macOS có thể không phát `ExitRequested` khi quit). plugin-shell chỉ kill tiến trình con trực tiếp, nên Windows gắn backend vào Job Object (kill-on-close) và macOS để backend tự thoát khi pipe bootstrap đóng (Python theo dõi EOF trên stdin).

Backend chỉ nhận kết nối loopback; xác minh token, Host và Origin. CORS/CSP giới hạn theo origin Tauri thực tế trên mỗi OS và origin dev. Tauri IPC chỉ cho phép các command/capability cần thiết, không cung cấp chạy shell tùy ý cho frontend.

### 3.1 Thư mục data theo yêu cầu mới

Trong môi trường phát triển hiện tại: `E:\pm\WriteStoryApp\data\`.

Windows portable:

```text
WriteStoryApp/
  WriteStoryApp.exe
  backend/                    Binary Python và thư viện đóng gói
  data/
    db/app.sqlite3            Tác phẩm, chương, history, state, jobs, settings
    assets/                   Ảnh và tài nguyên tác phẩm
    imports/                  Bản sao tài liệu đã nhập
    exports/                  TXT, Markdown, EPUB đã xuất
    backups/                  Các bản backup nhất quán
    logs/                     Log đã che thông tin bí mật
    cache/                    Dữ liệu có thể tạo lại
    tmp/                      File tạm
    secrets.enc               Vault API key mã hóa, tạo khi người dùng cấu hình
```

macOS (data-root do người dùng chọn ở lần chạy đầu, xem bên dưới):

```text
/Applications/WriteStoryApp.app
<data-root đã chọn>/           Cùng cấu trúc data bên trên
~/Library/Application Support/WriteStoryApp/data-root.json   Chỉ chứa con trỏ tới data-root
```

Trên macOS, **không được dựa vào việc `data` nằm cạnh `.app`**. Đã kiểm chứng: khi app có cờ quarantine và được mở từ vị trí tải về (Downloads, zip, DMG) mà chưa kéo bằng Finder, Gatekeeper chạy app từ một đường dẫn ngẫu nhiên chỉ đọc (App Translocation), nên không thấy thư mục bên cạnh. Apple khuyên app phải chạy đúng cả khi bị translocate ([Apple DTS](https://developer.apple.com/forums/thread/724969)).

Quy tắc data-root trên macOS:

1. Đọc con trỏ data-root từ `~/Library/Application Support/WriteStoryApp/data-root.json` (file nhỏ, chỉ chứa đường dẫn tuyệt đối và ID data).
2. Nếu chưa có: phát hiện translocation (đường dẫn executable chứa `/AppTranslocation/`) → hướng dẫn người dùng kéo app vào Applications và mở lại. Nếu không bị translocate → hiện bước chọn data-root, gợi ý mặc định là thư mục `data` cạnh `.app` khi ghi được, nếu không thì `~/Library/Application Support/WriteStoryApp/data`.
3. Ghi con trỏ, khóa data-root và tiếp tục như Windows.
4. Phát hành DMG có symlink `/Applications` để người dùng kéo thả; app đã được kéo bằng Finder không bị translocate.

Con trỏ data-root là ngoại lệ duy nhất nằm ngoài `data`; nó không chứa bản thảo hay secret.

Windows portable đặt phần mềm ở thư mục có quyền ghi, như ổ D/E hoặc thư mục cá nhân. `Program Files` thường không cho user thường ghi trực tiếp. Nếu vị trí cạnh app không ghi được, hiển thị lỗi/chọn thư mục data có quyền ghi; không tự chuyển dữ liệu sang AppData mà không cho người dùng biết. Không chạy app bằng administrator chỉ để lưu dữ liệu.

Data-root là duy nhất cho mỗi lần chạy, được truyền bằng đường dẫn tuyệt đối; DB và asset references trong data dùng đường dẫn tương đối để có thể chuyển cả thư mục sang máy khác. Không cho hai backend đồng thời mở cùng data-root để chạy workflow. Không dùng data đang hoạt động trên network share hoặc thư mục bị cloud sync trực tiếp; di chuyển/đồng bộ bằng backup đã đóng gói.

Thư mục data chứa mọi dữ liệu do ứng dụng quản lý. Cache hệ thống của webview, chứng chỉ ký và runtime OS có thể được hệ điều hành quản lý riêng; frontend không lưu bản thảo/cấu hình bền vững vào localStorage ngoài data.

Vault không dùng khóa hard-code trong app hoặc khóa lưu bên cạnh ciphertext. Nếu không muốn nhập mật khẩu vault, người dùng có thể chỉ cung cấp API key cho phiên hiện tại; không persist plaintext. Khi chuyển data giữa Win/Mac, mở vault bằng mật khẩu đã chọn. Các tùy chọn bỏ vault/lưu key vào OS keychain chỉ thêm nếu người dùng đổi yêu cầu.

## 4. Đồng thời, đa luồng và hiệu năng

### 4.1 Phân loại công việc

| Loại việc | Cách thực hiện |
|---|---|
| Chờ AI API, streaming, chờ HTTP | asyncio, client async, semaphore |
| SDK/đọc file blocking có thời gian ngắn | asyncio.to_thread hoặc thread pool có giới hạn |
| Parse PDF lớn, tokenize, tính toán CPU nặng | Worker process/ProcessPoolExecutor khi đo thấy cần |
| Ghi dữ liệu | Transaction ngắn, điều phối ghi; SQLite có một writer tại một thời điểm |
| UI và editor | Webview/React; debounce autosave, không render toàn editor mỗi token |

Async không làm một lần suy luận của model nhanh hơn. Nó giúp app đáp ứng trong lúc chờ và xử lý nhiều tác vụ I/O. Thread Python không phải phương án mặc định cho tăng tốc CPU-bound do GIL trong runtime phổ biến; dùng process hoặc thư viện native khi phù hợp.

Với Windows và Python frozen binary, kiểm tra `multiprocessing.freeze_support`, entrypoint guard và spawn; tránh child process khởi động lại toàn backend. Process pool chỉ nhận dữ liệu có thể serialize, không dùng chung SQLite connection/session giữa các process. Không mở process pool nếu tác vụ nhẹ hoặc chưa có nhu cầu.

### 4.2 Quy tắc concurrency: nhiều truyện song song, chương tuần tự

```text
                ┌──────────── Global Scheduler (asyncio, 1 process) ────────────┐
Work A queue →  │  ready set: truyện có job kế tiếp và không bị chặn            │
Work B queue →  │  chọn xoay vòng có trọng số (fair round-robin)               │→ Worker pool (N)
Work C queue →  │  mỗi truyện tối đa 1 job ghi đang chạy                        │
                └───────────────────────────────────────────────────────────────┘
                                    │
               Provider limiter: concurrency + token bucket (RPM/TPM) + Retry-After
                                    │
                         Cloud API / Ollama / LM Studio
```

- **Giữa các truyện: song song.** Số job chạy cùng lúc = `min(worker pool, giới hạn provider)`. Mặc định worker pool 4; người dùng chỉnh trong Settings.
- **Trong một truyện: tuần tự tuyệt đối.** Mỗi truyện có một hàng đợi FIFO; tối đa 1 job ghi (write/revise/resync/import/rollback) tại một thời điểm. Chương N+1 chỉ được enqueue khi chương N đã commit cùng state hợp lệ (§6).
- **Công bằng:** scheduler xoay vòng theo truyện, không lấy N truyện đầu danh sách (InkOS dùng `activeBooks.slice(0, N)` nên truyện xếp sau có thể không bao giờ được chạy). Truyện người dùng đang mở được cộng trọng số ưu tiên.
- **Khóa truyện:** bảng `work_locks` trong SQLite có lease + heartbeat. Job đến sau **xếp hàng** (`waiting_slot`) thay vì fail-fast như InkOS (`409 BOOK_BUSY`). Thao tác đọc và sửa tay trên UI không cần khóa; sửa tay dùng expected revision.
- **Limiter theo provider:** `max_concurrent_requests` (cloud mặc định 3–4, local mặc định 1 để tránh tăng VRAM/RAM), token bucket RPM/TPM, retry tối đa 3 lần với exponential backoff + jitter, ưu tiên header `Retry-After`; không retry 401/403/model-not-found. Một semaphore toàn app không thay thế giới hạn từng provider.
- **Ngân sách:** token/ngày và chi phí ước tính/ngày theo truyện và toàn app, lưu bền theo timezone cấu hình; hết ngân sách → job chuyển `waiting_slot` với lý do rõ ràng.
- **Tác vụ phụ độc lập** (review lại chương đã commit, chấm điểm, research, retrieval, dịch) chạy song song trong ngân sách riêng; không chạy song song các bước có phụ thuộc dữ liệu.
- **SQLite một writer:** không giữ transaction hoặc DB write lock trong lúc đợi AI. Commit đi qua một writer queue nội bộ (một task asyncio nhận lệnh commit) kèm `busy_timeout`, tránh `database is locked` khi nhiều truyện commit gần nhau. Nút cổ chai thực tế là API AI, không phải commit; đo ở R0.
- Editor có optimistic concurrency: AI tạo candidate từ revision nào thì phải ghi rõ. Nếu người dùng sửa bản gốc khi AI chạy, yêu cầu xử lý xung đột; không ghi đè bản mới.

Chế độ auto-write theo truyện:

| Chế độ | Hành vi |
|---|---|
| `auto` | Commit khi qua mọi cổng kiểm tra; dừng batch của truyện đó nếu rơi vào `waiting_user` |
| `review_each` | Mỗi chương dừng ở `waiting_user`; chương sau chỉ chạy sau khi tác giả accept |
| `review_every_k` | Auto, nhưng dừng chờ duyệt mỗi K chương |

Không bao giờ viết chương N+1 dựa trên candidate chưa commit của chương N. Một truyện bị dừng không ảnh hưởng các truyện khác.

### 4.3 Tác vụ nền và phục hồi

API tạo job, lưu DB và trả job ID ngay. Supervisor trong cùng process nhận job đã persist, chạy ngoài vòng đời request HTTP. Không dùng một FastAPI BackgroundTasks không có persistence làm cơ chế chính.

Trạng thái đề xuất:

```text
queued → waiting_slot (chờ worker/provider/ngân sách/khóa truyện) → running → succeeded
                                                                        ├─ waiting_user
                                                                        ├─ blocked (truyện needs_resync)
                                                                        ├─ failed
                                                                        ├─ cancelled
                                                                        └─ interrupted (sau crash/đóng app)
```

Trạng thái liền mạch của truyện tách khỏi trạng thái job: `work.continuity_status = ok | blocked_needs_resync | stale_from(K)`. Khi truyện `blocked_needs_resync`, scheduler không lấy job viết mới của truyện đó; các truyện khác vẫn chạy.

Job cần: idempotency key, type, work ID, queue position, priority, input/base revision, stage, checkpoint, progress, cancellation, error code và usage (gồm cache read/write tokens). Khi app khởi động lại, reconcile job running thành interrupted, kiểm tra checkpoint và cho phép resume từ bước hợp lệ cuối cùng.

MVP phục hồi ở ranh giới từng bước. Nếu app tắt giữa một request generation, lưu được bản nháp thì hiển thị nó nhưng không coi là chương hoàn chỉnh. Không hứa resume chính xác từng token hoặc exactly-once billing; retry có thể phát sinh thêm chi phí từ provider.

### 4.4 Mục tiêu hiệu năng để kiểm chứng

Các số dưới đây là tiêu chí đề xuất, chưa phải benchmark:

- API tạo job trả trong khoảng 300 ms ở p95 khi chạy local, không chờ AI hoàn tất.
- Mở chương đã lưu trong khoảng 300 ms sau khi backend sẵn sàng, với corpus thử nghiệm đã thống nhất.
- Khởi động lạnh tới backend ready mục tiêu dưới 5 giây trên máy tham chiếu; đo riêng từng OS và cách bundle Python.
- Độ trễ từ event backend tới UI mục tiêu dưới 200 ms; không bao gồm thời gian provider sinh token.
- Streaming cập nhật theo batch khoảng 50–100 ms, có backpressure và giới hạn buffer/log.
- Autosave debounce khoảng 500–1.000 ms; flush khi đổi chương/đóng cửa sổ, báo rõ nếu chưa lưu được.
- Test thư viện khoảng 50 tác phẩm, tổng 10.000 chương; chỉ tải trang metadata cần thiết, không nạp toàn bộ bản thảo vào state FE.
- Chạy đồng thời 3–5 truyện auto-write với mock provider có độ trễ thật: editor vẫn gõ mượt, không có lỗi `database is locked`, mọi truyện đều tiến (không truyện nào bị bỏ đói).

Đo CPU/RAM idle, startup, thời gian gọi AI, latency DB và số lần render. Lazy-load các thư viện nặng như PDF parser/embedding; không đưa PyTorch hoặc model weights vào bundle mặc định. Tạo index theo work ID, chapter number, job status và revision; dùng pagination và giới hạn log/cache. Chỉ tối ưu thêm khi có số liệu. RAM inference local được đo riêng theo model và hardware.

## 5. Mô hình dữ liệu

| Bảng | Nội dung |
|---|---|
| projects | Không gian làm việc và thiết lập |
| works | Tác phẩm, ngôn ngữ (`vi` mặc định; MVP chỉ cho `vi`), thể loại, giọng văn, mục tiêu; `status` (draft/ready/archived), `continuity_status` (ok/blocked_needs_resync/stale_from) + `continuity_chapter_no` + `continuity_reason`, ngân sách riêng của truyện |
| address_rules | Quy tắc xưng hô giữa từng cặp nhân vật (người nói → người nghe → từ xưng/gọi), theo giai đoạn truyện |
| style_profile | Hồ sơ văn phong của tác phẩm: Hán Việt/thuần Việt, kiểu thoại, kiểu bỏ dấu, dấu câu, danh sách cụm sáo cấm |
| outlines | Dàn ý/volume/chapter plan, revision |
| characters | Nhân vật, vai trò, mô tả, bí danh (có/không dấu, Hán Việt/thuần Việt) |
| chapters | Chương và pointer tới revision hiện tại; `status` (draft/generating/waiting_user/committed), `state_applied` (bool – chỉ số §9 Giai đoạn 4), số âm tiết, `deleted_at` |
| chapter_revisions | Tiptap JSON, plain text projection, nguồn sửa và timestamp |
| story_states | Snapshot `StoryState` sau mỗi chương theo schema §23.1.A |
| facts / hooks | Dữ kiện, móc truyện, nguồn chương, trạng thái; hook có `due_by_chapter`, `payoff_plan`, `priority` |
| chapter_handoffs | Bản giao nối chương: `ending_state` JSON (địa điểm, thời điểm truyện, nhân vật có mặt + trạng thái, hành động dở dang, cảm xúc chủ đạo), `tail_text` (đoạn cuối nguyên văn, cắt theo token), `open_threads`, `next_opening_requirements`, revision nguồn |
| story_events | Sự kiện trong dàn ý: tóm tắt, chương dự kiến, trạng thái planned/done/moved/dropped, phụ thuộc |
| chapter_plans | Kế hoạch chương kèm `input_hash` (state rev + handoff rev + outline rev); retry chỉ dùng lại plan khi hash khớp |
| timeline | Mốc thời gian truyện theo chương, dùng cho kiểm tra xác định |
| context_traces | Ngữ cảnh đã dùng cho từng bước AI: khối, lớp, nguồn, số token, bị nén hay không, prompt version (API `/trace`) |
| author_controls | Book rules, author intent, current focus của tác phẩm, có revision |
| findings | Gộp mọi nhận xét: nguồn (check/validator/seam/review/user), loại (fact/timeline/name/address/seam/pov/hook/length/slop/spelling/register/tone_mark_style/punctuation/craft), mức độ blocker/major/minor (mặc định §24 D7), trích dẫn theo `paragraph_id`, trạng thái open/resolved/dismissed/unavailable |
| chapter_candidates | Bản nháp AI: chương, base revision, job, loại (draft/repair/revise), văn bản theo đoạn, trạng thái streaming/partial/ready/accepted/rejected/superseded, tóm tắt kiểm tra (§23.2) |
| chapter_working_copy | Bản đang sửa của editor (một bản/chương, autosave ghi đè), tách khỏi revision (§23.2) |
| summaries | Tóm tắt phân tầng: chương, arc/quyển, synopsis toàn truyện (§23.3) |
| work_queues / work_locks | Hàng đợi theo truyện, ưu tiên, chế độ auto-write; khóa có lease + heartbeat |
| provider_limits | Giới hạn concurrency/RPM/TPM/retry và trạng thái cooldown theo provider (không chứa ngân sách) |
| usage_records / usage_counters | Một dòng mỗi request AI (token, cache, chi phí, job/step); bộ đếm gộp theo ngày/timezone, truyện và provider. Ngân sách toàn app nằm trong `settings`, ngân sách truyện nằm trong `works` |
| references | Tài liệu tham khảo và đoạn đã trích xuất |
| jobs / job_steps | Tác vụ, checkpoint và usage |
| job_events | Event có sequence để reconnect stream |
| providers / settings | Giao thức, base URL, bật tự lấy danh sách model, ưu tiên context dài, effort mặc định; chỉ lưu reference tới secret |
| provider_models | Danh sách model theo provider: `model_id`, thứ tự (đầu tiên = mặc định), nguồn (discovered/manual), tên hiển thị, `max_input_tokens`, `max_tokens`, effort hỗ trợ, giá/1M token (vào, ra, đọc/ghi cache), vai trò được phép, giới hạn đồng thời riêng, trường do người dùng sửa (không bị ghi đè), lần thấy gần nhất |
| role_models | Model + effort theo vai trò (planner, writer, checker/settle, seam/review, summary), toàn app và ghi đè theo truyện |
| assets | Đường dẫn và checksum file đã nhập/tạo |

Trong MVP, nội dung chương và trạng thái truyện dùng `data/db/app.sqlite3` làm dữ liệu chuẩn. Commit revision mới, state snapshot và cập nhật job trong cùng transaction khi phù hợp. Markdown/TXT/EPUB là dữ liệu xuất. Settings lưu trong DB; API key chỉ nằm trong vault mã hóa hoặc RAM phiên hiện tại.

SQLite dùng WAL, foreign_keys=ON, busy_timeout có giới hạn và synchronous=FULL làm baseline ưu tiên độ bền dữ liệu. Đã kiểm chứng ([sqlite.org/wal.html](https://sqlite.org/wal.html)): ở WAL, FULL fsync mỗi commit; NORMAL nhanh hơn nhưng có thể mất các giao dịch gần nhất khi mất điện (không hỏng DB). Commit chương ít và thưa nên giữ FULL; chỉ cân nhắc NORMAL cho bảng event/log nếu đo thấy cần. Không tắt bảo đảm ghi bền chỉ để tăng benchmark. File `app.sqlite3-wal`/`app.sqlite3-shm` khi xuất hiện là phần hoạt động bình thường, không được xóa thủ công trong khi app chạy.

Điều này tránh giả định rằng ghi một file và commit SQLite là một transaction chung. Với asset: ghi file tạm, finalize bằng rename cùng filesystem, sau đó commit metadata; file mồ côi được dọn sau. Không đánh dấu thành công khi asset chưa thực sự tồn tại.

FTS5 là projection có thể rebuild. Giữ source locations để người dùng kiểm tra dữ kiện. Cấu hình tiếng Việt đã chạy thử trên SQLite 3.51.3:

- Tokenizer `unicode61 remove_diacritics 2`. Giá trị mặc định 1 không tìm được "nguyen" trong "Nguyễn", "oc" trong "Ộc" (chữ mang hai dấu).
- FTS5 **không gập `đ→d`** (U+0111 không có phân rã Unicode). Tầng app chuẩn hóa NFC rồi thay `đ→d`, `Đ→D` cho cột tìm kiếm, áp dụng cho cả nội dung index và câu truy vấn; giữ văn bản gốc có dấu để hiển thị.
- Thêm bảng FTS5 trigram cho tên riêng/chuỗi con khi cần (chuỗi < 3 ký tự không khớp).
- Sắp xếp bằng `bm25()` (giá trị nhỏ hơn là khớp hơn), có trọng số cột.

Đánh giá retrieval với tiếng Việt có dấu/không dấu, tên riêng và truyện nhiều chương. Vector embeddings là mở rộng khi chất lượng lexical retrieval chưa đủ; model embedding local/cloud được cấu hình riêng.

Backup SQLite bằng `VACUUM INTO` ra file tạm (đích phải chưa tồn tại) rồi rename; hoặc backup API với `step(-1)`. Backup API từng bước sẽ khởi động lại nếu có ghi xen giữa, nên khi nhiều truyện đang viết thì `VACUUM INTO` phù hợp hơn ([backup](https://www.sqlite.org/backup.html), [VACUUM](https://www.sqlite.org/lang_vacuum.html)). Không copy tùy tiện file DB đang ghi trong WAL mode. Backup bao gồm assets, schema version và manifest/checksum; vault mã hóa có lựa chọn đưa vào backup, không xuất API key plaintext. Khi app đã đóng hoàn toàn, có thể copy nguyên thư mục data, bao gồm các file WAL còn tồn tại. `backups/` không tự được đóng vào backup tiếp theo để tránh lồng vô hạn; có giới hạn số bản lưu. Nên có một bản sao ngoài data để phục hồi khi mất cả ổ đĩa.

## 6. Quy trình viết AI

### 6.1 Nền truyện (một lần, sửa được)

1. **Brief:** thu yêu cầu về thể loại, nhân vật, bối cảnh, giọng văn, giới hạn và độ dài.
2. **Foundation:** tạo nền truyện, nhân vật, quy tắc; tác giả kiểm tra/chỉnh sửa.
3. **Event outline:** dàn ý tổng chia thành `story_events` có phụ thuộc, phân bổ vào chương dự kiến (theo StoryWriter, [arxiv 2506.16445](https://arxiv.org/abs/2506.16445)). Dàn ý được phép điều chỉnh sau mỗi chương (dàn ý động theo DOME, [arxiv 2412.13575](https://arxiv.org/abs/2412.13575)).
4. **State seed:** snapshot chương 0, hooks ban đầu có `due_by_chapter`.

### 6.2 Pipeline một chương: liền mạch, không đứt quãng

Phân tích InkOS cho thấy ba nguyên nhân gây đứt mạch mà bản Python phải tránh: (a) Writer không nhận văn bản chương trước, chỉ Planner nhận (`utils/planning-materials.ts`, `agents/planner.ts:70-78`); (b) chương vẫn được commit khi state không hợp lệ, nên sự kiện của chương bị mất khỏi state trong khi chương sau vẫn được viết (`pipeline/chapter-truth-validation.ts:99-127`); (c) review chỉ ghi nhận, không kích hoạt sửa.

```text
[Cổng vào] chương N-1 committed && state_applied && work.continuity_status = ok
   │
1. Load    handoff(N-1) + state snapshot(N-1) + story_events của N + hooks đến hạn
2. Plan    chapter_plan(N): mục tiêu, sự kiện bắt buộc, hook phải tiến/trả,
           cảnh mở đầu phải nối từ ending_state(N-1); lưu kèm input_hash
3. Compose context theo lớp (§6.4). BẢO VỆ, không nén:
           plan(N), handoff(N-1), tail_text(N-1)
4. Write   stream bản nháp; Writer NHẬN handoff + đuôi chương trước; lưu partial
5. Check   kiểm tra xác định, không gọi LLM:
           - độ dài trong khoảng mục tiêu
           - tên riêng chỉ thuộc canon/bí danh, hoặc được khai báo là nhân vật mới
           - nhân vật đã chết/vắng mặt không có hành động
           - cụm sáo/cấm (danh sách anti-slop, regex)
           - không lặp nguyên văn đoạn dài của chương trước (n-gram overlap)
6. Settle  state delta (facts, hooks, timeline, vị trí nhân vật) + ending_state(N)
7. Validate (a) schema + ràng buộc xác định trên delta; (b) LLM so state cũ/mới có trích dẫn
8. Seam    đoạn mở chương N có khớp ending_state(N-1)? (địa điểm, thời điểm,
           ai có mặt, cảm xúc, hành động dở dang)
9. Review  findings có bằng chứng, phân loại blocker / major / minor
10. Sửa    nếu có blocker hoặc seam fail: sửa CỤC BỘ đoạn vi phạm, quay lại bước 5;
           tối đa K vòng (mặc định 2) và trần token; hết vòng → waiting_user, KHÔNG commit
11. Commit 1 transaction: chapter_revision + state_snapshot + handoff(N) + summary
           + hooks + timeline + FTS + job result
```

Quy tắc:

- **Không bao giờ commit chương mà thiếu state hợp lệ.** Nếu validator thất bại sau K vòng: chương ở `waiting_user`, truyện chuyển `blocked_needs_resync`; tác giả sửa, chấp nhận kèm ghi chú, hoặc yêu cầu settle lại.
- Lỗi fact/timeline/seam/tên riêng là `blocker`; nhịp, giọng văn là `minor`, không chặn. Lỗi hay gặp nhất trong truyện dài do LLM viết là sự kiện và thời gian, tập trung ở giữa truyện (ConStory-Bench, [arxiv 2603.05890](https://arxiv.org/html/2603.05890v1)).
- Sửa cục bộ thay vì viết lại cả chương (Re3, ConWriter).
- State gồm cả **việc tương lai bắt buộc** (hook đến hạn, sự kiện phải xảy ra), không chỉ những gì đã xảy ra (NstAgent, [arxiv 2609.35759](https://arxiv.org/abs/2609.35759)).
- `tail_text` khoảng 1.000–2.000 token, cắt theo ranh giới đoạn; Planner cũng nhận bản cắt này thay vì toàn văn chương trước (InkOS đưa toàn văn nên chương dài có thể vượt ngân sách và throw).
- Sửa tay chương K nhỏ hơn chương mới nhất → `stale_from(K)`; UI đề xuất settle lại tuần tự K..N từ snapshot K-1 hoặc bỏ qua có xác nhận. Không tự viết lại văn bản các chương sau.

### 6.3 Revise theo yêu cầu tác giả

Tạo candidate dựa trên phạm vi tác giả chọn, so sánh và lưu lịch sử; nếu thay đổi chương mới nhất thì settle lại và cập nhật handoff, nếu là chương cũ thì đánh dấu `stale_from`.

### 6.4 Bố cục prompt để tận dụng cache

```text
[Lớp 1 – toàn app]   system, phương pháp viết, quy tắc tiếng Việt, danh sách cụm cấm
[Lớp 2 – theo truyện] story bible, dàn ý tổng, nhân vật chính, book rules
[Lớp 3 – theo chương] state snapshot, summaries chọn lọc, hooks đến hạn, handoff, tail_text, plan
[Lớp 4]               chỉ dẫn của lượt hiện tại
```

Provider cache theo prefix: Anthropic đọc cache ở mức 0,1× giá input, ghi cache 1,25× (TTL 5 phút) hoặc 2× (TTL 1 giờ) ([docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)); OpenAI cache tự động từ 1.024 token ([docs](https://developers.openai.com/api/docs/guides/prompt-caching)); Gemini có implicit caching ([docs](https://ai.google.dev/gemini-api/docs/caching)). Vì vậy không sửa lớp 1–2 khi một batch đang chạy; thay đổi story bible tạo revision mới và áp từ chương kế tiếp. Batch API (giảm 50%, xong trong tối đa 24 giờ) chỉ dùng cho tác vụ không gấp như review lại hàng loạt, không dùng cho chuỗi chương tuần tự.

### 6.5 Contract chung

Mỗi bước có input/output contract, prompt version, model, source revision, timing và token usage (gồm cache read/write). Độ dài đo bằng **số âm tiết** (§6.6).

### 6.6 Gói ngôn ngữ và yêu cầu tiếng Việt

Pipeline §6.2 không chứa logic riêng của một ngôn ngữ. Mọi phần phụ thuộc ngôn ngữ nằm sau một interface `LanguagePack`, chọn theo `works.language`:

| Thành phần của gói | Vai trò |
|---|---|
| `normalizer` | Chuẩn hóa văn bản khi lưu/tìm/so sánh |
| `length_counter` | Đơn vị độ dài (tiếng Việt: âm tiết; tiếng Anh: từ; tiếng Trung: ký tự) |
| `search_normalizer` | Chuẩn hóa cột tìm kiếm FTS (tiếng Việt: bỏ dấu + `đ→d`) |
| `deterministic_checks` | Kiểm tra xác định riêng của ngôn ngữ (xưng hô, lớp từ, chính tả…) |
| `prompts/`, `methods/` | Prompt và phương pháp sáng tác viết bằng ngôn ngữ đó, không dịch máy |
| `slop_list`, `genre_presets` | Cụm sáo và preset thể loại của ngôn ngữ đó |
| `ui` resource | File i18n của giao diện |

MVP chỉ có gói `vi` và chỉ gói này phải đạt tiêu chí nghiệm thu. Thêm ngôn ngữ = thêm gói + bộ truyện mẫu + bộ đánh giá model, không sửa pipeline. Không port nhánh zh/en của InkOS vào MVP. Phần dưới là đặc tả gói `vi`.

**Chuẩn hóa văn bản** (áp dụng khi lưu, khi tìm kiếm và trước khi so sánh):

- Unicode NFC cho mọi văn bản vào DB; văn bản dán từ nguồn ngoài (Word, web, bảng mã cũ) được chuẩn hóa khi import/paste.
- Kiểu bỏ dấu (`hoà`/`hòa`, `thuý`/`thúy`) theo `style_profile` của tác phẩm; trình kiểm tra cảnh báo khi trộn hai kiểu trong cùng truyện.
- Dấu câu và thoại theo một quy ước của tác phẩm: thoại bằng gạch đầu dòng (`–`/`—`) hoặc ngoặc kép; khoảng trắng quanh dấu câu.

**Đo độ dài:** đếm âm tiết sau NFC, tách theo khoảng trắng, bỏ dấu câu đứng riêng. Mục tiêu chương đặt theo âm tiết (ví dụ 2.500–3.500), UI hiển thị thêm số ký tự. Không dùng cách đếm ký tự tiếng Trung của InkOS.

**Kiểm tra xác định riêng cho tiếng Việt** (bước 5 của §6.2):

| Kiểm tra | Cách làm |
|---|---|
| Xưng hô | Đối chiếu từ xưng/gọi trong thoại với `address_rules` (ví dụ ta–ngươi, huynh–muội, anh–em, con–cha); đổi xưng hô phải có sự kiện trong state (kết nghĩa, thân thiết hơn, trở mặt) |
| Tên riêng | Tên và bí danh theo canon, gồm cả biến thể có/không dấu; cảnh báo khi một nhân vật bị gọi lẫn tên Hán Việt và tên thuần Việt nếu canon không cho phép |
| Lớp từ | Truyện cổ trang/tiên hiệp: cảnh báo từ hiện đại lạc thời (điện thoại, ô tô, "OK"…) theo danh sách của thể loại; truyện hiện đại: cảnh báo lạm dụng Hán Việt nếu `style_profile` yêu cầu |
| Cụm sáo | Danh sách cụm sáo/AI-slop tiếng Việt (ví dụ mở đoạn bằng "Trong khoảnh khắc ấy", lặp "không khỏi", "một cách" dày đặc) do tác giả bổ sung được; quét regex, finding mức `minor`. Không tự kích hoạt vòng sửa; được sửa kèm khi đoạn đó đang được sửa vì lỗi khác, hoặc khi tác giả yêu cầu (§24 D37) |
| Chính tả | Lỗi dấu hỏi/ngã và lỗi gõ Telex sót (`tieengs`, `ddi`) bằng từ điển âm tiết tiếng Việt hợp lệ; chỉ cảnh báo, không tự sửa |

**Prompt và phương pháp:** viết bằng tiếng Việt, ví dụ mẫu tiếng Việt, yêu cầu đầu ra tiếng Việt; schema JSON giữ khóa tiếng Anh cho code nhưng mọi giá trị văn bản là tiếng Việt. 20 nhóm phương pháp (§15.16) được biên soạn lại cho văn học mạng Việt Nam và các thể loại phổ biến: tiên hiệp, kiếm hiệp, huyền huyễn, ngôn tình, đô thị, cung đấu, xuyên không, trinh thám.

**Chọn model:** chất lượng tiếng Việt khác nhau nhiều giữa các model. R2 có bộ đánh giá nhỏ (cùng chương mẫu, cùng bối cảnh) để so model theo: tự nhiên của câu, đúng xưng hô, không lẫn từ Trung/Anh, đúng chính tả. Kết quả lưu để gợi ý model theo vai trò. Số token cho một âm tiết tiếng Việt tùy tokenizer của từng model; đo thực tế để ước tính chi phí, không dùng tỷ lệ của tiếng Anh.

Các vai trò planner/writer/reviewer không phải các dịch vụ riêng. Cấu hình model + effort theo vai trò có từ MVP (§7.1); mặc định mọi vai trò dùng model mặc định cho tới khi người dùng gán khác hoặc bộ đánh giá gợi ý.

Timeout gồm connect, first-token, stream-idle và overall deadline. Retry hữu hạn với backoff/jitter cho lỗi transient; lỗi API key/model không retry tự động. Cancel phải truyền tới HTTP request và ngăn commit candidate sau cancel. Lưu usage thực nhận; không suy diễn token khi provider chưa trả.

Prompt và tài liệu tham khảo là dữ liệu sáng tác. Nội dung import không được quyền tự mở file ngoài phạm vi, chạy shell hoặc thay đổi thiết lập. Tools có phạm vi rõ và output có validation.

## 7. API và UI

API khởi điểm:

```text
GET    /v1/health
GET    /v1/works
POST   /v1/works
GET    /v1/works/{id}
PATCH  /v1/works/{id}
GET    /v1/works/{id}/chapters
GET    /v1/chapters/{id}
PUT    /v1/chapters/{id}              expected_revision bắt buộc
GET    /v1/chapters/{id}/revisions
POST   /v1/jobs                      create foundation/write/review/revise
GET    /v1/jobs/{id}
POST   /v1/jobs/{id}/cancel
POST   /v1/jobs/{id}/resume
GET    /v1/jobs/{id}/events          SSE: bộ lọc theo job của luồng sự kiện chung /v1/events
(nhận candidate dùng POST /v1/candidates/{id}/accept – xem API bổ sung; không có /v1/jobs/{id}/accept)
POST   /v1/works/{id}/autowrite      {target_chapter | count, mode: auto|review_each|review_every_k, priority}
POST   /v1/works/{id}/autowrite/pause | resume | cancel
GET    /v1/works/{id}/continuity     continuity_status, handoff mới nhất, findings mở
POST   /v1/works/{id}/resync         settle lại từ chương K
GET    /v1/queues                   mọi truyện: đang chạy, chờ slot, bị chặn, bước pipeline, chi phí
GET    /v1/providers
POST   /v1/providers/test
POST   /v1/providers/{id}/discover   lấy {base_url}/v1/models ngay, trả số model mới/biến mất và lỗi cụ thể
GET    /v1/providers/{id}/models     danh sách hiệu lực (ghi đè hoặc tự lấy) + model khả dụng khác
PUT    /v1/providers/{id}/models     thứ tự, thêm/xóa, sửa metadata từng model
GET    /v1/settings/roles            model + effort theo vai trò
PUT    /v1/settings/roles
GET    /v1/providers/{id}/usage      RPM/TPM/chi phí hôm nay, cache hit
POST   /v1/imports
POST   /v1/exports
POST   /v1/backups
```

API bổ sung cho các màn hình đã thiết kế (§23):

```text
GET    /v1/events?since=<seq>&works=  SSE toàn cục cho Phòng viết/header (§23.1.C)
POST   /v1/works/{id}/chapters        tạo chương; DELETE /v1/chapters/{id}; POST /v1/works/{id}/chapters/reorder
GET    /v1/chapters/{id}/working-copy  PUT kèm base revision (autosave, §23.2)
POST   /v1/chapters/{id}/snapshot     tạo revision thủ công (Ctrl+S)
GET    /v1/chapters/{id}/revisions/{a}/diff/{b}
POST   /v1/chapters/{id}/revisions/{rev}/restore
GET    /v1/chapters/{id}/candidates   POST /v1/candidates/{id}/accept {paragraph_ids?} | reject
GET    /v1/chapters/{id}/trace        context trace: đã dùng ngữ cảnh nào, prompt version, model, usage
GET    /v1/chapters/{id}/handoff      PUT để tác giả sửa ending_state trước khi viết chương sau
GET    /v1/works/{id}/state?chapter=N StoryState sau chương N
CRUD   /v1/works/{id}/characters | facts | hooks | story-events | timeline | address-rules | style-profile
GET    /v1/works/{id}/findings?status=open   POST /v1/findings/{id}/resolve | dismiss
GET    /v1/works/{id}/search?q=       FTS có nguồn chương/đoạn
POST   /v1/works/{id}/autowrite/estimate   ước tính token/chi phí/thời gian
POST   /v1/vault/unlock | lock        GET /v1/vault/status
GET    /v1/storage                    dung lượng theo loại; POST /v1/storage/cleanup
```

UI chính:

- Thư viện: tác phẩm, tìm kiếm, trạng thái, mở gần đây.
- Phòng viết: mọi truyện đang auto-write, chương hiện tại, bước pipeline, trạng thái liền mạch, chi phí; tạm dừng/tiếp tục/ưu tiên từng truyện. Mở một truyện để đọc/sửa trong khi các truyện khác vẫn chạy.
- Workspace ba vùng: chương/dàn ý bên trái, editor giữa, AI/nhân vật/bộ nhớ bên phải.
- AI panel: yêu cầu, context đã chọn, tiến độ theo bước, dừng/resume, usage và candidate.
- Review panel: vấn đề, dẫn chứng, sửa có phạm vi.
- History: diff/restore revision; không xóa lịch sử để sửa bản chính.
- Cài đặt Mô hình AI (§7.1): kết nối, tự lấy danh sách model, danh sách model có thứ tự, effort, vai trò, đồng thời và ngân sách.
- Backup/import/export và quản lý lưu trữ.

Bố cục chi tiết, wireframe và thư viện React: [ui-design.vi.md](./ui-design.vi.md).

Mất kết nối UI không được đồng nghĩa hủy tác vụ backend. FE reconnect từ sequence; event không bị render lặp. Giới hạn history event và bảo toàn thông tin cần phục hồi.

### 7.1 Cấu hình model AI

Theo dạng trang Models của Claude: tự lấy danh sách model, danh sách ghi đè có thứ tự, ưu tiên context dài, effort mặc định. Wireframe tại [ui-design.vi.md §5.6](./ui-design.vi.md).

**Lấy danh sách model** (`be/infrastructure/ai/discovery.py`):

1. Chạy nền sau khi backend sẵn sàng (không chặn khởi động) nếu "Tự lấy danh sách model" bật; hoặc khi người dùng bấm "Kiểm tra lấy danh sách". Nếu tắt và danh sách thủ công đã có model thì bỏ qua.
2. Gọi `GET {base_url}/v1/models` qua adapter theo giao thức, timeout ngắn (khoảng 10 giây):
   - **Anthropic**: header `x-api-key` + `anthropic-version`; phân trang bằng `has_more` / `after_id` (`limit` tối đa 1.000). Mỗi model có `id`, `display_name`, `max_input_tokens`, `max_tokens`, `capabilities` (gồm `effort.{low,medium,high,xhigh,max}.supported`, `thinking`, `structured_outputs`, `batch`) ([docs](https://platform.claude.com/docs/en/api/models/list)).
   - **OpenAI-compatible** (gồm gateway tự dựng): `Authorization: Bearer`; đọc `data[].id`. Định dạng chuẩn thường không có context window/effort, nên các trường đó để trống cho người dùng điền; nếu gateway trả thêm trường mở rộng thì đọc khi có.
   - **Ollama/LM Studio**: endpoint OpenAI-compatible local, không cần key.
3. Chuẩn hóa thành `ProviderModel`; merge vào `provider_models`: thêm model mới, cập nhật lần thấy gần nhất, **không ghi đè trường người dùng đã sửa**, đánh dấu ⚠ model không còn trên server (không tự xóa).
4. Danh sách hiệu lực: nếu danh sách ghi đè có mục → dùng đúng danh sách đó theo thứ tự, mục đầu là mặc định; nếu rỗng → dùng danh sách tự lấy.
5. Lỗi (401, 404, timeout, JSON sai) lưu kèm thời điểm, hiển thị trên nút kiểm tra; không làm mất danh sách đã có.

**Ưu tiên context dài:** chỉ áp dụng khi người dùng chưa chọn model; chọn biến thể context 1M của model mặc định nếu provider có (biến thể là model ID riêng hoặc tham số/beta tùy provider, khai báo trong metadata model). Mặc định tắt vì viết chương thường không cần và context dài tốn chi phí hơn. Composer luôn lấy ngân sách context từ `max_input_tokens` của model thực dùng.

**Effort:**

- Mức: `low`, `medium`, `high`, `xhigh`, `max`. Trống = không gửi tham số, dùng mặc định của provider (Anthropic: `high`, riêng Opus 5.5 là `medium`) ([docs](https://platform.claude.com/docs/en/build-with-claude/effort)).
- Anthropic gửi `output_config.effort`. OpenAI-compatible: adapter ánh xạ sang tham số reasoning của endpoint nếu model khai báo hỗ trợ; không hỗ trợ thì bỏ tham số và ghi chú trong trace. Chỉ gửi mức nằm trong danh sách effort hỗ trợ của model.
- Thứ tự áp dụng: vai trò trong truyện → vai trò toàn app → effort mặc định → mặc định provider.
- **Giữ effort cố định trong một lượt viết**: đổi effort top-level giữa các request làm mất prompt cache, nên job ghim model + effort lúc bắt đầu; thay đổi cài đặt áp từ chương kế tiếp.
- Effort cao tăng token đầu ra (cả phần suy nghĩ), nên `max_tokens` của vai trò Viết đặt đủ lớn, và ngân sách/ước tính chi phí tính theo usage thực nhận.

**Vai trò gợi ý ban đầu** (điều chỉnh sau bộ đánh giá model tiếng Việt ở R2): Lập kế hoạch và Viết chương dùng model mạnh nhất, effort `high`; Kiểm tra/Settle và Mối nối/Review dùng model cân bằng, effort `medium`; Tóm tắt dùng model rẻ, effort `low`.

## 8. Cấu trúc repo đề xuất

```text
WriteStoryApp/
  fe/                        React/TypeScript/Vite, nhóm theo tính năng
    src/
      app/
      features/
      shared/
  be/                        Package Python writestory-be, sở hữu API và dữ liệu
    pyproject.toml
    src/writestory_be/
      main.py                FastAPI app factory
      bootstrap/
      api/
      modules/               Domain/use case/API theo nghiệp vụ
      jobs/
      infrastructure/        SQLite, files, vault và adapters cho AI ports
      core/
    migrations/
    tests/
  ai/                        Package Python writestory-ai, không import BE
    pyproject.toml
    src/writestory_ai/
      contracts/
      ports/
      providers/
      context/
      prompts/
      methods/
      workflows/
      evaluators/
      policies/
    tests/
  desktop/
    src-tauri/               Rust/Tauri, lifecycle và data-root
  contracts/                 OpenAPI snapshot; generated TS nằm tại FE
  tools/                     Dev, schema generation, packaging
  tests/                     Tích hợp xuyên package và desktop smoke tests
  docs/
    implementation-plan.vi.md
    folder-architecture.vi.md
  data/                      Runtime local, loại khỏi Git
  pyproject.toml             uv workspace: be và ai
  uv.lock                    Một lockfile Python chung
  pnpm-workspace.yaml        JS workspace: fe và desktop
  pnpm-lock.yaml
```

Backend sinh OpenAPI; frontend sinh types tại `fe/src/shared/api/generated/` để tránh khai báo hai bản lệch nhau. Routes chỉ điều phối; domain/workflow không phụ thuộc React/Tauri. BE import AI như một dependency Python trong cùng backend process, không thêm AI HTTP service. AI trả candidate/proposed state delta; BE sở hữu DB, transaction, canonical revision và job lifecycle. Nhờ vậy có thể chuyển shell hoặc thêm web/cloud sau này.

Đây là cây đích, chưa tạo source skeleton. Quy tắc import, cấu trúc từng tầng, dependency/lockfile, mapping module và nguồn đối chiếu nằm trong [folder-architecture.vi.md](./folder-architecture.vi.md). Cấu trúc này thay thế đề xuất cũ `apps/desktop` + `backend/app/ai`.

## 9. Lộ trình và điều kiện hoàn thành

Ước lượng cơ sở: một lập trình viên có kinh nghiệm làm tập trung, khoảng 10–13 tuần cho MVP đóng gói và pilot. Điều chỉnh sau spike, mức hoàn thiện UI và chất lượng AI thực tế. Chất lượng văn chương cần tác giả kiểm chứng, không chỉ unit test.

### Giai đoạn 0 — Spike desktop/packaging, tuần 1

- Dựng React/Tauri và backend Python tối thiểu.
- Bundle Python, startup readiness, token, cổng động, shutdown.
- Thử Tiptap với gõ tiếng Việt: Unikey và EVKey trên Windows (bật/tắt "sửa lỗi gợi ý"), Telex/VNI có sẵn của macOS; gõ trong đoạn có bold/italic, ở đầu/cuối mark; paste văn bản dài; undo/redo. Không tìm thấy báo cáo lỗi riêng cho Telex/VNI, nhưng có nhiều lỗi composition tương tự với IME Nhật/Hàn trên WKWebView ([prosemirror#1190](https://github.com/ProseMirror/prosemirror/issues/1190)) và lỗi nhân đôi ký tự ([tiptap#2780](https://github.com/ueberdosis/tiptap/issues/2780)).
- Mock stream AI và chạy app trên Windows x64/macOS Apple Silicon; thử 3 truyện auto-write song song với mock provider.
- Kiểm chứng vault, quyền ghi data-root portable, luồng chọn data-root macOS khi bị App Translocation, PyInstaller onedir qua `bundle.resources`, tắt backend khi quit (không để tiến trình mồ côi).

Hoàn thành khi máy sạch không có Python/Node mở được app, stream hoạt động, đóng app không để lại backend, editor gõ tiếng Việt ổn định trên cả WebView2 và WKWebView. Quyết định giữ Tauri hay đổi shell tại đây; lỗi IME không khắc phục được trên WKWebView là lý do cụ thể để chuyển sang Electron.

### Giai đoạn 1 — Nền dữ liệu và app shell, tuần 2–3

- SQLite schema/migrations, settings/provider secret references.
- Library/workspace, CRUD tác phẩm/nhân vật/dàn ý/chương.
- Local API client và thống nhất error/protocol versions.
- Backup/restore cơ bản và app single-instance.

Hoàn thành khi dữ liệu tồn tại sau restart, migration chạy đúng và đọc/ghi không cần internet.

### Giai đoạn 2 — Editor và version, tuần 4

- Tiptap JSON và plain-text projection, autosave.
- Revision, restore/diff cơ bản, expected_revision.
- Search, chapter navigation và xử lý save error.

Hoàn thành khi crash không làm mất bản đã lưu, AI và người dùng không ghi đè lẫn nhau, văn bản Unicode xuất/nhập lại giữ đúng nội dung.

### Giai đoạn 3 — Async jobs và AI adapter, tuần 5–6

- Một provider cloud trước; thêm OpenAI-compatible local endpoint để test lựa chọn offline.
- Supervisor, job persistence, events, checkpoints, cancellation.
- Scheduler đa truyện: hàng đợi theo truyện, xoay vòng công bằng, khóa có lease xếp hàng, writer queue SQLite.
- Limiter theo provider (concurrency, RPM/TPM, `Retry-After`), timeout, bounded retry, usage và ngân sách.
- FE progress/reconnect; mock lỗi/rate limit/disconnect.

Hoàn thành khi tác vụ không block editor, cancel ngăn commit, app restart hiển thị interrupted job và resume từ checkpoint hợp lệ; 5 truyện mock chạy song song đều tiến, 429 giả lập được chờ đúng `Retry-After`. Bản không có internet vẫn chỉnh sửa được dữ liệu local.

### Giai đoạn 4 — Quy trình viết truyện, tuần 7–9

- Brief/foundation, event outline, planner, FTS retrieval, context budget và prompt theo lớp.
- Writer nhận handoff + tail_text; kiểm tra xác định; settle; validator; seam check; review; vòng sửa cục bộ có giới hạn; transaction commit (§6.2).
- Cổng chặn `blocked_needs_resync`, `stale_from(K)` và resync tuần tự.
- Auto-write ba chế độ `auto` / `review_each` / `review_every_k`; revise có phạm vi.
- Bộ truyện mẫu tiếng Việt (ít nhất một tiên hiệp/kiếm hiệp, một ngôn tình hoặc đô thị) để kiểm tra continuity, xưng hô, tên riêng, lớp từ và độ dài.
- Kiểm tra xác định tiếng Việt (§6.6) và bộ so sánh model theo chất lượng tiếng Việt.

Hoàn thành khi **3 truyện mẫu chạy song song, mỗi truyện 20 chương**, đạt các chỉ số:

- 0 chương committed có `state_applied=false`.
- Seam check pass ≥ 95% (sau tối đa 2 vòng sửa).
- 0 tên nhân vật ngoài canon chưa được khai báo.
- 0 lỗi xưng hô sai `address_rules` mà không có sự kiện đổi xưng hô; không trộn hai kiểu bỏ dấu trong một truyện.
- 100% hook quá `due_by_chapter` được báo cáo.
- Tỷ lệ n-gram trùng giữa hai chương liền kề dưới ngưỡng cấu hình.
- Người đọc chấm từng chương và cả truyện (theo kiểu [EQ-Bench Longform](https://github.com/EQ-bench/longform-writing-bench)); tác giả kiểm tra được nguồn context, review và history.

Tác vụ thất bại không làm trạng thái truyện tiến trước bản thảo.

### Giai đoạn 5 — Export, hiệu năng và installer, tuần 10–11

- TXT/Markdown trước, EPUB sau khi metadata/Unicode ổn định.
- Test corpus lớn, startup/RAM, stream batching, backup.
- Installer Windows và macOS; ký/notarize cho phát hành công khai.
- Crash/recovery, upgrade migration và kiểm tra backend frozen process pool.

Hoàn thành khi cài/nâng cấp không làm mất dữ liệu, chạy máy sạch và vượt các tiêu chí hiệu năng đã điều chỉnh theo số đo.

### Giai đoạn 6 — Pilot, tuần 12–13 khi cần

- Dùng viết truyện thật, sửa các vấn đề workflow/UX/chất lượng.
- Hoàn thiện hướng dẫn cấu hình cloud/local AI và backup.
- Chốt release, changelog và update policy.

Hoàn thành khi người dùng tạo tác phẩm → viết/sửa chương → đóng/mở → phục hồi → xuất tác phẩm mà không cần terminal.

## 10. Đóng gói Windows và macOS

- FE build static; Python bundle binary và runtime/dependency đi kèm; Rust launch bằng đường dẫn tài nguyên tuyệt đối.
- Với PyInstaller onedir, phải bundle đủ thư mục runtime, giữ layout cần thiết và kiểm tra quyền execute. PoC xác định resource mapping thực tế của Tauri trên từng OS.
- Windows x64 và macOS arm64 ưu tiên trước. macOS Intel và Windows ARM thêm theo nhu cầu, có build/test riêng; không giả định cùng binary chạy mọi architecture.
- Windows xuất installer NSIS hoặc MSI sau spike. WebView2 có các chế độ `downloadBootstrapper` (mặc định, cần mạng), `embedBootstrapper` (~1,8 MB), `offlineInstaller` (~127 MB), `fixedRuntime` (~180 MB), `skip` ([Tauri](https://v2.tauri.app/distribute/windows-installer/)). Bản portable dùng được offline chọn `offlineInstaller` hoặc `fixedRuntime`; xác nhận tên khóa cấu hình trong schema khi dựng.
- macOS: Tauri ký binary chính và `externalBin` nhưng **không ký** các `.dylib/.so` trong `_internal/` của PyInstaller onedir đặt ở resources, khiến notarize lỗi ([tauri#8075](https://github.com/tauri-apps/tauri/issues/8075), [tauri#11992](https://github.com/tauri-apps/tauri/issues/11992)). CI chạy `codesign --options runtime --timestamp` từng file bằng cùng Developer ID trước khi bundle. WKWebView gắn với phiên bản macOS, nên chốt phiên bản macOS tối thiểu và test editor trên bản thấp nhất.
- macOS xuất .app/.dmg, kiểm tra phiên bản macOS tối thiểu theo Tauri/webview và Python dependencies đã chọn.
- Build macOS trên runner/macOS, Windows trên Windows; không hứa cross-compile toàn bộ PyInstaller từ một máy.
- Phát hành công khai: chuẩn bị chứng chỉ Windows; Apple Developer ID, ký các binary/framework bên trong và notarization. Ký thành công là một phần của CI release, không chỉ ký vỏ .app.
- Auto-update chỉ thêm sau khi migration/backup tin cậy; gói cập nhật phải được xác minh chữ ký. Rollback DB schema cần chính sách riêng.
- Portable build cập nhật binary/resources mà giữ nguyên data; không đóng gói data mẫu đè lên dữ liệu thật. Installer nếu bổ sung phải hỗ trợ data-root đã chọn. Bản thảo và vault không bị xóa khi nâng cấp. Uninstall có lựa chọn rõ nếu muốn xóa user data.

## 11. Kiểm thử cần thiết

| Phạm vi | Kịch bản quan trọng |
|---|---|
| Domain | Kiểm tra schema, state delta, revision conflict và per-work ordering |
| AI contract | Mock provider thiếu output, stream đứt, sai JSON, 429/401, deadline |
| Persistence | Transaction rollback, migration, FTS rebuild, backup/restore |
| Job recovery | Kill process ở mỗi stage, partial draft, cancel race và resume |
| FE | Autosave, reconnect stream, event trùng, nhận candidate và sửa song song |
| Desktop | Startup token, cổng xung đột, single-instance, shutdown, data path |
| Packaging | Máy không có Python/Node, vault, signed app, upgrade, data portable, quyền ghi và Unicode path |
| Performance | Corpus lớn, RAM, cold startup, token batching và CPU parsing |

Playwright có thể kiểm tra FE chạy trong browser với mock backend. Nó không tự xác nhận mọi hành vi native Tauri trên macOS. CI desktop dùng công cụ driver phù hợp nền tảng và smoke/manual test cho phần native chưa có automation ổn định.

## 12. Cách sử dụng khung InkOS

Tham khảo các ý tưởng: tách UI/core, vai trò planner/writer/reviewer, quản lý canon/hook, task-relevant retrieval, input/output contracts, review có bằng chứng, lưu revision và checkpoint.

Không bê nguyên trạng filesystem/API TypeScript sang Python. Chuyển từng capability thành use case Python với contract và test tương ứng. Ưu tiên vertical slice viết một chương hoàn chỉnh trước khi mở rộng hết các chức năng InkOS.

InkOS có giấy phép AGPL-3.0-only. Nếu sao chép/chuyển thể mã nguồn hoặc nội dung Skill/prompt được bảo hộ từ dự án, giữ attribution và thực hiện nghĩa vụ giấy phép phù hợp. Nếu dự kiến phân phối ứng dụng đóng nguồn, chốt chiến lược giấy phép trước khi tái sử dụng code; tham khảo kiến trúc và tự viết vẫn cần phân biệt với copy/port trực tiếp.

## 13. Quyết định chốt và việc làm đầu tiên

1. Chốt mô hình local cá nhân, React FE, Python FastAPI BE/AI, Tauri desktop, SQLite tại data/db/app.sqlite3 và data-root portable.
2. Làm spike đóng gói và editor trên Windows/macOS trước khi triển khai pipeline lớn.
3. Xây vertical slice: tạo tác phẩm → lưu chương → AI stream candidate → nhận bản mới → mở lại.
4. Thêm checkpoint/continuity/review, sau đó export và tối ưu theo đo đạc.
5. Chỉ mở rộng cloud sync, account, Redis hoặc distributed workers khi có yêu cầu sản phẩm tương ứng.

Các lựa chọn còn cần chốt trong triển khai: provider/model dùng thử, máy/OS hỗ trợ tối thiểu, nhu cầu macOS Intel, tên app/app-id và khả năng ký installer. Những lựa chọn này không ngăn bắt đầu spike hoặc thiết kế domain.

## 14. Phạm vi rà soát nguồn và mức bằng chứng

Nguồn đọc: `E:\Inke\inkos`, manifest phiên bản 2.0.0, Git HEAD `8fc2ae57080b9821257dee3e37cc677e2b6f389a`. Đây là phân tích tĩnh của README, entrypoint, API, UI route, capability registry, workflow, schema, Skill và các kiểm thử liên quan; không phải xác nhận chạy thành công mọi chức năng hoặc mọi nhà cung cấp.

Chỉ mục tự trích xuất trong `docs/inkos-source-inventory.json` chứa đường dẫn và dòng đăng ký API/CLI để đối chiếu khi triển khai:

| Bề mặt | Số lượng trong nguồn | Cách hiểu |
|---|---:|---|
| API route đăng ký trực tiếp | 120 | Không đồng nghĩa 120 chức năng độc lập; nhiều route cùng một use case |
| Static route | 2 | Phục vụ assets và SPA fallback |
| Module command CLI | 27 | Module có thể chứa nhiều subcommand |
| Tên route UI | 25 | Bao gồm alias và các view của cùng một tác phẩm |
| Skill tích hợp | 20 | Là tài liệu phương pháp, không phải 20 service |
| File module endpoint | 44 | Có file tồn tại nhưng chưa đăng ký trong provider registry |
| Entry trong ALL_PROVIDERS | 39 | Metadata/adapter được đăng ký; cần test thực tế riêng |

SKILL.md, prompt và tài liệu của Inke được đọc như dữ liệu mô tả hệ thống nguồn. Các hướng dẫn bên trong không thay thế yêu cầu đã chốt của người dùng: React FE, Python BE/AI, desktop Win/Mac, dữ liệu tập trung trong data.

### 14.1 Bản đồ nguồn dùng trong ma trận tính năng

Mã nguồn trong các bảng dưới đây dùng nhóm Sxx để tránh lặp đường dẫn dài. Mọi đường dẫn tính từ `E:\Inke\inkos`.

| Mã | Nguồn chính |
|---|---|
| S01 | `packages/core/src/harness/contracts.ts`, `builtin-profiles.ts`, `tools/work-creation.ts`, `work-store.ts` |
| S02 | `packages/core/src/harness/production-capabilities.ts`, `runtime.ts`, `explicit-action.ts`, `episode-store.ts` |
| S03 | `packages/core/src/agent/agent-session.ts`, `turn-completion.ts`; Studio `api/chat-request-store.ts`, `api/task-store.ts`, `shared/session-request.ts` |
| S04 | `packages/core/src/pipeline/runner.ts`, `chapter-review.ts`, `chapter-truth-validation.ts`, `chapter-state-recovery.ts`, `chapter-persistence.ts` |
| S05 | `packages/core/src/models/runtime-state.ts`, `models/input-governance.ts`, `state/runtime-state-store.ts`, `state/state-projections.ts`, `utils/governed-context.ts`, `utils/memory-retrieval.ts` |
| S06 | `packages/core/src/interaction/edit-controller.ts`, `harness/tools/longform-edits.ts`, `state/chapter-workspace.ts`, `utils/text-range-edits.ts` |
| S07 | `packages/core/src/materials/ingest.ts`, `materials/retrieve.ts`, `references/book-references.ts`, `retrieval/local-search.ts` |
| S08 | `packages/core/src/pipeline/short-fiction-runner.ts`, `short-production-state.ts`, `agents/short-fiction.ts`, `harness/tools/short-production.ts` |
| S09 | `packages/core/src/agents/fanfic-canon-importer.ts`, `agents/import-context.ts`, `utils/chapter-splitter.ts`; pipeline runner import/initFanfic/initSpinoff/initImitation |
| S10 | `packages/core/src/pipeline/script-storyboard-runner.ts`, `agents/script-storyboard.ts` |
| S11 | `packages/core/src/interactive-film/graph-schema.ts`, `delta.ts`, `validation.ts`, `path-analysis.ts`, `evaluator.ts`, `delivery-requirements.ts` |
| S12 | `packages/core/src/agent/film-authoring-tools.ts`; `interactive-film/export-html.ts`, `export-ink.ts`, `node-image.ts`; `harness/tools/film-delivery.ts` |
| S13 | `packages/core/src/play/play-runner.ts`, `play-db.ts`, `play-store.ts`, `play-image.ts`; `harness/tools/play-state.ts`, `play-image.ts` |
| S14 | `packages/core/src/translation/source.ts`, `runner.ts`, `revision.ts`, `export.ts`, `types.ts`; `harness/tools/translation.ts` |
| S15 | `packages/core/src/llm/provider.ts`, `service-resolver.ts`, `providers/index.ts`, `cover-providers.ts`, `utils/effective-llm-config.ts` |
| S16 | `packages/core/src/skills/builtin-loader.ts`, `external-loader.ts`, `activations.ts`; `packages/core/skills/*/SKILL.md` |
| S17 | `packages/core/src/forecast/runner.ts`, `schema.ts`, `context-builder.ts`; `agent/forecast-tools.ts` |
| S18 | `packages/core/src/pipeline/scheduler.ts`; `agents/radar.ts`, `researcher.ts`; `utils/web-search.ts`, `utils/analytics.ts`; `notify/*` |
| S19 | `packages/core/src/agents/detector.ts`, `pipeline/detection-runner.ts`, `models/project.ts` |
| S20 | `packages/core/src/harness/artifact-revisions.ts`, `source-sync.ts`, `artifact-edit-policy.ts`, `artifact-validation.ts`, `tools/artifact-methods.ts`, `tools/work-artifacts.ts` |
| S21 | `packages/studio/src/api/server.ts`, `hooks/use-hash-route.ts`, `pages/*`, `components/chat/*` |
| S22 | `packages/cli/src/program.ts`, `commands/*`, `book-backup.ts`, `tui/*`; `README.en.md` |

### 14.2 Những khác biệt nguồn phải giữ rõ trong kế hoạch

- README ghi 19 Skill; cây nguồn hiện có 20 thư mục Skill.
- README liệt kê `genre list/show/copy/create`; chương trình CLI hiện không đăng ký command genre. Genre/platform hiện là metadata chuỗi. CRUD bộ preset thể loại sẽ là phần bổ sung của WriteStoryApp, không ghi là CLI nguồn đã có.
- README liệt kê `style analyze`; `commands/style.ts` hiện đăng ký import. Phân tích style có API Studio `/api/v1/style/analyze` và UI, nên chức năng phân tích tồn tại nhưng bề mặt CLI khác README.
- Rewrite CLI lịch sử và endpoint Studio rewrite không hoàn toàn giống nhau. Studio hiện gọi revision mode rework; phải thiết kế lại hành vi tác động chương sau một cách rõ ràng.
- Chỉnh một đoạn chính xác đã có trong code. Tính năng can thiệp một phần chương và tự cascade toàn bộ chương sau vẫn xuất hiện ở roadmap chưa hoàn tất; không coi hai việc này giống nhau.
- Scheduler nguồn chuyển một vài dạng cron thành interval; không phải bộ máy cron đầy đủ. Daily counter nguồn nằm trong memory và dùng ngày UTC. Bản Python sẽ persist quota và dùng timezone cấu hình của app.
- PDF nhập cho dịch thuật hiện cần text layer; PDF scan cần OCR chưa được hỗ trợ. OCR là mở rộng, không được đánh dấu đã có.
- Skill loader hỗ trợ references tĩnh; import Skill không đồng nghĩa plugin thực thi script. Custom agent plugin và export theo nền tảng còn trong roadmap nguồn.
- Các schema viết truyện/UI nguồn chủ yếu zh/en; dịch thuật dùng source/target language dạng chuỗi. WriteStoryApp dùng kiến trúc gói ngôn ngữ (§6.6) và **làm tiếng Việt trước**; nhánh zh/en của InkOS không được port vào MVP, ngôn ngữ khác thêm sau bằng gói riêng.

## 15. Ma trận toàn bộ nhóm tính năng đưa vào dự án

Mã giai đoạn: R0 spike; R1 nền tảng; R2 viết truyện dài/MVP; R3 truyện ngắn và phái sinh; R4 dịch/nghiên cứu/hình ảnh; R5 kịch bản/storyboard; R6 tương tác; R7 hoàn thiện các kênh và tích hợp. Chi tiết thời lượng ở phần 20.

Các dòng dưới đây là tính năng có bề mặt/schema/workflow trong nguồn. Hành vi mới của WriteStoryApp được ghi riêng trong mô tả hoặc phần 19. Mỗi tính năng phải có ticket và acceptance test trước khi chuyển sang hoàn thành.

### 15.1 Thư viện Work, tác phẩm và artifact

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| WRK01 | Thư viện thống nhất cho truyện dài/ngắn, script, storyboard, film, world, translation và visual asset | S01,S21 | R1–R6 |
| WRK02 | Tạo Work từ Profile, lưu brief, ngôn ngữ (MVP: `vi`), thể loại, style profile và metadata | S01,S02 | R1 |
| WRK03 | Thiết lập truyện: tiêu đề, thể loại, nền tảng, số chương, độ dài, trạng thái | S04,S21,S22 | R1 |
| WRK04 | Work Inspector: artifact, bản candidate/current/superseded, checksum và revision parent | S01,S20,S21 | R1–R2 |
| WRK05 | Xem và nhận một revision cũ/candidate làm bản hiện tại | S20,S21 | R2 |
| WRK06 | Lineage: tác phẩm phái sinh tham chiếu đúng Work/artifact/revision nguồn | S01,S09,S20 | R3 |
| WRK07 | Profile tùy chỉnh: capability, Skill, schema artifact, policy và production options | S01,S02,S21 | R3 |
| WRK08 | Episode/event history: thao tác nào tạo kết quả nào, trạng thái và lỗi | S02,S21 | R1–R2 |
| WRK09 | Xóa tác phẩm và backup/restore toàn bộ tác phẩm, backup trước restore | S21,S22 | R2 |
| WRK10 | Migration dữ liệu cũ: preview rồi apply, giữ dữ liệu gốc/draft chưa sẵn sàng | S22, harness legacy-migration | R7 |

### 15.2 Chat, phiên làm việc và action engine

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| CHT01 | Chat tự nhiên để thảo luận, đọc dữ liệu hoặc gọi action | S02,S03,S21 | R2 |
| CHT02 | Tạo/đổi tên/xóa phiên; lưu transcript; mở lại theo Work | S03,S21 | R1–R2 |
| CHT03 | Phiên chưa gắn tác phẩm chuyển thành phiên gắn Work vừa tạo | S03,S01 | R2 |
| CHT04 | Chọn model theo phiên, override routing và depth/light-normal-deep khi được hỗ trợ | S03,S15,S22 | R2,R7 |
| CHT05 | Nhận nguồn/attachment và pin revision nguồn cho các action phái sinh | S03,S09,S20,S21 | R3 |
| CHT06 | Đề xuất action có tham số; confirm/cancel theo Profile và mức rủi ro | S02,S03 | R2 |
| CHT07 | Stream câu trả lời, tool progress, timeline và log; UI tùy chọn mở/đóng chi tiết | S03,S21 | R2 |
| CHT08 | Abort phiên/tác vụ; phục hồi background task và retry gắn đúng request/baseline | S03,S21 | R2 |
| CHT09 | Chống submit trùng/đồng thời cùng phiên, giữ identity/idempotency | S03,S21 | R2 |
| CHT10 | Completion có trạng thái answered/delivered/needs_input/blocked, dựa artifact receipt | S03,S20 | R2 |
| CHT11 | Chat vẫn hỏi được tiến độ khi task sản xuất đang chạy; ngăn tạo job trùng | S03,S21 | R2 |

### 15.3 Truyện dài và điều khiển sáng tác

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| LNG01 | Tạo nền truyện từ ý tưởng/brief hoặc draft hiện có | S04 | R2 |
| LNG02 | Story frame, volume map, role cards và book rules có cấu trúc | S04,S05 | R2 |
| LNG03 | Author intent dài hạn và current focus cho vài chương tới | S04,S05 | R2 |
| LNG04 | Revise/recover foundation chưa hoàn tất; giữ draft lỗi để tiếp tục | S04 | R2 |
| LNG05 | Planner tạo chapter intent, yêu cầu giữ/tránh và xung đột cần giải quyết | S04,S05 | R2 |
| LNG06 | Composer chọn working set, ngân sách context, rule stack và bảo vệ nguồn quan trọng | S04,S05 | R2 |
| LNG07 | Viết chương kế tiếp bằng pipeline thống nhất | S04 | R2 |
| LNG08 | Viết N chương hoặc viết tới số chương mục tiêu; thực hiện tuần tự và công bố mỗi chương đã lưu | S04,S22 | R2 |
| LNG09 | Brief riêng từng chương và one-off instruction cho write/revise | S04,S21,S22 | R2 |
| LNG10 | Length target/range theo đơn vị của gói ngôn ngữ (tiếng Việt: âm tiết), telemetry; không cắt văn bản tùy tiện | S04, models/length-governance | R2 |
| LNG11 | Review continuity/craft dựa canon, intent, plan và bằng chứng | S04,S05 | R2 |
| LNG12 | Observer/settlement: trích xuất thay đổi nhân vật, thời gian, địa điểm, quan hệ, kiến thức và hooks | S04,S05 | R2 |
| LNG13 | Validate/reconcile state delta, snapshot và commit chương/trạng thái | S04,S05 | R2 |
| LNG14 | Context/intent/trace cho từng chương để kiểm tra vì sao AI dùng dữ kiện đó | S04,S05,S21 | R2 |
| LNG15 | Narrative forecast: nhiều hướng tương lai, comparison, fingerprint/stale và chọn candidate plan | S17 | R3 |

### 15.4 Sửa, lịch sử và đồng bộ lại truyện

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| EDT01 | Đọc/chỉnh/lưu chương thủ công; lưu phiên bản nguồn manual | S06,S21 | R1–R2 |
| EDT02 | Revise mode spot-fix, polish, rewrite, rework, anti-detect; phương pháp de-slop theo ngữ nghĩa | S04,S16,S22 | R2–R3 |
| EDT03 | Sửa đoạn chính xác hoặc range; giữ nguyên văn bản ngoài phạm vi | S06,S20 | R2 |
| EDT04 | Thay toàn chương theo văn bản tác giả cung cấp | S06,S21 | R2 |
| EDT05 | Đổi tên entity xuyên dữ liệu/chương hiện hành; không sửa frozen history | S06 | R3 |
| EDT06 | Sửa control/rules/role docs; book rules có cả nội dung đọc được và schema | S06,S05,S21 | R2 |
| EDT07 | Chapter workspace: brief, plan, phiên bản và inspiration card chỉ tư vấn | S06,S21 | R2 |
| EDT08 | Restore bản chương cũ, đánh dấu/đồng bộ lại derived state | S06,S21 | R2 |
| EDT09 | Xóa chương mới nhất, trash và rollback state/index; chính sách cho xóa chương giữa cần riêng | S06,S22,S21 | R2 |
| EDT10 | Recount/sync chương; rebuild state và search từ văn bản đã sửa | S04,S06,S22 | R2 |
| EDT11 | Review/revise/export artifact độc lập; domain-owned artifact phải dùng domain action | S20 | R3–R6 |
| EDT12 | Review và export đúng revision đã pin; nhận biết review/export stale sau sửa | S03,S20 | R3 |
| EDT13 | Rollback/regenerate từ chương N: snapshot trước N, xử lý chương N trở đi và sinh lại chương; phân biệt rework không rollback | S22,S04 | R3 |

### 15.5 Bộ nhớ, tài liệu và tham khảo

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| MEM01 | Facts có subject/predicate/object, nguồn và khoảng hiệu lực theo chương | S05 | R2 |
| MEM02 | Hooks open/progressing/deferred/resolved/superseded, dependency/payoff và ghi chú | S05 | R2 |
| MEM03 | Chapter summaries và ma trận nhân vật; projection dễ đọc | S05,S21 | R2 |
| MEM04 | Một retrieval kernel FTS5/BM25 cho memory, material và Skill reference | S05,S07 | R2–R3 |
| MEM05 | Truy xuất giữ source location; chọn ngữ nghĩa từ ứng viên lexical và compaction trace | S04,S05,S07 | R2–R3 |
| MEM06 | Import material từ URL/file text/PDF; lưu nguồn, purpose và text đã trích xuất | S07 | R3–R4 |
| MEM07 | Bind/unbind/list material vào truyện với uses/note; chỉ lấy theo nhiệm vụ | S07 | R3 |
| MEM08 | Tìm/read/list nội dung trong phạm vi; chặn path traversal và nguồn không hợp lệ | S02,S07 | R2–R3 |
| MEM09 | Rebuild index từ dữ liệu chuẩn; không coi search DB là canon | S05,S07 | R2 |

### 15.6 Truyện ngắn hoàn chỉnh

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| SHT01 | Tạo truyện ngắn từ direction/reference, tiêu đề, số phần và độ dài | S08 | R3 |
| SHT02 | Chạy cả chuỗi hoặc riêng outline/draft/review/package | S08 | R3 |
| SHT03 | Viết theo batch, lưu partial, bổ sung phần thiếu và resume | S08 | R3 |
| SHT04 | Review toàn truyện/phạm vi, dẫn chứng và delivery checks theo manuscript hash | S08 | R3 |
| SHT05 | Opening hook độc lập, đo độ dài và giữ yêu cầu tiêu đề/số chương | S08 | R3 |
| SHT06 | Sales package: synopsis/selling points và cover prompt; không tự sửa manuscript khi chỉ đóng gói | S08 | R3 |
| SHT07 | Revise toàn truyện hoặc một số chương; thay cấu trúc/số chương theo chỉ dẫn có scope rõ | S08 | R3 |
| SHT08 | Revision operation ID/checkpoint; resume đúng nguồn, giữ tiến độ review/package và báo changed chapters | S08 | R3 |
| SHT09 | Cover tùy chọn và trạng thái kiểm chứng checks_passed/needs_revision/unverified | S08 | R3–R4 |

### 15.7 Import, fanfic, ngoại truyện và phong cách

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| ADP01 | Import chương từ văn bản/file; split mặc định/tùy chỉnh, giữ nguyên nội dung và provenance | S09,S22 | R3 |
| ADP02 | Reverse-engineer foundation và replay từng chương để dựng state/hook/summary | S04,S09 | R3 |
| ADP03 | Resume import; continuation hoặc series mới với ranh giới nguồn rõ | S04,S09 | R3 |
| ADP04 | Import parent canon/external canon file và gắn tác phẩm nguồn | S04,S09,S21 | R3 |
| ADP05 | Fanfic: canon/AU/OOC/CP, đọc canon và refresh từ nguồn | S09,S16,S22 | R3 |
| ADP06 | Spinoff: tác phẩm riêng, parent lineage và định hướng ngoại truyện | S04,S09 | R3 |
| ADP07 | Style analyze/import: guide thao tác dựa bằng chứng của văn bản mẫu | S04,S16,S21 | R3 |
| ADP08 | Imitation Work mới: premise riêng, pin nguồn và gắn style guide | S04,S09,S16 | R3 |
| ADP09 | Phân tích truyện dài/ngắn để học cấu trúc, nhịp, emotion/evidence/reversal | S16,S03 | R3 |

### 15.8 Kịch bản và storyboard

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| SCR01 | Chuyển ý tưởng/nguồn thành script theo format, số tập, thời lượng và requirements | S10 | R5 |
| SCR02 | Persist spec/source trước, sinh script và lưu revision; failure giữ candidate | S10,S20 | R5 |
| SCR03 | Tạo storyboard từ script/narrative: style, aspect ratio, granularity, max shots | S10 | R5 |
| SCR04 | Shot list/storyboard và image prompts là artifact riêng có liên hệ | S10 | R5 |
| SCR05 | Asset manifest nguồn/generated/selected, variants và shot prompt mapping | S10 | R5 |
| SCR06 | Review/revise phạm vi và export đúng bản script/storyboard | S20 | R5 |

### 15.9 Interactive film, graph và player

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| FIL01 | Tạo film package: spec, story tree, flags, script, storyboard, image prompts và graph | S10,S11 | R6 |
| FIL02 | Wizard/workbench cho world anchor, nhân vật/voice, biến, structure và endings | S11,S12,S21 | R6 |
| FIL03 | Node start/normal/branch/merge/ending/explore, scene và dialogue | S11 | R6 |
| FIL04 | Choice với target, condition/effect, variables và ending definitions | S11 | R6 |
| FIL05 | Draft structure, fill/revise node, connect choice, remove node bằng typed delta | S11,S12 | R6 |
| FIL06 | Tree/React Flow view và lưu vị trí node; chỉnh graph có revision | S11,S21 | R6 |
| FIL07 | Validation broken-link/dead-end/unreachable/ending/gated path/type/unused variable | S11 | R6 |
| FIL08 | Delivery requirements: cấu trúc mong muốn, báo cáo và evidence | S11,S12 | R6 |
| FIL09 | Path analysis: phân bố ending/độ dài, giới hạn enumeration và đánh dấu truncated | S11 | R6 |
| FIL10 | Player/HTML preview: evaluate điều kiện, effects, lựa chọn và kết thúc | S11,S12,S21 | R6 |
| FIL11 | Sinh ảnh cho node, gắn asset và version | S12 | R6 |
| FIL12 | Export graph JSON, Ink và playable HTML/package | S12,S21 | R6 |

### 15.10 Play: thế giới mở và lựa chọn dẫn hướng

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| PLY01 | Tạo world riêng, mode open/guided, world contract và visual contract | S13,S03 | R6 |
| PLY02 | Seed opening scene và đồ thị player/world có thể chơi | S13 | R6 |
| PLY03 | Hành động tự do hoặc số lựa chọn cấu hình; diễn tiến theo lượt | S13 | R6 |
| PLY04 | Entities, edges/relations, state slots, events và lifecycle evidence | S13 | R6 |
| PLY05 | Time semantics, location, vật phẩm, kiến thức và quan hệ theo contract | S13 | R6 |
| PLY06 | HUD và kiểm tra entity/holding/evidence/relation/state | S13,S21 | R6 |
| PLY07 | Một lượt tạo action intent, mutation và scene nhất quán, validate trước commit | S13 | R6 |
| PLY08 | Snapshot trước lượt và rollback nếu commit lỗi | S13 | R6 |
| PLY09 | Regenerate scene giữ facts; đổi hành động thì rollback/replay; save/restore variant | S13 | R6 |
| PLY10 | Chỉnh contract/state bằng domain action; inspect current world/run | S13,S02 | R6 |
| PLY11 | Ảnh scene/entity, image settings và variants; sinh ảnh không tiến thêm lượt | S13 | R6 |

### 15.11 Dịch thuật dài và glossary

Thứ tự: làm trước chiều **ngoại ngữ → tiếng Việt** (thường gặp: tiếng Trung, tiếng Anh), vì kết quả là tác phẩm tiếng Việt dùng chung gói `vi` (kiểm tra xưng hô, tên Hán Việt, chính tả). Các chiều khác thêm khi có gói ngôn ngữ đích tương ứng. Bản dịch là một tác phẩm trong thư viện, dùng chung editor, review và xuất bản. Nhóm này nằm ngoài MVP.

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| TRN01 | Nguồn inline hoặc EPUB/PDF text/TXT/Markdown, chapter splitting | S14 | R4 |
| TRN02 | Chọn ngôn ngữ nguồn/đích (bản đầu: đích tiếng Việt), title, segment size, glossary tên riêng (Hán Việt/phiên âm) và quy tắc xưng hô | S14 | R4 |
| TRN03 | Dịch pending segments theo batch; kiểm tra thiếu/trùng/sai index/output rỗng | S14 | R4 |
| TRN04 | Merge glossary và lưu progress từng batch để resume | S14 | R4 |
| TRN05 | Review từng chương với evidence, tổng hợp report và pending counts | S14 | R4 |
| TRN06 | Revise một segment, giữ nguồn và phiên bản | S14 | R4 |
| TRN07 | Export TXT/Markdown/EPUB, giữ title/metadata và liên hệ nguồn | S14 | R4 |

### 15.12 Bìa và tài nguyên hình ảnh

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| IMG01 | Bìa riêng hoặc bìa gắn Work, visual brief từ nội dung và yêu cầu tác giả | S08,S15,S16 | R4 |
| IMG02 | Provider/model/base URL/API key cho ảnh tách khỏi model viết | S15,S21 | R4 |
| IMG03 | Sinh/regenerate bằng prompt, tham khảo ảnh khi endpoint hỗ trợ | S08,S15 | R4 |
| IMG04 | Chữ trên bìa/title, selling package và constraints thị giác là input phân biệt | S08,S16 | R4 |
| IMG05 | Lưu binary thật, manifest, request, revision và chọn ảnh hiện hành | S08,S13,S20 | R4–R6 |

### 15.13 Model, provider và chẩn đoán

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| MOD01 | Service settings, thêm/xóa dịch vụ và lưu secret riêng | S15,S21 | R1–R2 |
| MOD02 | Tự lấy danh sách model từ `{base_url}/v1/models` khi mở app và theo nút "Kiểm tra lấy danh sách"; danh sách ghi đè có thứ tự (đầu tiên = mặc định); metadata context/output/effort/giá tự điền khi server trả về, người dùng sửa được; cache trong DB (§7.1) | S15,S21 | R2 |
| MOD03 | Custom endpoint/model; nhóm aggregator và CodingPlan metadata | S15 | R2–R7 |
| MOD04 | Protocol Chat Completions/Responses/Anthropic, streaming và non-streaming | S15,S22 | R2–R4 |
| MOD05 | Model mặc định, effort mặc định, ưu tiên context dài; model + effort theo vai trò (lập kế hoạch, viết, kiểm tra/settle, mối nối/review, tóm tắt), ghi đè theo truyện | S15,S21,S22 | R2 |
| MOD06 | Kiểm tra model/provider/protocol phù hợp; chính sách tương thích từng endpoint | S15 | R2–R7 |
| MOD07 | Ollama/LM Studio local; xử lý endpoint không cần API key khi phù hợp | S15 | R2–R4 |
| MOD08 | Proxy, custom headers, extra options và lọc tham số override reserved | S15 | R4 |
| MOD09 | Timeout first event/idle/request, retry transient hữu hạn, tiếp tục output bị giới hạn | S15,S03 | R2 |
| MOD10 | Doctor: cấu hình hiệu lực, nguồn settings, kết nối/model và lỗi cụ thể | S15,S21,S22 | R2 |
| MOD11 | CLI/env overrides được phân biệt với Studio settings; import env rõ ràng | S15,S21,S22 | R7 |

### 15.14 Skills và phương pháp sáng tác

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| SKL01 | Danh mục Skill, mô tả, nguồn và chẩn đoán lỗi load | S16,S21 | R2 |
| SKL02 | 20 nhóm phương pháp tích hợp, gắn theo Profile/action | S16 | R2–R6 |
| SKL03 | Import folder có SKILL.md và references tĩnh; edit/delete project Skill | S16,S21 | R3 |
| SKL04 | Project Skill cùng ID override built-in; pin version dùng cho run | S16,S02 | R3 |
| SKL05 | Agent lựa chọn/use_skill và @skill-id cho một lượt; không tự nâng quyền tool | S16,S03 | R3 |
| SKL06 | Creative Methods Editor chỉnh Profile/Skill, phương pháp tách khỏi runtime protocol | S16,S01,S21 | R3 |

### 15.15 Tự động hóa, xuất bản, analytics và tích hợp

| ID | Tính năng / kết quả | Nguồn | Giai đoạn |
|---|---|---|---|
| OPS01 | Auto-write tới chương mục tiêu, batch summary và trạng thái tác phẩm | S04,S22 | R2 |
| OPS02 | Scheduler start/stop, write/radar cycle, concurrency, cooldown/retry và hạn mức mỗi ngày | S18,S21 | R7 |
| OPS03 | Radar market scan, kết quả/cơ hội và lịch sử | S18,S21 | R4 |
| OPS04 | Research web theo mục đích/depth, nguồn, query log và partial failures | S18,S07 | R4 |
| OPS05 | Analytics: độ dài, nhận xét, tiến độ, token usage và context trace | S18,S04,S21 | R2–R4 |
| OPS06 | AIGC detect một/all chương, lưu kết quả và thống kê; provider GPTZero/Originality/custom | S19,S22,S21 | R4 |
| OPS07 | Export truyện TXT/Markdown/EPUB, download hoặc lưu file | S20,S21,S22 | R2 |
| OPS08 | Log có cấu trúc, xem log/progress, quiet/JSON output cho automation | S18,S21,S22 | R2,R7 |
| OPS09 | Telegram, Feishu/Lark, WeCom và webhook event filter/HMAC | S18,S21,S22 | R7 |
| OPS10 | UI preferences (ngôn ngữ giao diện – MVP chỉ tiếng Việt, theme, font, cỡ chữ) và cấu hình dự án; persist trong data | S21 | R1–R2 |
| OPS11 | Tương đương CLI/TUI/interact JSON cho external agents, slash commands/model/depth/confirm | S22,S03 | R7 |
| OPS12 | Update và health/runtime check; bản desktop thay bằng installer/update có ký | S22 | R7 |

### 15.16 Danh mục 20 phương pháp tích hợp

| Skill nguồn | Phương pháp tương ứng trong Python |
|---|---|
| inkos-long-writing | Viết truyện dài, nhân quả nhân vật, cảnh và nhịp nối chương |
| inkos-short-writing | Truyện ngắn, whole-story craft và đóng gói |
| inkos-story-review | Review có tiêu chí và bằng chứng |
| inkos-story-deslop | Sửa văn rập khuôn/mơ hồ theo ngữ nghĩa, giữ giọng tác giả |
| inkos-story-import | Import manuscript và tái dựng canon |
| inkos-continuation-writing | Viết tiếp và xác định ranh giới series mới |
| inkos-fanfic-writing | Fanfic và mức độ lệch canon |
| inkos-spinoff-writing | Ngoại truyện có arc độc lập và parent lineage |
| inkos-imitation-writing | Học kỹ thuật phong cách, xây premise mới |
| inkos-long-story-analysis | Phân tích văn bản dài |
| inkos-short-story-analysis | Phân tích cấu trúc/đảo chiều truyện ngắn |
| inkos-long-market-research | Nghiên cứu thị trường truyện dài |
| inkos-short-market-research | Nghiên cứu thị trường truyện ngắn |
| inkos-script-writing | Chuyển thể và viết kịch bản |
| inkos-storyboard | Phân cảnh/shot và prompt thị giác |
| inkos-interactive-film | Cấu trúc lựa chọn, node và kết thúc |
| inkos-play-world | Contract và diễn tiến thế giới tương tác |
| inkos-play-illustration | Ảnh scene/entity nhất quán với facts |
| inkos-story-cover | Định hướng bìa, chữ và constraints |
| inkos-translation | Dịch dài (trước tiên sang tiếng Việt): glossary tên Hán Việt/phiên âm, xưng hô, segment và review |

Phương pháp thuộc gói ngôn ngữ. Bản đầu tiên viết bằng tiếng Việt cho văn học mạng Việt Nam (không dịch máy từ bản zh/en), có schema đầu ra, ví dụ tiếng Việt và sample evaluation; ngôn ngữ khác có bộ phương pháp riêng khi thêm gói. Hai nhóm nghiên cứu thị trường (long/short-market-research) hướng tới nền tảng đọc truyện tiếng Việt thay vì nền tảng Trung Quốc của nguồn. Nếu sử dụng lại nguyên Skill/prompt nguồn, áp dụng nghĩa vụ giấy phép đã nêu ở phần 12.

## 16. Luồng xử lý nghiệp vụ và phục hồi

Trong mỗi luồng, nguồn InkOS cung cấp hành vi tham khảo. DB transaction, đường dẫn data, UI Tiptap và vault là thiết kế triển khai của WriteStoryApp. UI button, chat tool và CLI dùng chung application use case; không xây ba pipeline độc lập.

### FL01 — Khởi động và chọn data-root

Đầu vào: thư mục portable hoặc data-root người dùng đã chọn.

1. Rust xác định data-root tuyệt đối, kiểm tra quyền ghi, khóa single-instance.
2. Khởi chạy Python bằng bootstrap pipe, loopback socket và token; kiểm tra protocol version.
3. Migrate DB sau backup cần thiết; tạo các thư mục còn thiếu; reconcile job/session/episode bị gián đoạn.
4. Load library/settings; mở vault khi cần dùng key; FE nối stream từ event cursor.

Đầu ra: desktop ready với DB tại data/db/app.sqlite3. Lỗi: quyền ghi/migration/protocol đưa ra thông báo cụ thể; không tạo DB mới ở vị trí khác rồi hiển thị thư viện trống.

### FL02 — Chat → capability → artifact

Đầu vào: text, session, Work hiện tại, attachment/source refs và model.

1. Persist request ID, author instruction và baseline revision; chặn submit trùng.
2. Resolve Profile, capability, Skill và context chỉ trong phạm vi Work.
3. Agent thảo luận hoặc gọi typed tool; host validate arguments, scope và policy. Action destructive phải confirm; action recoverable tuân policy, không hỏi lại mọi bước.
4. Runtime tạo episode/action events, khóa mutation cần thiết và gọi use case.
5. Publish artifact refs/revision/observations; session chưa bound được gắn vào Work vừa tạo.
6. Finish dựa receipt: answered/delivered/needs_input/blocked; content quality và execution success là hai thông tin riêng.

Lỗi: giữ request/checkpoint và partial artifacts, retry đúng request/baseline; cancel truyền tới provider. Không báo đã xuất/đã viết nếu chưa có artifact thật. Nguồn: S02,S03,S20.

### FL03 — Tạo nền truyện và recover draft

Đầu vào: title, ngôn ngữ (MVP: `vi`), thể loại, style profile (giọng văn, Hán Việt/thuần Việt, kiểu thoại), mục tiêu chương/độ dài theo đơn vị của gói ngôn ngữ, brief/reference.

1. Tạo Work draft, lưu brief và source lineage.
2. Architect sinh story frame, volume map, roles, rules và author intent/focus.
3. Kiểm tra schema, đầy đủ đầu vào cần viết; persist candidate và stage checkpoint.
4. Nhận foundation hợp lệ, tạo state seed/snapshot chương 0; chuyển readiness.

Lỗi: Work vẫn draft, UI hiển thị phần đã có và action recover/revise foundation; writer không chạy trên nền thiếu. Nguồn: S04,S01.

### FL04 — Viết chương kế tiếp

Đầu vào: Work ready, chapter brief, focus, length contract và revision hiện tại.

1. Kiểm tra cổng vào: chương N-1 committed, `state_applied`, `continuity_status = ok`. Xác định next chapter, lấy khóa truyện (xếp hàng nếu đang bận); kiểm tra không trùng số chương.
2. Load handoff(N-1), state snapshot, story_events và hooks đến hạn. Planner tạo chapter plan có `input_hash`; retrieval/composer chọn canon, references, Skill và context budget theo lớp; lưu intent/context/trace.
3. Writer nhận plan + handoff + tail_text(N-1), stream candidate, đo độ dài; persist partial nhưng chưa đánh dấu complete.
4. Kiểm tra xác định (độ dài, tên riêng, nhân vật đã chết, anti-slop, lặp n-gram).
5. Settlement tạo typed state delta và ending_state(N); validate cấu trúc/canon (xác định trước, LLM sau).
6. Seam check giữa đoạn mở chương N và ending_state(N-1); reviewer ghi findings có bằng chứng và mức độ.
7. Blocker hoặc seam fail → sửa cục bộ, quay lại bước 4, tối đa K vòng. Hết vòng → `waiting_user` + `blocked_needs_resync`, không commit.
8. Commit chapter revision, state snapshot, handoff(N), summaries/hooks/timeline, measurement, usage và job result trong một transaction; cập nhật FTS và event.
9. Hiển thị chương/observations; gửi thông báo đã cấu hình sau khi commit; scheduler mới được enqueue chương N+1.

Không áp một phần state. Khác InkOS: không bao giờ lưu chương khi state không hợp lệ (InkOS vẫn lưu và giữ state cũ, khiến diễn biến chương đó mất khỏi bộ nhớ truyện). Findings về văn chương (`minor`) không tự biến thành lỗi kỹ thuật. Lỗi provider giữ draft/checkpoint; không tự chạy chương sau với dữ liệu chưa nhất quán. Nguồn: S04,S05; chi tiết §6.2.

### FL05 — Viết nhiều chương hoặc tới chương mục tiêu

1. Tính range còn thiếu, chọn chế độ `auto` / `review_each` / `review_every_k`, pin request/base revision. Cấu hình model/effort/methods được ghim **theo từng job chương** lúc job bắt đầu (§7.1), nên thay đổi cài đặt áp từ chương kế tiếp.
2. Đưa vào hàng đợi của truyện; scheduler đa truyện cấp slot theo xoay vòng công bằng và limiter provider.
3. Thực hiện FL04 tuần tự; sau mỗi chương publish receipt và checkpoint, rồi mới enqueue chương kế tiếp.
4. Nếu dừng ở chương N (waiting_user, blocked, cancel, hết ngân sách), giữ nguyên các chương hoàn tất; resume chỉ range chưa có.
5. Cập nhật total usage/batch summary; hạn mức/cooldown áp theo từng provider và truyện.

Nhiều truyện chạy FL05 cùng lúc; trong một truyện không chạy đồng thời các chương. Nếu range không bắt đầu ở next chapter, trả conflict và inspect/recovery action. Nguồn: S04,S22; mô hình đồng thời §4.2.

### FL06 — Review, sửa có phạm vi và nhận bản mới

1. Pin artifact/revision chính xác, request tác giả và nguồn so sánh.
2. Review trả findings với source ID/line range; host xác minh quote thật, đánh dấu unavailable khi thiếu nguồn.
3. Revise xác định editable scope trước; generate replacement riêng cho selection/range hoặc cả chương theo mode.
4. Host giữ phần ngoài scope, đo diff/length, lưu candidate và kiểm tra expected revision.
5. Receive/adopt tạo current revision; rebuild state bị ảnh hưởng trước khi writer tiếp tục.

Nếu source đổi trong lúc AI chạy, giữ candidate và trả revision conflict. Review-only/export-only không được ngầm sửa prose. Nguồn: S06,S20,S04.

### FL07 — Sửa tay, rename, restore, delete và resync

1. Chụp version trước sửa; validate thao tác và affected scope.
2. Lưu text replace/local patch hoặc rename entity có preview phạm vi; không sửa snapshots/history.
3. Mark derived-state/search/review stale khi nguồn đổi; job resync dùng văn bản mới.
4. Restore version chạy như một revision mới. Xóa latest chapter có confirm, trash và rollback snapshot/index.
5. Resync settle/review lại rồi cập nhật canonical state; lịch sử action được giữ.

Xóa/sửa chương giữa có ảnh hưởng các chương sau: bản Python hiển thị dependency và lựa chọn rebuild, không mặc định xóa hàng loạt. Rewrite/rework và rollback/regenerate là hai action phân biệt.

Action rollback/regenerate tương đương CLI nguồn: chọn chương N → kiểm tra snapshot N-1 → confirm phạm vi → backup/archive chương N trở đi → restore state N-1 → enqueue viết lại N. CLI nguồn xóa các file downstream; bản Python lưu chúng trong history/archive để có thể phục hồi khi generation lỗi. Việc viết tiếp lại toàn bộ downstream là batch action riêng. Nguồn: S06,S04,S21,S22.

### FL08 — Narrative forecast

1. Đọc canon hiện tại và tạo fingerprint.
2. Nhập divergence, số branch và horizon; AI sinh nhiều kế hoạch tương lai độc lập.
3. Lưu branch/comparison bên ngoài canonical state; re-check fingerprint khi mở lại.
4. Chọn branch chỉ tạo selected candidate plan.

Applying plan vào outline/focus là action riêng có review/confirmation. Không tự sửa chương đã có hoặc coi tương lai dự đoán là facts. Nguồn: S17.

### FL09 — Tài liệu tham khảo và retrieval

1. Nhập file hoặc fetch URL; copy nguồn vào data/imports, kiểm tra loại/kích thước, extract text.
2. Persist material với title/purpose/source và source offsets; index FTS.
3. Bind vào Work với uses/note, hoặc unbind khi không còn phù hợp.
4. Job tìm BM25 candidates, chọn các đoạn phù hợp nhiệm vụ và budget; giữ provenance trong trace.

Lỗi một nguồn không được làm mất nguồn khác; tài liệu thiếu/không extract được có trạng thái riêng. PDF scan không tự được coi là text PDF. Nguồn: S07,S05.

### FL10 — Import truyện có sẵn và viết tiếp

1. Nhận manuscript, preview chapter splitting/regex và continuation/series boundary.
2. Tạo Work draft; giữ text gốc, chapter order và imported provenance.
3. Compile nguồn lớn thành context cho Architect; dựng foundation một lần.
4. Replay chương tuần tự để dựng state/hook/summary từ văn bản thật, snapshot từng bước.
5. Resume từ chapter checkpoint, không trả phí Architect lại nếu foundation còn hợp lệ.
6. Chỉ mở writer tại next chapter khi import hoàn tất; series mới có lineage riêng.

Lỗi/nguồn đổi: không trộn hai manuscript vào cùng checkpoint. Nguồn: S04,S09.

### FL11 — Fanfic và refresh canon

1. Import/pin source; parse canon, nhân vật, world rules và information boundaries.
2. Chọn mode canon/AU/OOC/CP cùng direction; tạo Work mới.
3. Dựng foundation với phạm vi deviation đã yêu cầu; viết bằng FL04.
4. Refresh source tạo canon revision mới; review ảnh hưởng trước áp vào tác phẩm đang viết.

Parent/reference không bị chỉnh khi viết fanfic. Nguồn: S09,S16.

### FL12 — Spinoff và imitation/style analysis

1. Chọn nguồn đúng artifact/revision và premise riêng.
2. Spinoff lấy parent canon cho một arc mới; imitation trích style guide có bằng chứng, không copy plot vào premise.
3. Tạo Work/lineage, foundation và constraints; persist guide/source refs.
4. Viết/review theo FL04/FL06; guide có thể sửa và version riêng.

Nguồn: S04,S09,S16,S20.

### FL13 — Truyện ngắn và sales package

1. Nhập direction/reference, title, số phần, length range và opening hook.
2. Outline → draft theo batch → kiểm tra đủ phần/text → review → package.
3. Lưu partial/batch checkpoint; completion hữu hạn cho phần thiếu, không khai đủ chương nếu chưa đủ.
4. Review gắn manuscript hash; package sinh synopsis/selling points/cover prompt từ bản hiện hành.
5. Có thể chạy riêng từng stage; review/package-only không sửa manuscript. Ảnh bìa là job riêng/tùy chọn.

Quality status checks_passed/needs_revision/unverified phân biệt với job execution. Nguồn: S08.

### FL14 — Revise truyện ngắn và resume operation

1. Pin manuscript/outline/review hash; chọn scope và constraints mới.
2. Lập revision plan, map chương giữ/di chuyển/viết lại; lưu operation ID.
3. Thực thi từng chương trong plan, checkpoint completed parts.
4. Review/package lại đúng manuscript mới, không rewrite thêm khi retry finalization.
5. Trả changed chapter numbers, title/opening/outline changes và delivery status.

Resume chỉ dùng operation ID của request đã lưu; nguồn hoặc constraints đổi thì conflict/new operation rõ ràng. Nguồn: S08.

### FL15 — Kịch bản

1. Pin text/source, format, tập/thời lượng và requirements.
2. Persist script spec và source trước khi gọi AI.
3. Generate script bằng phương pháp script; validate artifact không rỗng và lưu revision.
4. Review/revise có scope, export đúng revision.

Nếu generation lỗi, Work vẫn giữ spec/source và candidate để retry. Nguồn: S10,S20.

### FL16 — Storyboard và asset mapping

1. Nhận script/text, visual style, aspect ratio, shot granularity/max shots.
2. Persist spec; tạo storyboard/shot list và image prompts riêng.
3. Tạo manifest mapping shot → prompt → source/generated/selected asset.
4. Review continuity/visual constraints; regenerate/chọn ảnh không thay source script ngoài scope.

Sinh image prompt hoặc assets manifest không đồng nghĩa đã có ảnh; binary phải thực sự được tạo. Nguồn: S10,S20.

### FL17 — Interactive film: tạo và chỉnh graph

1. World anchor/characters/voice/variables/endings và requirements được persist.
2. Tạo package hoặc draft structure rồi fill từng node.
3. Typed graph delta cho revise/connect/remove; validate schema và giữ revision.
4. Chạy structural + gated reachability/type + delivery validation; lưu findings.
5. Preview/player chạy evaluator; path analysis báo ending distribution và giới hạn enumeration.
6. Sinh ảnh node và export JSON/Ink/playable HTML đúng revision.

Graph invalid giữ candidate để sửa, không báo package valid. Export evidence ghi source revision; review hiện hành stale khi graph đổi. Nguồn: S10,S11,S12.

### FL18 — Player lựa chọn

1. Load graph revision, khởi tạo variables và start node.
2. Lọc dialogue/choices theo condition; người dùng chọn một choice khả dụng.
3. Apply effects set/add/sub có kiểm tra type; chuyển target node.
4. Lưu player state/history nếu cần, hiển thị ending; reset tạo run mới.

Broken link/dead end/không có choice khả dụng trả trạng thái giải thích được; không tự đi tới một node bất kỳ. Nguồn: S11,S12,S21.

### FL19 — Play: tạo world và một lượt hành động

1. Persist world contract, mode open/guided, quy tắc văn phong và hình ảnh.
2. Sinh opening scene; extract seed graph; yêu cầu player/world graph đủ để chơi.
3. User action → context → action intent + mutation + scene/choices.
4. Validate entity references, holdings/evidence, time và rules; chụp snapshot trước turn.
5. Commit graph/event/current state/presentation/transcript cùng ranh giới turn trong SQLite.

Lỗi thì rollback lượt, giữ variant/candidate nếu có; không tăng turn trên scene chưa commit. Contract quyết định hệ thống, không áp RPG mặc định cho mọi world. Nguồn: S13.

### FL20 — Play: regenerate, variants và ảnh

1. Nếu chỉ sửa cách kể scene, giữ facts/actions/time và choices theo yêu cầu.
2. Nếu thay hành động, khôi phục checkpoint trước turn rồi replay input mới.
3. Giữ variant cũ/mới; restore variant phục hồi graph/state/scene/transcript nhất quán.
4. Image job pin scene/entity context, sinh binary, lưu versions/settings/manifest và cập nhật HUD.

Sinh ảnh không tiến lượt; ảnh cũ không được gắn nhầm vào scene mới. Nguồn: S13.

### FL21 — Dịch truyện dài (trước tiên sang tiếng Việt)

1. Inline/file → extract → chapter/segment → manifest và glossary.
2. Dịch chỉ pending segments theo batch; kiểm tra ID/index đầy đủ, không trùng hoặc target rỗng.
3. Merge glossary, persist batch progress và usage; resume từ pending.
4. Review chương và lưu findings/report; sửa segment bằng action riêng.
5. Export source/target đã chọn ra TXT/Markdown/EPUB đúng revision.

Translation source giữ nguyên. PDF scan yêu cầu OCR mở rộng. Nguồn: S14.

### FL22 — Bìa/ảnh độc lập

1. Chọn Work, visual instruction, title lettering, size/aspect, model/provider ảnh và reference nếu hỗ trợ.
2. Compile prompt từ story context và yêu cầu thực; tạo request snapshot.
3. Gọi API ảnh; nhận/download binary thật; kiểm tra format và persist asset.
4. Lưu revision/manifest, chọn current variant, preview/export.

Nếu fail, không chỉ tạo path rồi báo thành công. Caption/marketing/reference không tự trở thành chữ in trên bìa. Nguồn: S08,S15,S16.

### FL23 — Research, Radar và detection

1. Research xác định query/purpose/depth; gọi search/fetch, lưu source/query log và partial failure.
2. Radar dùng bằng chứng để sinh hướng/cơ hội cho tác phẩm, lưu history; tác giả chọn áp vào brief.
3. Detection pin chapter revision, gọi provider detection, lưu raw/normalized result và stats.

Search không có key/bị lỗi không được giả nguồn mới. Detection là chỉ báo từ dịch vụ, không bảo đảm văn bản là/không là AI; de-slop sửa craft không hứa vượt detector. Nguồn: S18,S19,S16.

### FL24 — Scheduler, quota và notifications

1. Người dùng cấu hình lịch, timezone, chapter target, provider limits và notifications.
2. Scheduler chọn Work active theo xoay vòng công bằng (không lấy N truyện đầu danh sách như InkOS), tránh tick overlap, enqueue FL05/job nghiên cứu; dùng biểu thức cron thật thay vì quy đổi xấp xỉ sang interval.
3. Persist quota theo ngày/timezone, retry/cooldown và next-run; respect pause/cancel.
4. Sau commit, ghi notification outbox; gửi native notification hoặc các kênh đã bật, retry độc lập.

MVP local chỉ chạy scheduler khi backend đang mở. Để viết khi đóng cửa sổ, cần chế độ tray/background được người dùng bật rõ ràng ở R7; máy sleep không được hứa vẫn xử lý. Lỗi thông báo không rollback chương đã lưu. Nguồn: S18,S21,S22; durable quota/outbox là cải tiến Python.

### FL25 — Export, backup/restore và migration

1. Pin source revision, kiểm tra artifact/delivery status; export collection hoặc artifact phù hợp domain.
2. Ghi file tạm rồi finalize vào data/exports; ghi export receipt với source revision/hash.
3. Backup dùng `VACUUM INTO` ra file tạm rồi rename (§5) và asset manifest, ghi vào data/backups; không lồng các backup cũ.
4. Restore validate schema/checksum, backup hiện trạng trước, đóng writers rồi thay dữ liệu/rebuild projection.
5. Import dữ liệu InkOS có preview, nhận biết kiểu Work/source và migrate thành DB/asset của Python; không sửa thư mục nguồn.

Lỗi giữ backup/bản gốc, không báo đã restore khi chỉ copy được một phần. Nguồn: S20,S22; transaction SQLite và portable data là thiết kế Python.

### FL26 — Provider, Skill và Profile settings

1. Configure provider/protocol/base URL/proxy, secret trong vault; bật/tắt tự lấy danh sách model, ưu tiên context dài, effort mặc định.
2. Lấy `{base_url}/v1/models` (khi mở app hoặc bấm kiểm tra), merge vào danh sách model không ghi đè trường người dùng sửa; sắp thứ tự danh sách ghi đè (đầu tiên = mặc định); gán model + effort theo vai trò (§7.1). Lưu capability và error cụ thể; không dùng model ảnh cho writer.
3. Import/edit Profile/Skill trong data; validate IDs, schema và static reference paths.
4. Pin cấu hình và Skill version vào từng job; chỉnh settings không làm run đang chạy đổi model ngầm.

Skill không tự chạy script hoặc bỏ qua tool policy. CLI override chỉ áp lượt chạy được yêu cầu; UI không bị env ghi đè ngầm. Nguồn: S01,S15,S16,S22.

## 17. Kiến trúc mở rộng để chứa toàn bộ phạm vi

Giữ nguyên React/Tauri/FastAPI/SQLite đã chốt. Bổ sung domain modules và action contracts thay vì chuyển sang server/cloud.

```text
be/src/writestory_be/
  api/                       API mỏng; export OpenAPI cho FE
  jobs/                      Supervisor, checkpoint, events, recovery
  modules/
    harness/                 Profile, Capability, ActionResult, Episode
    sessions/                Chat, transcript, requests, binding
    works/                   Library, artifact và lineage
    chapters/                Save/accept/restore với revision checks
    longform/                Foundation, chapter, state, hooks
    short_fiction/           Stages, delivery, revision operations
    adaptation/              Import, canon, fanfic, spinoff, style
    scripts/                 Spec, draft, review, revision
    storyboards/             Shots, prompts, asset mapping
    interactive_film/        Graph, evaluator, delta, validation, export
    play/                    World, graph entities, turn, variants
    translation/             Source, segments, glossary, review
    visual/                  Cover, illustration, asset variants
    research/                Materials, references, Radar/search
    operations/              Export/backup use cases và notification
  infrastructure/
    db/                      SQLite repositories, transactions, FTS
    files/                   Assets, export/backup adapters
    secrets/                 Encrypted vault
    ai/                      Context/progress ports implementation

ai/src/writestory_ai/
  contracts/                 AI typed input/output, không phải DB models
  ports/                     Provider/context/progress interfaces
  providers/                 Text/image/search/detection adapters
  context/                   Budgets, governance, retrieval policy, trace
  methods/                   Skill registry, static references, versions
  workflows/                 Pipeline theo longform/short/script/film/play/translation
  prompts/                   Templates đóng gói, version/checksum
  evaluators/                Continuity và output validation
  policies/                  Bounded retry/limits
```

Các module mở theo giai đoạn, không tạo toàn bộ thư mục rỗng từ đầu. AI không import BE hoặc ghi canonical SQLite. BE triển khai context/progress ports để AI lấy evidence và phát checkpoint; phần 22 và tài liệu cấu trúc quy định dependency chi tiết.

Contracts tối thiểu:

- Work: id/profile/language/genre/style_profile/status/lineage/metadata và current artifact refs.
- Profile: capabilities, required/recommended methods, artifact schemas, confirmation và production options.
- ActionRequest: action, payload, source UI/chat/CLI, expected revisions, author instruction, confirmation và idempotency key.
- ActionResult: execution status, summary, artifact revision refs, observations, measurements, usage và recovery details.
- DeliveryStatus: checks_passed/needs_revision/unverified/stale, không đồng nhất với job success.
- Observation: category execution/quality/scope, assessment issue/resolved/unavailable/observation, target revision/hash và source ranges.
- JobStep: input/output hashes, checkpoint, pinned methods/model, attempt, cost, timestamps và cancellation.

API mở rộng theo domain: `/v1/profiles`, `/v1/skills`, `/v1/sessions`, `/v1/episodes`, `/v1/materials`, `/v1/references`, `/v1/short-fiction`, `/v1/adaptations`, `/v1/scripts`, `/v1/storyboards`, `/v1/films`, `/v1/worlds`, `/v1/translations`, `/v1/images`, `/v1/research`, `/v1/detection`, `/v1/schedules`. Các action dài tạo job chung; endpoint đọc/chỉnh nhỏ vẫn có version checks.

Các màn hình mở rộng: Work Inspector/Creative Methods, short workbench, Import Manager, Style/Analysis, Translation Manager, Script/Storyboard, Film Wizard/Flow/Player, Play HUD, Model services, Radar, Analytics, Scheduler, Logs và Doctor. FE dùng React Flow ở R6; editor dùng Tiptap thay textarea, nhưng domain action vẫn đảm bảo derived-state consistency.

## 18. SQLite và thư mục data cho toàn bộ tính năng

Bổ sung các bảng vào phần 5, dùng cùng `data/db/app.sqlite3`:

| Domain | Bảng/nhóm dữ liệu mở rộng |
|---|---|
| Work/harness | profiles, profile_versions, artifacts, artifact_revisions, work_lineage, episodes, action_events, action_receipts |
| Chat | sessions, messages, attachments, request_snapshots, session_work_bindings |
| Methods | methods, method_versions, method_documents, profile_methods, job_method_bindings |
| Longform | author_controls, chapter_briefs, chapter_plans, context_traces, story_states, facts, hooks, summaries |
| Materials | materials, material_segments, work_reference_bindings, retrieval_documents/FTS |
| Short | short_specs, short_stage_runs, short_delivery, sales_packages, revision_operations/checkpoints |
| Adaptation | canon_sources, canon_versions, style_guides, import_runs, import_chapter_progress |
| Script/storyboard | script_specs, scripts, storyboards, shots, shot_prompt_bindings |
| Film | film_specs, graph_revisions, nodes/choices/variables/endings, delivery_requirements/reports, player_runs |
| Play | worlds, world_runs, entities, edges, state_slots, turns, run_snapshots, turn_variants, presentations |
| Translation | translation_projects, source_segments, translated_segment_revisions, glossary_terms, translation_reviews |
| Visual | image_requests, image_assets, image_variants, selected_asset_bindings |
| Research/detection | research_runs, research_sources, radar_reports, detection_results |
| Operation | schedules, usage_counters, usage_records, notification_outbox, export_receipts, backup_manifests, migration_runs |

Không tạo tất cả bảng ngay tuần đầu. Migration theo giai đoạn/domain; ID và revision contracts được thống nhất ở R1 để tránh redesign nền tảng.

Thư mục data mở rộng:

```text
data/
  db/app.sqlite3
  assets/<work-id>/           Ảnh và file nhị phân có checksum
  imports/                   Bản sao nguồn gốc, file Skill/material nhập
  methods/                   SKILL.md + references do user import/chỉnh
  exports/<work-id>/          TXT/MD/EPUB/JSON/Ink/HTML packages
  backups/                   SQLite snapshot + immutable asset manifest
  logs/                      Rotated logs, che secrets
  cache/                     Projection/cache có thể rebuild
  tmp/                       Staging files
  secrets.enc
```

Nguồn text/prose/spec/graph/state chuẩn nằm trong DB; binary/assets/method documents nằm trong data với metadata/version/checksum trong DB. Không giữ hai nguồn chuẩn cùng lúc giữa SQLite và file Markdown. FTS/cache/export phải có source revision và cách rebuild.

Mọi cấu hình, lịch, quota, transcript và Skill do app quản lý cũng nằm trong data. Backend đọc đúng một data-root, khóa thao tác cùng Work và serialize write transaction ngắn. Binary inference/model của Ollama/LM Studio là tài nguyên của ứng dụng AI bên ngoài; chỉ import vào data nếu sau này người dùng yêu cầu app tự quản lý model weights.

## 19. Những phần bổ sung riêng cho WriteStoryApp

Các mục sau là thiết kế mới của dự án, không được ghi là chức năng InkOS đã có hoàn chỉnh:

| ID | Bổ sung | Giai đoạn |
|---|---|---|
| NEW01 | Desktop portable Win/Mac, Python sidecar, data-root cạnh app và vault portable | R0–R1 |
| NEW02 | Kiến trúc gói ngôn ngữ; gói `vi` làm trước và hoàn thiện xuyên UI/schema/method/length/retrieval/export: xưng hô, style profile, chuẩn hóa NFC/kiểu bỏ dấu, kiểm tra lớp từ và chính tả (§6.6). Gói ngôn ngữ khác sau MVP | R1–R6 |
| NEW03 | Tiptap, autosave, undo/redo và UI diff revision | R1–R2 |
| NEW04 | SQLite canonical transaction thay file-based truth, job checkpoint bền vững | R1–R2 |
| NEW05 | Expected revisions và conflict UI khi AI chạy đồng thời với sửa tay | R2 |
| NEW06 | CRUD preset thể loại/nền tảng để tái dùng metadata và phương pháp | R3 |
| NEW07 | Durable scheduler quota/timezone, kênh thông báo ngoài, tray/background opt-in (R7). `notification_outbox` + thông báo native đã có từ MVP (§23.2 #12) | R2/R7 |
| NEW08 | Signed installer/update, portable migration và export/import backup giữa Win/Mac | R7 |
| NEW09 | OCR PDF scan, embeddings khi lexical retrieval chưa đủ | Mở rộng sau đánh giá, không chặn hoàn thành parity nguồn |
| NEW10 | Can thiệp một phần chương và tự cascade nhiều chương sau có preview/approval | Mở rộng sau parity; source roadmap chưa hoàn tất |
| NEW11 | Custom executable agent plugin và export theo nền tảng | Mở rộng sau parity; source roadmap chưa hoàn tất |

Phạm vi parity nguồn bao gồm ma trận phần 15 và FL01–FL26. NEW09–NEW11 là backlog mở rộng được giữ lại nhưng chưa cam kết vào release parity. Cloud sync/tài khoản/server vẫn ngoài phạm vi đã chốt.

## 20. Lộ trình đầy đủ và ticket theo module

Ước lượng đề xuất cho một lập trình viên có kinh nghiệm làm tập trung: MVP khoảng 10–13 tuần; phạm vi rộng tương đương nguồn khoảng 33–45 tuần, tùy chất lượng AI/UX và mức kiểm thử provider. Đây không phải deadline hay số liệu năng suất đã đo. Phần 9 vẫn là lộ trình MVP; bảng này bổ sung phần còn lại.

| Release | Thời lượng | Nội dung và phụ thuộc | Điều kiện hoàn thành |
|---|---:|---|---|
| R0 | 1 tuần | Desktop spike, Python frozen, local token/port, data, Vietnamese editor | Máy sạch Win/Mac chạy được vertical slice mock |
| R1 | 2 tuần | Work/artifact/profile contracts, DB/migrations, library, editor, settings/vault | Dữ liệu bền, không mất khi restart, data-root thống nhất |
| R2 | 7–10 tuần | Jobs, scheduler đa truyện, longform pipeline liền mạch (§6.2), memory, review/revise/restore/delete/resync, cấu hình model (§7.1), export, các mục [Chặn MVP]/[MVP] của §23. Chat/action engine đầy đủ (CHT06–CHT11) chuyển sang R3 | 3 truyện × 20 chương song song đạt chỉ số §9 Giai đoạn 4; cancel/recovery/conflict ổn |
| R3 | 5–7 tuần | Short stages/revision, materials/skills, import/canon/fanfic/spinoff/style, forecast | Resume đúng operation/source, đủ delivery artifacts và lineage |
| R4 | 4–6 tuần | Translation/glossary, cover/image, research/radar, detection, mở rộng provider | Batch/segment/asset đúng nguồn; failure không làm mất kết quả |
| R5 | 5–7 tuần | Script/storyboard/spec, shot/prompt/asset, review/export | Source pinning và visual continuity, revisions kiểm tra được |
| R6 | 6–8 tuần | Film graph/delta/validation/player/exports và Play world/turn/variants/HUD/images | Reachability/evaluator đúng; turn rollback/restore nhất quán |
| R7 | 3–4 tuần | Scheduler/tray, notifications, CLI/TUI/interact parity, migration nguồn, signed release | Acceptance matrix đủ, installer/upgrade giữ nguyên data |

Thứ tự phụ thuộc: R0 → R1 → R2. R3/R4 cần contracts/job/retrieval của R2; R5 cần artifact/source binding/visual; R6 cần graph và revision nền; R7 tổng hợp và harden. Không mở toàn bộ UI menu chưa có use case chạy được.

Mỗi ticket trong backlog có mẫu:

```text
Feature ID / Flow ID:
Source evidence: path + entrypoint/function + snapshot commit
User outcome:
Inputs, source revisions, permissions:
Output artifact/data contract:
FE screen/API/domain job:
SQLite migration + files under data:
Cancellation/retry/checkpoint/conflict behavior:
Acceptance tests and reference sample:
Status: planned / implementing / source-reviewed / verified
```

Đăng ký 39 provider nguồn được lưu làm catalog tham khảo, không yêu cầu mua key/test tất cả trong MVP. Chốt protocol coverage và một provider từng nhóm cần dùng; provider chưa test phải hiển thị trạng thái chưa kiểm chứng. Không đoán model mới nhất hoặc bảo đảm model metadata nguồn vẫn đúng thời điểm phát hành.

## 21. Ma trận nghiệm thu phạm vi đầy đủ

| Nhóm/flow | Kiểm tra bắt buộc |
|---|---|
| WRK/CHT, FL01–03 | Restart/single-instance/data permission, schema migration, bound session, typed action policy và completion receipt |
| LNG/MEM, FL04–05 | Sequential dependencies, cổng chặn khi state không hợp lệ, handoff/seam check, vòng sửa có giới hạn, empty/truncated output, length drift (đếm âm tiết), invalid state delta, review unavailable, per-chapter checkpoint, chỉ số liền mạch §9 Giai đoạn 4 |
| Đa truyện, §4.2 | 3–5 truyện song song không truyện nào bị bỏ đói, khóa xếp hàng, 429/`Retry-After`, hết ngân sách, một truyện bị chặn không ảnh hưởng truyện khác, không `database is locked` |
| EDT, FL06–07 | Outside-scope unchanged, exact source evidence, expected revision conflict, restore/delete/rename và derived-state stale |
| Forecast, FL08 | Fingerprint stale, selected branch chỉ là plan, không sửa canonical tables |
| Material/import, FL09–10 | URL/file/text-PDF, source provenance, chapter split preview, resume after crash và không pha nguồn khác |
| Adaptation, FL11–12 | Parent/source revision pinning, boundaries của fanfic/series, style guide và lineage |
| Short, FL13–14 | Missing chapters, stage-only không rewrite prose, manuscript hash stale, pending revision ID/resume và package retry |
| Script/storyboard, FL15–16 | Spec/source persist trước, prompt không đồng nghĩa image, shot binding và export exact revision |
| Film/player, FL17–18 | Invalid delta, broken/gated links, variable type, endings, bounded path enumeration và JSON/Ink/HTML consistency |
| Play, FL19–20 | Seed usable graph, mutation validation, turn atomicity, scene-only vs replay, variants và image không tăng turn |
| Translation, FL21 | Duplicate/missing segment, glossary consistency, resume pending, review/version/export Unicode |
| Visual, FL22 | Binary tồn tại, correct scene/title/source, cancellation và variants manifest |
| Research/detection, FL23 | Không giả sources, partial failure, result provenance và vendor uncertainty |
| Scheduler, FL24 | No overlap, persisted quota/timezone, pause/sleep/restart và notification failure sau commit |
| Export/backup, FL25 | Reviewed/exported revision cùng bản, asset checksums, WAL snapshot, restore rollback và no recursive backup |
| Settings/methods, FL26 | Protocol/provider capability, secret không vào log, static Skill import, action scope và pinned config |
| Full Win/Mac release | No Python/Node installed, Unicode paths, writable portable data, bundle signing, key vault và upgrade không mất truyện |

Definition of done cho parity: mỗi feature ID phần 15 có use case/backend contract, UI hoặc kênh điều khiển phù hợp, migration cần thiết và test có ý nghĩa; mọi flow có kịch bản success/failure/cancel/recovery tương ứng. Chỉ có code/API declaration là chưa đủ để đánh dấu verified.

## 22. Quy ước cấu trúc FE, BE và AI cập nhật

Yêu cầu mới: mỗi tầng có một thư mục riêng, có nguồn chính thức để đối chiếu. Áp dụng cấu trúc trong phần 8 và 17, với bản thiết kế chi tiết tại [folder-architecture.vi.md](./folder-architecture.vi.md).

- **FE:** React/TypeScript/Vite; `app`, `features`, `shared`; UI tổ chức theo tính năng. API types sinh từ BE, editor buffer và UI state không thay thế dữ liệu chuẩn trong SQLite.
- **BE:** FastAPI package Python với `src` layout; module nghiệp vụ sở hữu use cases và revision validation; hạ tầng sở hữu DB/files/vault. Jobs chạy bền vững ngoài request lifecycle.
- **AI:** package Python riêng với `src` layout; contracts, ports, providers, context, methods, workflows và evaluators. AI trả bản đề xuất; BE quản lý lưu/accept/cancel/recovery.
- **Desktop:** Tauri tách khỏi React source; bootstrap Python, quản lý cổng/token và data-root tuyệt đối. FE dist là tài nguyên build của shell.
- **Dependencies:** uv workspace cho BE/AI, pnpm workspace cho FE/desktop; mỗi hệ có lockfile riêng ở vị trí đã thiết kế. AI không phụ thuộc ngược BE; FE không chứa provider key/prompt orchestration.
- **Data:** một `data/` chung như đã chốt; không thêm DB hoặc data-root riêng cho từng tầng. Source folders không phải layout bắt buộc của runtime portable.
- **Thực hiện:** dựng tối thiểu ở R0, nền dữ liệu/contracts ở R1, jobs/pipeline ở R2, mở rộng theo R3–R7. Giữ nguyên backlog 146 hạng mục và 26 flow.

Nguồn tham chiếu gồm React, Vite, FastAPI, PyPA, uv, pnpm, Tauri, SQLAlchemy, Alembic, SQLite và PEP 8. Không có một quy chuẩn duy nhất bắt buộc toàn bộ cây FE/BE/AI; tên `features/modules/workflows` và ranh giới nghiệp vụ là quyết định kiến trúc dự án. Các quy ước được phân biệt với hướng dẫn framework trong tài liệu cấu trúc.

**Trạng thái đối chiếu (02/10/2026):** source InkOS được kiểm tra tại máy. Các giả định kỹ thuật chính đã được kiểm chứng trên trang chính thức (Tauri, PyInstaller, SQLite, FastAPI, SQLAlchemy, uv, python.org, cryptography, OWASP, Apple) và FTS5 tiếng Việt đã chạy thử; kết quả và URL tại [review-and-optimization.vi.md §7](./review-and-optimization.vi.md). Còn chưa xác nhận: tên khóa `fixedRuntime` trong schema Tauri, trang uvicorn.org, hành vi IME tiếng Việt trên Tiptap (phải test ở R0).

## 23. Bổ sung thiết kế còn thiếu (rà soát BE/FE/AI 02/10/2026)

Rà soát lại BE, FE, AI theo hai yêu cầu cốt lõi (đa truyện, chương liền mạch) và các màn hình trong [ui-design.vi.md](./ui-design.vi.md). Mức ưu tiên: **[Chặn MVP]** phải chốt trước khi code R2; **[MVP]** làm trong R1–R2; **[Sau]** sau MVP.

### 23.1 Hợp đồng dùng chung BE ↔ AI ↔ FE

**A. Schema trạng thái truyện `StoryState` và `StateDelta` [Chặn MVP]**

Pipeline §6.2 (settle, validate, seam, handoff) dựa trên state nhưng trước đây chưa định nghĩa. Bản v1:

```text
StoryState (snapshot sau chương N)
  chapter_no
  story_time        nhãn mốc thời gian truyện + số thứ tự để so sánh trước/sau
  characters[]      id, status (alive/dead/missing/unknown), location_id, condition,
                    goals, knowledge[] (fact_id nhân vật đã biết), inventory[], in_last_scene
  relationships[]   a, b, kind, intensity, since_chapter   (nguồn cho quy tắc xưng hô)
  facts[]           id, subject, predicate, object, valid_from, valid_until, evidence
  hooks[]           id, status, opened_at, due_by, last_advanced, payoff_plan
  events[]          story_event_id, status
  locations[]       id, name, aliases
```

`StateDelta` là danh sách thao tác có kiểu: `character.add`, `character.update`, `character.move`, `character.learn`, `relationship.set`, `address.change`, `location.add`, `fact.add`, `fact.close`, `hook.open|advance|resolve|defer` (`resolve` có cờ `as_superseded`), `event.done|move|drop`, `time.advance` (có cờ `in_flashback`). Thao tác mô tả điều xảy ra trong văn bản bắt buộc `evidence` (`paragraph_id` + trích ngắn); thao tác kế hoạch không có đoạn văn tương ứng (`event.move`, `event.drop`, `hook.defer`) dùng `reason` thay cho `evidence`. Chi tiết trường và luật V01–V15: [F09 ai.md](./features/F09-trang-thai-va-bo-nho/ai.md).

Bảng `facts`, `hooks`, `timeline`, `story_events` là **sổ cái** đánh chỉ mục theo chương, được ghi trong cùng transaction và từ cùng delta với snapshot `story_states`; `story_states` là **lịch sử** bất biến (trạng thái sau chương N). Bất biến cần test: chiếu sổ cái tại chương N bằng facts/hooks trong snapshot N. Tác giả sửa Story Bible được chuyển thành một `StateDelta` nguồn `user`, không ghi thẳng sổ cái. Trường `hooks[].due_by` trong JSON là bản chiếu của cột `hooks.due_by_chapter`. Validator xác định: ID tồn tại; nhân vật đã chết không di chuyển/hành động; thời gian không lùi trừ đoạn hồi tưởng được đánh dấu; hook đã đóng không được advance; nhân vật không dùng thông tin chưa `learn` (lộ bí mật sớm là lỗi liền mạch hay gặp). Snapshot lưu đầy đủ mỗi chương (nhỏ, rollback đơn giản); chỉ chuyển sang delta + snapshot định kỳ nếu đo thấy lớn.

**B. Đoạn văn có ID [Chặn MVP]**

Sửa cục bộ, trích bằng chứng, diff theo đoạn và nhận từng đoạn đều cần neo ổn định. Mỗi đoạn có `paragraph_id` (Tiptap UniqueID ở FE, BE giữ nguyên trong plain-text projection). AI nhận văn bản dạng `[p:abc123] nội dung…`; bước sửa trả `ops: [{paragraph_id, action: replace | insert_after | delete, text}]`; BE áp ops, kiểm tra đoạn ngoài phạm vi không đổi, sinh ID mới cho đoạn chèn.

**C. Luồng sự kiện toàn cục [Chặn MVP]**

Trước đây chỉ có `/v1/jobs/{id}/events`, không đủ cho Phòng viết và chỉ báo "N truyện đang chạy". Thêm `GET /v1/events?since=<seq>&works=` (SSE, `Last-Event-ID`). Envelope có version:

```text
{v, seq, ts, type, work_id?, job_id?, chapter_no?, payload}
type: job.queued | job.state | job.step | token.delta | stream.tail | candidate.ready
      | candidate.updated | finding.added | finding.updated | chapter.committed
      | work.continuity | queue.changed | provider.status | usage.updated | vault.status
      | notification.created | backend.notice
```

`stream.tail` mang 1–2 dòng cuối của bản nháp đang viết (throttle khoảng 4 lần/giây) cho Phòng viết, gửi cho mọi client; `token.delta` chỉ gửi cho truyện trong `works=`, không có `seq` riêng mà dùng watermark + `offset` theo `candidate_id`. Con trỏ `since` cũ hơn thời hạn giữ `job_events` → `backend.notice` kind `replay_gap`, FE tải lại trạng thái qua REST.

`token.delta` được gộp 50–100 ms và chỉ gửi cho truyện client đăng ký trong `works=`; Phòng viết nhận `job.step` và đoạn đuôi rút gọn. Các event khác lưu `job_events` để replay; `token.delta` không lưu lâu, bản nháp được giữ qua checkpoint của candidate. FE dùng một kết nối duy nhất và phân phối theo `work_id`.

**D. Hợp đồng lỗi API [MVP]**

Mọi lỗi trả `{code, message, detail, retryable, action}` theo tinh thần problem details (RFC 9457); `message` lấy từ gói ngôn ngữ. Mã tối thiểu: `REVISION_CONFLICT` (409), `WORK_BLOCKED`, `WORK_BUSY_QUEUED`, `CHAPTER_RANGE_CONFLICT`, `VAULT_LOCKED`, `PROVIDER_AUTH`, `PROVIDER_UNREACHABLE`, `PROVIDER_RATE_LIMIT`, `PROVIDER_REFUSAL`, `OUTPUT_TRUNCATED`, `STRUCTURED_OUTPUT_INVALID`, `BUDGET_EXCEEDED`, `VALIDATION`. FE ánh xạ `code` → thông báo + nút hành động; Phòng viết hiển thị đúng lý do chờ/chặn.

`WORK_BUSY_QUEUED`, `VAULT_LOCKED`, `PROVIDER_UNREACHABLE`, `PROVIDER_RATE_LIMIT`, `BUDGET_EXCEEDED` vừa là mã lỗi (chỉ trả HTTP khi lời gọi đồng bộ cần tài nguyên đó ngay) vừa là giá trị `jobs.wait_reason` khi job nền chuyển `waiting_slot` – job không bị fail vì các lý do này. BE luôn trả `message` dự phòng; FE ưu tiên chuỗi i18n theo `code`.

### 23.2 BE

| # | Còn thiếu | Đề xuất | Mức |
|---|---|---|---|
| 1 | Nơi lưu bản nháp AI | Bảng `chapter_candidates` (§5); `/accept` đọc từ đây, cho nhận cả chương hoặc từng `paragraph_id`; candidate bị từ chối/superseded được dọn theo hạn | Chặn MVP |
| 2 | Autosave tạo quá nhiều revision | Autosave ghi `chapter_working_copy` (một bản/chương, ghi đè, kèm base revision). Revision chỉ tạo khi: rời chương, nhàn ≥ 2 phút có thay đổi, trước/sau nhận AI, Ctrl+S, trước restore | MVP |
| 3 | Sửa tay khi truyện đang auto-write | Chương committed mới nhất (N-1) là nền của chương N đang viết → editor read-only, nút "Tạm dừng để sửa" (batch dừng sau bước hiện tại, candidate N bị hủy vì base đổi). Sửa chương cũ hơn → `stale_from(K)`, batch dừng sau chương đang chạy | Chặn MVP |
| 4 | Chèn/xóa/đổi thứ tự chương giữa truyện | Không cho khi truyện đang chạy. Khi dừng: tạo `stale_from(K)` với K nhỏ nhất bị ảnh hưởng, yêu cầu resync tuần tự trước khi viết tiếp | MVP |
| 5 | API cho các màn hình | Danh sách bổ sung tại §7 (chapters, working copy, candidates, trace, handoff, state, Story Bible CRUD, findings, search, estimate, vault, storage) | MVP |
| 6 | Ước tính chi phí trước khi chạy | `autowrite/estimate`: token ước tính theo usage trung bình các chương trước của truyện (hoặc mặc định theo độ dài mục tiêu), giá từ `provider_models`, trả khoảng min–max và thời gian ước tính; yêu cầu xác nhận khi vượt ngân sách | MVP |
| 7 | Vault khóa sau khởi động lại | Job cần key khi vault khóa → `waiting_slot` lý do `VAULT_LOCKED`; mở vault thì scheduler chạy tiếp, không cần tạo lại job | MVP |
| 8 | Mất mạng / provider không phản hồi | Lỗi kết nối không làm fail job: `waiting_slot` lý do `PROVIDER_UNREACHABLE`, backoff tăng dần tới tối đa 5 phút; Phòng viết hiển thị đếm ngược | MVP |
| 9 | Máy ngủ khi đang auto-write | Tùy chọn "giữ máy thức khi đang viết" do Rust thực hiện (Windows `SetThreadExecutionState`, macOS IOPMAssertion); khi máy thức lại, request treo hết timeout và chạy lại từ checkpoint | MVP |
| 10 | Dữ liệu phình to | Chính sách giữ: mọi revision committed; candidate bị từ chối 30 ngày; `job_events` 90 ngày; trace chi tiết theo dung lượng tối đa; xoay vòng log. Endpoint `storage` báo dung lượng và dọn dẹp | MVP |
| 11 | Ghi request/response AI để debug | Tùy chọn (mặc định tắt) lưu prompt đã render và response vào `data/logs/ai/` theo job/step, che secret, giới hạn dung lượng | MVP |
| 12 | Thông báo hệ thống | Thông báo native qua Tauri notification plugin khi chương bị chặn, batch xong, provider lỗi kéo dài; bật/tắt trong Cài đặt. Telegram/webhook giữ ở R7 | MVP |
| 13 | Test adapter provider | Fixture ghi/phát lại response; mock provider mô phỏng độ trễ, 429 + `Retry-After`, 5xx, refusal, cắt `max_tokens`, JSON hỏng, mất kết nối giữa stream | MVP |
| 14 | Hai bảng findings trùng nhau | Gộp `review_findings` + `continuity_findings` thành `findings` (§5) | MVP |

### 23.3 AI

| # | Còn thiếu | Đề xuất | Mức |
|---|---|---|---|
| 1 | Ngữ cảnh cho truyện rất dài (200+ chương) | Tóm tắt phân tầng trong bảng `summaries`: tóm tắt chương (sau mỗi chương), tóm tắt arc/quyển (khi đóng arc hoặc mỗi 10–20 chương), synopsis toàn truyện (cập nhật mỗi arc). Composer: synopsis + tóm tắt arc hiện tại + K tóm tắt chương gần nhất + kết quả tìm kiếm + handoff. Kích thước context ổn định dù truyện dài bao nhiêu | Chặn MVP |
| 2 | Structured output không ổn định | Settle/validate/seam/review dùng structured outputs hoặc tool-use có JSON schema khi `capabilities.structured_outputs`; nếu không có thì JSON mode + parse + một lần yêu cầu sửa; Pydantic validate; vẫn lỗi → step fail `STRUCTURED_OUTPUT_INVALID` | Chặn MVP |
| 3 | Model từ chối / output bị cắt | Phân biệt `stop_reason`: **refusal** (bạo lực, nội dung nhạy cảm vốn có trong kiếm hiệp, trinh thám…) → không retry lặp, chuyển `waiting_user` kèm gợi ý chỉnh chỉ dẫn hoặc đổi model; **max_tokens** → viết tiếp từ điểm dừng (tối đa 2 lần) rồi ghép, ghi trong trace | Chặn MVP |
| 4 | Đếm token trước khi gửi | Anthropic: endpoint count tokens khi cần chính xác; provider khác: ước lượng bằng tỷ lệ token/âm tiết đo được theo model (lưu trong `provider_models`) + biên an toàn 15%; vượt ngân sách thì nén lớp compressible, không cắt phần bảo vệ | MVP |
| 5 | Nhịp truyện, kết thúc sớm | Planner nhận "ngân sách chương": số sự kiện còn lại / số chương còn lại tới mục tiêu; cảnh báo khi dồn hoặc kéo dài; không cho kết thúc truyện trước chương mục tiêu nếu tác giả chưa cho phép | MVP |
| 6 | Ai điều chỉnh dàn ý động | Bước "xét lại dàn ý" mỗi K chương (mặc định 10) hoặc khi ≥ 2 sự kiện bị `moved`: đề xuất sửa `story_events`; chế độ `review_*` cần tác giả duyệt; chế độ `auto` chỉ áp khi không đụng sự kiện tác giả đã khóa | MVP |
| 7 | Giọng văn trôi theo thời gian | Lớp 2 prompt chứa 1–2 đoạn mẫu giọng văn (của tác giả hoặc chương đã duyệt), chọn cố định để không phá cache; cảnh báo khi đổi model Viết giữa truyện | MVP |
| 8 | Quản lý prompt | Template Jinja2 sandbox + manifest id/version/checksum trong gói ngôn ngữ; snapshot test cho prompt đã render; prompt version ghi vào `job_steps` | MVP |
| 9 | Bộ đánh giá khi đổi prompt/model | Truyện mẫu + kiểm tra xác định (§9 Giai đoạn 4) + LLM-judge với rubric tiếng Việt; chạy khi đổi prompt hoặc model, lưu kết quả để so sánh | MVP (bản nhỏ) |
| 10 | Model dự phòng | Tùy chọn model dự phòng theo vai trò khi model chính lỗi kéo dài (không áp cho 429 ngắn); ghi rõ trong trace. Mặc định tắt vì đổi giọng văn và mất cache | Sau |

### 23.4 FE

| # | Còn thiếu | Đề xuất | Mức |
|---|---|---|---|
| 1 | Lần chạy đầu | Onboarding: (macOS) chọn data-root → đặt mật khẩu vault hoặc chọn dùng key theo phiên → thêm provider + kiểm tra lấy danh sách model → tạo truyện đầu tiên hoặc truyện mẫu | Chặn MVP |
| 2 | Trạng thái backend | Màn "đang khởi động"; "backend dừng bất ngờ – khởi động lại"; banner mất kết nối SSE và tự nối lại từ `seq` | Chặn MVP |
| 3 | Chương đang làm nền | Editor hiện chương N-1 read-only khi chương N đang viết, kèm nút "Tạm dừng để sửa" (§23.2 #3) | Chặn MVP |
| 4 | Mở khóa vault | Hộp thoại nhập mật khẩu khi có job cần key; badge "vault đang khóa" trên header | MVP |
| 5 | Hộp thoại auto-write | Số chương / đến chương, chế độ, ưu tiên; hiện ước tính chi phí và thời gian; cảnh báo vượt ngân sách | MVP |
| 6 | Xuất truyện | Hộp thoại export: TXT/Markdown/EPUB, khoảng chương, metadata, có/không tiêu đề chương. Import có xem trước tách chương ở R3 | MVP (export) |
| 7 | Trạng thái rỗng/lỗi/đang tải | Mẫu thống nhất: skeleton; rỗng kèm hướng dẫn; lỗi theo hợp đồng §23.1.D kèm nút hành động | MVP |
| 8 | Chế độ tập trung | Ẩn hai panel, chỉ editor và font đọc; Ctrl+Shift+F | MVP |
| 9 | Trung tâm thông báo | Danh sách sự kiện quan trọng (chương bị chặn, batch xong, lỗi provider), bấm vào mở đúng chỗ xử lý | MVP |
| 10 | Trang Lưu trữ | Dung lượng DB/asset/log/backup, dọn dẹp theo §23.2 #10 | MVP |
| 11 | Sửa handoff và state | Tab "Nối" cho sửa `ending_state` trước khi viết chương sau; trang Story Bible xem `StoryState` theo từng chương (thanh trượt chương) | MVP |
| 12 | Test FE | Playwright chạy FE với mock backend cho luồng chính (tạo truyện → auto-write → bị chặn → sửa → chạy tiếp); checklist test IME thủ công | MVP |

### 23.5 Thứ tự chốt trước khi code R2

1. Schema `StoryState`/`StateDelta` và `paragraph_id` (23.1.A, 23.1.B): mọi bước AI và bảng dữ liệu phụ thuộc vào đây.
2. Envelope event toàn cục và hợp đồng lỗi (23.1.C, 23.1.D): FE và BE làm song song được khi hai hợp đồng này cố định.
3. Candidate + working copy + quy tắc sửa tay khi đang auto-write (23.2 #1–#3, 23.4 #3).
4. Tóm tắt phân tầng, structured output, xử lý refusal/cắt output (23.3 #1–#3).
5. Onboarding và trạng thái backend (23.4 #1–#2).

Mỗi mục trên trở thành ticket theo mẫu §20 trước khi bắt đầu R2.

## 24. Quyết định đồng bộ sau khi chia tính năng (02/10/2026)

Khi tách tài liệu thành [features/](./features/README.md) và [tests/](./tests/README.md), các file tính năng phát hiện mâu thuẫn giữa các phần của Plan/Arch/UI. Bảng dưới là quyết định chốt; khi file tính năng còn ghi khác, bảng này thắng và file đó cần sửa theo.

| ID | Vấn đề | Quyết định |
|---|---|---|
| D1 | FL25 ghi backup API, §5 ưu tiên `VACUUM INTO` | `VACUUM INTO` ra file tạm rồi rename (FL25 đã sửa) |
| D2 | `story_states` (§5) vs `state_snapshots` (§18) | Dùng `story_states` (§18 đã sửa) |
| D3 | `usage_counters` vs `quota_counters`; ngân sách đặt trong `provider_limits` | `usage_records` + `usage_counters`; ngân sách app trong `settings`, ngân sách truyện trong `works`; `provider_limits` chỉ chứa giới hạn và cooldown (§5 đã sửa) |
| D4 | Hai endpoint accept | Chỉ `POST /v1/candidates/{id}/accept`; bỏ `/v1/jobs/{id}/accept` (§7 đã sửa) |
| D5 | Thông báo native MVP vs outbox R7 | `notification_outbox` + thông báo native trong MVP; kênh ngoài ở R7 (NEW07 đã sửa) |
| D6 | `state_applied`, trạng thái chương/tác phẩm chưa có cột | `chapters.status`, `chapters.state_applied`; `works.status`, `works.continuity_status`, `works.continuity_chapter_no`, `works.continuity_reason` (§5 đã sửa) |
| D7 | Loại và mức độ findings chưa đủ | Loại mở rộng như §5. Mức mặc định: fact/timeline/name/seam/pov/address (sai xưng hô không có sự kiện đổi) = **blocker**; hook quá hạn, độ dài lệch quá khoảng mục tiêu = **major**; slop/spelling/register/tone_mark_style/punctuation/craft = **minor** (chỉ cảnh báo). Tác giả chỉnh mức trong `style_profile` |
| D8 | `waiting_user` lẫn với bị chặn | Job `waiting_user` có `wait_reason`: `review_required` (chế độ review_each/k, hoặc job viết đơn lẻ từ AI panel) hoặc `repair_exhausted` (chỉ trường hợp này đặt `works.continuity_status = blocked_needs_resync`). Trạng thái job `blocked` chỉ dùng cho job đang xếp hàng của truyện bị chặn |
| D9 | Mã lỗi hay lý do chờ | Xem §23.1.D: các mã liên quan tài nguyên đồng thời là `jobs.wait_reason`; job nền không fail vì chúng |
| D10 | Phòng viết không có event mang đuôi văn bản | Thêm `stream.tail`, cùng `candidate.updated`, `finding.updated`, `notification.created`; `/v1/jobs/{id}/events` là bộ lọc của luồng chung (§23.1.C đã sửa) |
| D11 | Job viết một chương đơn lẻ tự commit hay chờ | Từ AI panel: dừng ở `waiting_user` (`review_required`) chờ tác giả nhận. Trong auto-write chế độ `auto`: tự commit khi qua mọi cổng |
| D12 | Sửa tay chính chương mới nhất | Coi là `stale_from(N)`: chỉ settle lại chương N và tạo handoff mới trước khi viết N+1 |
| D13 | Ghim cấu hình theo batch hay theo job | Theo từng job chương (FL05 đã sửa) |
| D14 | Ai sở hữu retry | AI `policies/retry.py`: phân loại lỗi, backoff cho một lời gọi. BE `infrastructure/ai/limits.py`: semaphore, token bucket, cooldown chung theo `Retry-After`, AI gọi qua `ProviderLimiterPort`. BE `jobs/`: `waiting_slot`, resume, checkpoint. Hết retry: 429 → `waiting_slot` chờ cooldown; 5xx → job `failed` (retryable) và auto-write tạm dừng truyện đó; cắt `max_tokens` sau 2 lần viết tiếp → giữ candidate, finding `length` major, `waiting_user`; output rỗng → `OUTPUT_EMPTY`, retry một lần rồi fail |
| D15 | Job nào phải giữ khóa truyện | `foundation`, `write`, `revise`, `resync`, `import`, `rollback`. Job `review`, `export`, `backup` không giữ khóa truyện |
| D16 | Vai trò cho bước nền truyện | Dùng vai trò `planner`; không thêm vai trò mới trong MVP |
| D17 | Effort mặc định áp cho đâu | Áp cho mọi vai trò chưa đặt effort riêng (theo §7.1); sửa mô tả UI §5.6.1 cho khớp |
| D18 | Nguồn của revision | `chapter_revisions.source`: `manual`, `auto_snapshot`, `agent`, `revise`, `restore`, `import` |
| D19 | Định dạng ID | UUIDv7 cho mọi bảng; `paragraph_id` 8 ký tự `[a-z0-9]` duy nhất trong chương |
| D20 | Data-root Windows khi cạnh `.exe` không ghi được; WebView2 cho bản zip | Con trỏ `%APPDATA%\WriteStoryApp\data-root.json` chỉ dùng trong trường hợp đó. Bản zip portable: WebView2 sẵn trên máy hoặc `fixedRuntime`; `offlineInstaller` chỉ cho installer |
| D21 | Gợi ý data-root macOS | `~/Library/Application Support/WriteStoryApp/data` |
| D22 | Spawn backend | Rust spawn trực tiếp file thực thi trong thư mục PyInstaller onedir nằm ở `bundle.resources`; không dùng `externalBin`. Ghi ADR ở R0 |
| D23 | Mock provider phải vào được bản đóng gói spike | Đặt ở `ai/src/writestory_ai/providers/mock.py`; fixture test re-export |
| D24 | Khóa data-root | Hai lớp: Rust giữ `data/.instance.lock` (single-instance), Python giữ `data/db/.backend.lock` |
| D25 | Bảng tìm kiếm | Dùng chung `search_documents` + `search_fts` (+ `search_trigram`) cho chương, Story Bible và sau này materials (R3); không tạo bảng FTS riêng từng loại |
| D26 | Địa điểm, tuyến truyện | MVP không có bảng `locations` (đọc từ `StoryState.locations`); thêm `story_events.storyline` cho hàng timeline |
| D27 | Nhiều provider | Cho nhiều provider; UI hiện bộ chuyển provider khi có hơn một |
| D28 | Công tắc ưu tiên context 1M | Chỉ có tác dụng khi `provider_models` khai báo biến thể context dài; nếu model đã báo `max_input_tokens` đủ lớn thì công tắc bị ẩn |
| D29 | `PUT /v1/chapters/{id}` và snapshot | `PUT` dùng cho tiêu đề và thay toàn văn (có `expected_revision`); `POST …/snapshot` chốt working copy thành revision |
| D30 | Cây chương và khung workspace chưa có chủ | Thuộc F07 (cây chương cơ bản, khung 3 cột) |
| D31 | Preset thể loại cần ở R1 nhưng gói `vi` ở R2 | R1 tạo sẵn `languages/vi/genres.json` tối giản; F08 hoàn thiện ở R2 |
| D32 | API còn thiếu (vault, onboarding, provider CRUD, shutdown, concurrency, hàng đợi, backup list/restore) | Lấy theo mục "Tên mới đề xuất" của F00–F14 khi dựng OpenAPI ở R1; OpenAPI là nguồn chuẩn, §7 chỉ là danh sách khởi điểm |

| D33 | Cột lưu chương bị chặn/stale: `stale_from_chapter` (F05) vs `continuity_chapter_no` (F11) | `works.continuity_chapter_no` + `works.continuity_reason` (JSON), dùng chung cho `blocked_needs_resync` và `stale_from` |
| D34 | Sổ cái facts/hooks vs snapshot | Sổ cái + lịch sử như §23.1.A (đã bổ sung) |
| D35 | StateDelta thiếu thao tác thêm nhân vật/địa điểm, `superseded`; `evidence` bắt buộc cho thao tác kế hoạch | Thêm `character.add`, `location.add`, `hook.resolve.as_superseded`; `event.move/drop`, `hook.defer` dùng `reason` (§23.1.A đã sửa) |
| D36 | `hooks.due_by_chapter` vs `StoryState.hooks[].due_by` | Giữ cả hai: cột DB `due_by_chapter`, JSON `due_by` là bản chiếu |
| D37 | Cụm sáo "sửa cục bộ" vs vòng sửa chỉ cho blocker | Cụm sáo là `minor`, không kích hoạt vòng sửa (§6.6 đã sửa) |
| D38 | Nơi đặt prompt và manifest | Prompt phụ thuộc ngôn ngữ và manifest nằm trong `ai/src/writestory_ai/languages/<lang>/prompts/`; `ai/.../prompts/` chỉ giữ phần dùng chung không phụ thuộc ngôn ngữ (nếu có) |
| D39 | "Chấp nhận kèm ghi chú" vs không commit thiếu state hợp lệ | Ghi chú chỉ được bỏ qua finding từ LLM (review/seam/LLM-validator); lỗi của validator xác định (V01–V15) và lỗi schema không bao giờ được bỏ qua |
| D40 | Cột `tokens_per_syllable` gắn với tiếng Việt | Giữ tên trong MVP; khi thêm gói ngôn ngữ thứ hai đổi thành `tokens_per_length_unit` kèm `length_unit` của gói |
| D41 | Phòng viết hiển thị 6 bước, pipeline có 11 bước | Ánh xạ hiển thị theo [F10 fe.md](./features/F10-viet-chuong-lien-mach/fe.md); dữ liệu event vẫn dùng tên bước đầy đủ |
| D42 | Banner bị chặn đặt ở `continuity/` hay `workspace/` | Component ở `fe/src/features/continuity/`, được `workspace/` (F07) lắp vào |
| D43 | Cổng vào chương trong Review §4.2 lỏng hơn Plan §6.2 | Theo Plan §6.2: `continuity_status = ok` (chặn cả `stale_from`) |
| D44 | Xác định người nói/người nghe cho kiểm tra xưng hô | Heuristic xác định (không gọi LLM) theo [F08 ai.md](./features/F08-goi-ngon-ngu-vi/ai.md): độ tin cậy high+high → blocker; có medium → major kèm `needs_confirmation` để reviewer xác nhận. Đo tỷ lệ báo nhầm trên truyện mẫu ở R2 |
| D45 | Lỗi hỏi/ngã giữa hai âm tiết đều hợp lệ ("dể dàng", "sữa chữa") | Từ điển âm tiết không bắt được; MVP chỉ cảnh báo Telex sót và âm tiết không hợp lệ, cần từ điển từ ghép/bigram (sau MVP) |

Tên mới mà các file tính năng đề xuất (bảng, cột, endpoint, mã lỗi, module) được chấp nhận làm tên làm việc. Khi dựng skeleton R1, gom vào migration và OpenAPI; tên nào trùng ý nghĩa giữa hai tính năng thì chọn một và sửa file còn lại.
