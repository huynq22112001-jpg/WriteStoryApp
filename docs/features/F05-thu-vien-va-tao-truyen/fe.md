# F05 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/` | Thư viện (UI §5.1) | Search params có type: `?view=grid\|table&q=&genre=&status=&sort=` |
| `/new` | Wizard tạo truyện (UI §5.7) | `?workId=&step=` để mở lại nháp; không có `workId` = bắt đầu mới |
| `/works/$workId` | Workspace | Chỉ điều hướng tới (F07/F10/F11 sở hữu); gọi `POST /v1/works/{id}/open` khi vào |

## Component

```text
fe/src/features/library/
  pages/LibraryPage.tsx
  pages/NewWorkWizardPage.tsx
  components/LibraryToolbar.tsx        Tìm (Ctrl+K mở palette chung), Thể loại ▾, Trạng thái ▾, [▦|☰], [+ Truyện]
  components/WorkGrid.tsx              Lưới card ảo hóa theo hàng (TanStack Virtual)
  components/WorkTable.tsx             Bảng ảo hóa
  components/WorkCard.tsx
  components/WorkStatusBadge.tsx
  components/WorkActionsMenu.tsx       Mở, Đổi tên, Lưu trữ, Xóa
  components/wizard/WizardStepper.tsx
  components/wizard/BasicsStep.tsx         Ngôn ngữ + thể loại + style profile
  components/wizard/BriefStep.tsx
  components/wizard/WritingConfigStep.tsx
  components/wizard/ReviewCreateStep.tsx
  hooks/useWorksInfinite.ts, useWorkDraft.ts, useLibraryLiveUpdates.ts
  api/works.ts, api/languages.ts
  schemas/wizard.ts                    zod 4 cho từng bước
  index.ts                             Export WorkStatusBadge cho Phòng viết/header
```

Bước 3–5 nhúng component public của `features/story_bible` (F06): `FoundationStep`, `AddressRulesStep`, `EventOutlineStep`.

| Component | Trách nhiệm |
|---|---|
| `LibraryPage` | Lấy danh sách bằng `useInfiniteQuery`, chọn lưới/bảng, render trạng thái rỗng/lỗi/tải |
| `WorkGrid` | Ảo hóa theo hàng; số cột tính từ độ rộng container (ResizeObserver); card cao cố định để ước lượng kích thước |
| `WorkCard` | Bìa (hoặc placeholder chữ cái đầu), tiêu đề, "Ch {committed}/{target}", `WorkStatusBadge`, chi phí (hoặc "—") |
| `WorkTable` | Cột: Tên, Thể loại, Chương, Trạng thái, Liền mạch, Cập nhật, Mở gần nhất; sắp xếp theo cột |
| `WorkStatusBadge` | Render `badge.kind` + `label_key` + `params` từ BE; luôn có icon + chữ (UI §8); tooltip lý do chờ |
| `WizardStepper` | 7 bước: Cơ bản → Brief → Nền truyện → Xưng hô → Dàn ý sự kiện → Cấu hình viết → Tạo; đánh dấu bước đã xong; cho quay lại |
| `BasicsStep` | Tên truyện, Ngôn ngữ (ô chọn chỉ có "Tiếng Việt"), Thể loại (preset + "Khác…"), style profile: Hán Việt/cân bằng/thuần Việt, kiểu thoại (gạch đầu dòng `–`/`—` hoặc ngoặc kép), kiểu bỏ dấu (`hoà`/`hòa`), cụm sáo cấm (tag input), giọng văn, 0–2 đoạn mẫu |
| `BriefStep` | Brief (textarea, đếm âm tiết hiển thị), số chương mục tiêu, gợi ý nội dung brief theo thể loại |
| `WritingConfigStep` | Độ dài chương min–max (âm tiết), chế độ auto-write mặc định + K, vòng sửa tối đa, ngân sách $/ngày và token/ngày của truyện (trống = theo app), bảng vai trò ghi đè (`RoleTable` của F04 với `workId`) |
| `ReviewCreateStep` | Tóm tắt các bước, danh sách thiếu (từ `detail.missing`), nút "Tạo truyện" gọi `PATCH status=ready` rồi điều hướng `/works/$workId` |

## State và dữ liệu

- TanStack Query keys: `['works', 'list', filters]` (infinite), `['works', workId]`, `['works', workId, 'style-profile']`, `['languages']`, `['languages', 'vi', 'genres']`.
- Zustand: `useLibraryUiStore` giữ `view` (grid/table) trong phiên; lựa chọn lâu dài lưu qua settings DB (không localStorage – Plan §3.1).
- Lưu nháp wizard: mỗi bước dùng react-hook-form; "Tiếp" → validate zod → PATCH (`wizard_step` = bước kế, thêm vào `wizard_completed_steps`); "Lưu nháp & đóng" → PATCH không đổi bước rồi về `/`. Khi rời trang có thay đổi chưa lưu → hộp thoại xác nhận. Bước 1 lần đầu gọi `POST /v1/works` rồi `navigate({search: {workId}})`.
- Mở lại nháp: `/new?workId=` → GET work → nhảy tới `step` trong URL nếu có, nếu không thì `wizard_step`.
- API dùng: `GET/POST/PATCH/DELETE /v1/works`, `POST /v1/works/{id}/open`, `GET/PUT /v1/works/{id}/style-profile`, `GET /v1/languages`, `GET /v1/languages/vi/genres`, `PUT /v1/settings/roles?work_id=` (F04).
- Event SSE dùng (`/v1/events`): `job.state`, `queue.changed`, `work.continuity`, `chapter.committed` → `useLibraryLiveUpdates` gom trong 500 ms rồi invalidate `['works','list']` (giảm refetch khi nhiều truyện cùng chạy). Không đăng ký `token.delta` cho thư viện.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton 8 card (lưới) hoặc 10 dòng (bảng) |
| Rỗng (chưa có truyện) | Minh họa + "Chưa có truyện nào" + nút "Tạo truyện đầu tiên" (và "Mở truyện mẫu" nếu onboarding F03 cung cấp) |
| Rỗng (lọc không ra) | "Không có truyện khớp bộ lọc" + nút "Xóa bộ lọc" |
| Lỗi (`code`) | Khung lỗi theo F01 + nút "Thử lại"; `REVISION_CONFLICT` trong wizard → toast + tải lại bước |
| Lỗi `VALIDATION` khi Tạo | Danh sách mục thiếu, mỗi mục là link nhảy về bước tương ứng |
| Lỗi `WORK_ACTIVE_JOB` khi xóa | "Truyện đang được viết. Dừng auto-write trước khi xóa" + nút "Mở Phòng viết" |
| Thành công | Toast "Đã tạo truyện" / "Đã lưu nháp" |

## Tương tác, phím tắt, khả năng tiếp cận

- Ctrl+K mở command palette chung (gõ tên truyện để mở); `/` focus ô tìm của thư viện.
- Lưới: điều hướng bằng phím mũi tên giữa card (roving tabindex), Enter mở truyện; menu ngữ cảnh bằng Shift+F10.
- Ô ngôn ngữ chỉ có một lựa chọn nhưng vẫn hiển thị (UI §1 #5) kèm ghi chú "Các ngôn ngữ khác sẽ có sau".
- Badge: icon + chữ, `aria-label` đầy đủ ("Đang chờ slot số 2 vì nhà cung cấp đầy").
- Stepper là `nav` với `aria-current="step"`; bước chưa mở khóa vẫn chọn được nếu đã có dữ liệu.

## Chuỗi giao diện (i18n)

Namespace `library` và `wizard`, ví dụ khóa: `library.title` ("Thư viện"), `library.newWork` ("+ Truyện"), `library.empty.title`, `library.badge.blocked` ("Bị chặn, cần resync"), `library.badge.waitingSlot` ("Chờ slot #{{pos}}"), `library.badge.stale` ("Cần settle lại từ Ch.{{k}}"), `wizard.steps.basics` ("Cơ bản"), `wizard.steps.brief`, `wizard.steps.foundation` ("Nền truyện"), `wizard.steps.addressRules` ("Xưng hô"), `wizard.steps.eventOutline` ("Dàn ý sự kiện"), `wizard.steps.writingConfig` ("Cấu hình viết"), `wizard.steps.review` ("Tạo"), `wizard.style.toneMark.old` ("Kiểu cũ: hoà, thuý"), `wizard.style.toneMark.new` ("Kiểu mới: hòa, thúy"). Nhãn thể loại lấy từ preset của gói ngôn ngữ (BE trả `label`). MVP chỉ có `vi`.

## Việc cần làm

- [ ] `LibraryPage` + `WorkGrid`/`WorkTable` ảo hóa, toolbar lọc/tìm, chuyển chế độ xem.
- [ ] `WorkStatusBadge` dùng chung (export cho Phòng viết, header).
- [ ] `useLibraryLiveUpdates` gom event và invalidate có throttle.
- [ ] Wizard: stepper, lưu nháp từng bước, mở lại đúng bước, xác nhận khi rời trang.
- [ ] `BasicsStep` (style profile đầy đủ), `BriefStep`, `WritingConfigStep`, `ReviewCreateStep`.
- [ ] Nhúng bước 3–5 của F06; khi F06 chưa có, hiển thị placeholder "Sẽ có ở R2" và cho bỏ qua trong dev.
- [ ] Menu thao tác: lưu trữ, xóa (xác nhận gõ tên truyện).

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `WorkStatusBadge` render đủ 11 `kind`, có chữ + icon | `fe/src/features/library/components/WorkStatusBadge.test.tsx` |
| component | `WorkGrid` chỉ render số card trong viewport với 500 mục | `fe/src/features/library/components/WorkGrid.test.tsx` |
| component | `BasicsStep`: chỉ có "Tiếng Việt"; preset thể loại điền mặc định style profile | `fe/src/features/library/components/wizard/BasicsStep.test.tsx` |
| e2e (mock backend) | Tạo truyện qua wizard, đóng ở bước Brief, mở lại → đúng bước, dữ liệu còn | `fe/tests/e2e/wizard-draft.spec.ts` |
| e2e (mock backend) | Thư viện: tìm "nguyen" ra "Nguyễn", lọc trạng thái, event `work.continuity` đổi badge | `fe/tests/e2e/library.spec.ts` |

Luồng: [T04](../../tests/flows/T04-tao-truyen-va-nen-truyen.md).

## Tên mới đề xuất

- Search params: `/?view=&q=&genre=&status=&sort=`, `/new?workId=&step=`.
- Component/hook: `LibraryToolbar`, `WorkGrid`, `WorkTable`, `WorkCard`, `WorkStatusBadge`, `WorkActionsMenu`, `WizardStepper`, `BasicsStep`, `BriefStep`, `WritingConfigStep`, `ReviewCreateStep`, `useWorksInfinite`, `useWorkDraft`, `useLibraryLiveUpdates`, `useLibraryUiStore`.
- Giá trị bước wizard: `basics`, `brief`, `foundation`, `address_rules`, `event_outline`, `writing_config`, `review`.
- i18n namespace `library`, `wizard`.
