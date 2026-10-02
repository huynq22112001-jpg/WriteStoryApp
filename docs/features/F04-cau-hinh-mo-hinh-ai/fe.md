# F04 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/settings/models` | Mô hình AI (UI §5.6.1) | Mục đầu của menu trái Cài đặt (UI §5.6) |
| `/settings/roles` | Vai trò & effort (UI §5.6.2) | Cấp toàn app |
| `/settings/limits` | Đồng thời & ngân sách (UI §5.6.3) | Số truyện song song, request đồng thời/RPM/TPM theo provider, ngân sách |
| `/works/$workId?mode=…` → hộp thoại "Cài đặt truyện › Vai trò" | Ghi đè vai trò theo truyện | Dùng lại `RoleTable` với `workId` |

`$section` thuộc `/settings/$section` (UI §4 Route). Onboarding (F03) nhúng `ProviderConnectionForm` + `DiscoverButton`.

## Component

```text
fe/src/features/settings/
  pages/ModelsSettingsPage.tsx
  pages/RolesSettingsPage.tsx
  pages/LimitsSettingsPage.tsx
  components/SettingRow.tsx            Mẫu chung: tiêu đề đậm, mô tả xám, "Tìm hiểu thêm ⌄", điều khiển căn phải
  components/ProviderSwitcher.tsx
  components/ProviderConnectionForm.tsx
  components/DiscoverButton.tsx
  components/ModelList.tsx             dnd-kit sortable
  components/ModelRow.tsx              Hàng thu gọn/mở rộng (› / ⌄)
  components/OtherModelsSection.tsx    "Model khả dụng khác"
  components/AddModelDialog.tsx        "+ Thêm"
  components/EffortSelect.tsx
  components/RoleTable.tsx
  hooks/useProviders.ts, useProviderModels.ts, useRoles.ts, useLimits.ts
  api/providers.ts                     Query/mutation dùng generated types
  schemas/providerForm.ts              zod 4
```

| Component | Trách nhiệm |
|---|---|
| `SettingRow` | Bố cục mục cài đặt kiểu trang Models của Claude (UI §5.6): `title` đậm, `description` xám, link "Tìm hiểu thêm ⌄" mở phần giải thích ngay bên dưới (Base UI Collapsible), `control` căn phải |
| `ProviderSwitcher` | Chỉ hiện khi có > 1 provider: tab/ô chọn provider + "+ Thêm nhà cung cấp". Với 1 provider giao diện giống hệt wireframe |
| `ProviderConnectionForm` | Khối "Kết nối": Giao thức (Anthropic \| OpenAI-compatible \| Ollama/LM Studio), Base URL, API key (ô mật khẩu, ghi chú "lưu trong vault"), nút "Kiểm tra kết nối". Ollama/LM Studio ẩn ô key, gợi ý base URL local |
| `DiscoverButton` | Nút "Kiểm tra lấy danh sách" góc phải tiêu đề, chấm tròn: xám = `never`, xanh = `ok`, đỏ = `error`, vàng nhấp nháy = đang chạy hoặc `waiting_vault`. Kết quả: số model, mới/biến mất, lỗi cụ thể |
| `ModelList` / `ModelRow` | Danh sách ghi đè có thứ tự, kéo `⋮⋮` để đổi thứ tự, mục đầu gắn nhãn "mặc định", `✕` xóa, `›`/`⌄` mở rộng. Hàng mở rộng: Tên hiển thị, Context, Output tối đa, Effort hỗ trợ (checkbox 5 mức), Giá/1M token (vào, ra, đọc cache, ghi cache), Dùng cho (5 vai trò), Đồng thời riêng, dòng "Nguồn: tự lấy dd/mm/yyyy · ✓ đã thử gọi". Ô người dùng đã sửa có biểu tượng "đã sửa" + nút khôi phục |
| `OtherModelsSection` | Model tự lấy nhưng không có trong danh sách ghi đè, nút thêm nhanh |
| `AddModelDialog` | Nhập `model_id` thủ công (gateway không liệt kê model) |
| `EffortSelect` | Chỉ hiện mức model hỗ trợ + "(mặc định model)"; model không hỗ trợ → khóa kèm tooltip giải thích |
| `RoleTable` | 5 dòng vai trò × [Model ▾] [Effort ▾]; hiển thị giá trị kế thừa mờ "(theo …)"; ghi chú ⓘ effort cố định trong một lượt viết |

## State và dữ liệu

- TanStack Query keys: `['providers']`, `['providers', id, 'models']`, `['settings', 'roles', workId ?? 'app']`, `['providers', id, 'limits']`, `['settings', 'limits']`.
- Zustand: không cần store riêng; trạng thái mở rộng hàng model và trạng thái "Tìm hiểu thêm" là state cục bộ component.
- Form: react-hook-form + zod; **lưu tự động từng mục** (UI §5.6.3): toggle lưu ngay; ô text lưu khi blur hoặc sau debounce 800 ms; kéo thả lưu khi thả. Toast sonner "Đã lưu". Mọi PUT/PATCH gửi `expected_revision`.
- API dùng: `GET/POST/PATCH/DELETE /v1/providers`, `POST /v1/providers/test`, `POST /v1/providers/{id}/discover`, `GET/PUT /v1/providers/{id}/models`, `GET/PUT /v1/settings/roles[?work_id]`, `GET/PUT /v1/providers/{id}/limits`, `GET/PUT /v1/settings/limits`.
- Event SSE dùng (`/v1/events`): `provider.status` → cập nhật chấm tròn, invalidate `['providers', id, 'models']`; `vault.status` → cập nhật ghi chú khóa ô key.
- Kéo thả: dnd-kit sortable, cập nhật optimistic; lỗi 409 → rollback + tải lại + toast.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton cho khối Kết nối và 3 hàng model |
| Rỗng (chưa có provider) | Màn rỗng: "Chưa kết nối nhà cung cấp AI" + nút "Thêm nhà cung cấp" |
| Rỗng (danh sách model) | `auto_discover` tắt: "Danh sách trống. Thêm model hoặc bật Tự lấy danh sách"; bật: "Bấm Kiểm tra lấy danh sách" |
| Đang lấy danh sách | Chấm tròn vàng, nút bị khóa, chữ "Đang lấy…" |
| Lỗi `PROVIDER_AUTH` | Chấm đỏ: "Sai API key (401)" + nút "Sửa key" |
| Lỗi `PROVIDER_UNREACHABLE` | `endpoint_not_found`: "Server không có /v1/models (404)"; `timeout`: "Hết thời gian chờ"; `bad_response`: "Phản hồi không đúng định dạng" — kèm thời điểm, danh sách cũ vẫn hiển thị |
| Lỗi `VAULT_LOCKED` | "Vault đang khóa" + nút "Mở vault" (hộp thoại F03) |
| Lỗi `REVISION_CONFLICT` | Toast "Cài đặt vừa thay đổi ở nơi khác, đã tải lại" |
| Model ⚠ | Biểu tượng ⚠ + tooltip "Không còn trên server từ dd/mm" (chữ, không chỉ màu – UI §8) |
| Thành công | Toast "Tìm thấy N model · 2 mới · 1 biến mất" |

## Tương tác, phím tắt, khả năng tiếp cận

- Danh sách model: kéo bằng chuột và bàn phím (dnd-kit KeyboardSensor: Space nhấc, ↑/↓ di chuyển, Space thả); thông báo `aria-live` "Đã chuyển claude-pro lên vị trí 1, đây là model mặc định".
- Nút chỉ có icon (`⋮⋮`, `›`, `✕`) có `aria-label` tiếng Việt: "Kéo để đổi thứ tự", "Mở rộng chi tiết model", "Xóa khỏi danh sách".
- Chấm tròn trạng thái luôn kèm chữ trong `aria-label`/tooltip.
- Xóa model mặc định hoặc xóa provider: hộp thoại xác nhận nêu vai trò bị ảnh hưởng.
- "Tìm hiểu thêm ⌄" là `button` có `aria-expanded`.

## Chuỗi giao diện (i18n)

Namespace `settings`, ví dụ khóa: `settings.models.title` ("Mô hình AI"), `settings.models.discover.button` ("Kiểm tra lấy danh sách"), `settings.models.autoDiscover.title` ("Tự lấy danh sách model"), `settings.models.autoDiscover.desc`, `settings.models.longContext.title` ("Ưu tiên bản context dài (1M)"), `settings.models.list.desc` ("Ghi đè danh sách lấy tự động. Model đầu tiên là mặc định. Kéo để đổi thứ tự."), `settings.models.effort.title` ("Mức effort mặc định"), `settings.models.learnMore` ("Tìm hiểu thêm"), `settings.roles.planner` ("Lập kế hoạch"), `settings.roles.writer` ("Viết chương"), `settings.roles.checker` ("Kiểm tra/Settle"), `settings.roles.reviewer` ("Mối nối & Review"), `settings.roles.summary` ("Tóm tắt"), `settings.roles.effortNote`. Thông báo lỗi lấy từ `errors.<CODE>` (F01). MVP chỉ có `vi`.

## Việc cần làm

- [ ] `SettingRow` dùng chung cho mọi mục Cài đặt.
- [ ] Trang Mô hình AI theo đúng thứ tự wireframe §5.6.1: Kết nối → Tự lấy danh sách → Ưu tiên context dài → Danh sách model (+ Thêm, Model khả dụng khác) → Mức effort mặc định.
- [ ] `DiscoverButton` với 4 trạng thái chấm tròn và tóm tắt kết quả.
- [ ] `ModelList` kéo thả + `ModelRow` mở rộng, đánh dấu trường đã sửa, khôi phục.
- [ ] `EffortSelect` lọc theo `supported_efforts` (NULL → khóa với chú thích "Chưa biết model hỗ trợ mức nào; khai báo trong chi tiết model").
- [ ] `RoleTable` cấp app và cấp truyện, hiển thị kế thừa.
- [ ] Trang Đồng thời & ngân sách (lưu tự động).
- [ ] Xử lý SSE `provider.status`.
- [ ] Không bao giờ hiển thị lại API key đã lưu (chỉ `••••` + "Thay key").

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `ModelList`: kéo đổi thứ tự → nhãn "mặc định" chuyển; gọi PUT đúng thứ tự | `fe/src/features/settings/components/ModelList.test.tsx` |
| component | `ModelRow`: sửa context → hiện "đã sửa"; khôi phục gọi `reset_fields` | `fe/src/features/settings/components/ModelRow.test.tsx` |
| component | `EffortSelect`: chỉ hiện mức hỗ trợ; khóa khi `[]`/NULL | `fe/src/features/settings/components/EffortSelect.test.tsx` |
| component | `DiscoverButton`: xám/vàng/xanh/đỏ, thông điệp 401/404/timeout | `fe/src/features/settings/components/DiscoverButton.test.tsx` |
| e2e (mock backend) | Thêm provider → lấy danh sách → ghi đè → gán vai trò → reload vẫn giữ | `fe/tests/e2e/settings-models.spec.ts` |
| e2e (mock backend) | Vault khóa khi lấy danh sách → mở vault → tự chạy lại | `fe/tests/e2e/settings-models-vault.spec.ts` |

Luồng: [T03](../../tests/flows/T03-cau-hinh-mo-hinh-ai.md).

## Tên mới đề xuất

- Route: `/settings/models`, `/settings/roles`, `/settings/limits` (giá trị của `$section`).
- Component: `SettingRow`, `ProviderSwitcher`, `ProviderConnectionForm`, `DiscoverButton`, `ModelList`, `ModelRow`, `OtherModelsSection`, `AddModelDialog`, `EffortSelect`, `RoleTable`.
- i18n namespace `settings` và các khóa nêu trên.
