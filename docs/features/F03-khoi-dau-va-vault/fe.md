# F03 — Frontend

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/onboarding` | `OnboardingPage` (wizard toàn màn, không có ribbon/sidebar) | Tự chuyển tới khi `GET /v1/onboarding` trả `status="pending"`; mở lại được từ Cài đặt |
| (toàn cục) | `VaultUnlockDialog` | Hộp thoại modal, mở từ badge, từ lỗi `VAULT_LOCKED`, từ toast job chờ vault |
| (header) | `VaultBadge` | Cạnh chỉ báo "● N truyện đang chạy" (UI §4) |
| `/settings/security` | Mục "Bảo mật & API key" | Trạng thái vault, tạo/đổi mật khẩu/khóa/đặt lại, danh sách key (không hiện giá trị), chạy lại onboarding |

Wizard (Plan §23.4 #1, UI §5.8):

```text
Bước 1  Thư mục dữ liệu   (macOS: "Đã chọn: <đường dẫn>" ✓ — chọn ở màn F00; Windows: "Dữ liệu nằm cạnh ứng dụng: <đường dẫn>")
Bước 2  Bảo mật API key   (•) Đặt mật khẩu vault  ( ) Chỉ dùng key trong phiên này
Bước 3  Kết nối AI        Form provider + [Kiểm tra kết nối] [Kiểm tra lấy danh sách]   [Để sau]
Bước 4  Truyện đầu tiên   [Tạo truyện mới] [Mở truyện mẫu]   [Vào thư viện]
```

## Component

```text
fe/src/features/onboarding/
  pages/OnboardingPage.tsx
  components/OnboardingStepper.tsx
  components/StepDataRoot.tsx
  components/StepSecurity.tsx        Chọn chế độ; form mật khẩu (react-hook-form + zod)
  components/StepProvider.tsx        Nhúng form provider của F04
  components/StepFirstWork.tsx       Nút sang wizard F05 / truyện mẫu F05
  api/onboarding.ts                  useOnboarding(), useUpdateOnboarding(), useCompleteOnboarding()
  hooks/useOnboardingRedirect.ts     Điều hướng tới /onboarding khi pending
  index.ts
fe/src/features/settings/
  components/vault/VaultUnlockDialog.tsx
  components/vault/VaultBadge.tsx
  components/vault/CreateVaultForm.tsx
  components/vault/ChangePasswordForm.tsx
  components/vault/ResetVaultDialog.tsx
  components/vault/SecretList.tsx
  pages/SecuritySettingsPage.tsx
  api/vault.ts                       useVaultStatus(), useCreateVault(), useUnlockVault(), useLockVault(),
                                     useChangeVaultPassword(), useResetVault(), useSetVaultMode(), useSecrets()
  store/vaultDialogStore.ts          Zustand: open/close + lý do mở (badge | error | job)
```

| Component | Trách nhiệm |
|---|---|
| `OnboardingPage` | Đọc `OnboardingState`, bắt đầu ở bước đầu chưa `done`; mỗi bước xong gọi `PUT /v1/onboarding {step}`; nút "Bỏ qua thiết lập" → `complete {skipped:true}` rồi về `/` |
| `StepSecurity` | Hai lựa chọn có mô tả rõ: vault (key mã hóa trong `data/secrets.enc`, cần mật khẩu khi mở app và dùng AI, **quên mật khẩu là mất key**, có thể chép data sang máy khác) và theo phiên (key chỉ trong bộ nhớ, phải nhập lại mỗi lần mở app). Vault: hai ô mật khẩu, chỉ báo độ mạnh (độ dài; cảnh báo < 12 ký tự), checkbox "Tôi hiểu không thể khôi phục mật khẩu" bắt buộc → `POST /v1/vault`. Theo phiên → `PUT /v1/vault/mode {mode:"session_only"}` |
| `StepProvider` | Nhúng form kết nối provider của F04; khi lưu key, truyền `storage = vault.mode === "vault" ? "vault" : "session"`. Hiển thị kết quả kiểm tra kết nối/lấy danh sách model do F04 trả. "Để sau" → bước kế tiếp với `provider=skipped` |
| `StepFirstWork` | "Tạo truyện mới" → `/new` (F05) sau khi `complete`; "Mở truyện mẫu" → hành động truyện mẫu của F05 rồi mở workspace; "Vào thư viện" → `/` |
| `VaultUnlockDialog` | Ô mật khẩu (tự focus), nút "Mở khóa"; lý do mở hiện ở dòng phụ ("3 tác vụ đang chờ mở vault"). Lỗi `VAULT_PASSWORD_INVALID` → thông báo dưới ô, xóa ô; `VAULT_UNLOCK_THROTTLED` → khóa nút, đếm ngược theo `Retry-After`. Thành công → đóng, toast "Đã mở vault", retry thao tác gây lỗi nếu có (callback do người mở truyền vào) |
| `VaultBadge` | `state="locked"` → icon khóa + "Vault đang khóa" (+ "· N chờ" nếu `waiting_jobs > 0`), bấm mở dialog. `unlocked` → icon khóa mở thu gọn, menu "Khóa vault". `absent` + `mode="session_only"` + có key `available=false` → "Cần nhập key" dẫn tới Cài đặt → Mô hình AI. `absent` + `undecided` → ẩn |
| `SecretList` | Bảng `ref` → nhãn thân thiện (tên provider từ F04), nơi lưu (Vault/Phiên), trạng thái (sẵn sàng/khóa/thiếu), nút xóa. Không bao giờ hiển thị giá trị |
| `ResetVaultDialog` | Yêu cầu gõ đúng "XÓA VAULT"; giải thích mọi key trong vault bị xóa |

## State và dữ liệu

- TanStack Query keys: `['vault']` (status), `['secrets']`, `['onboarding']`.
- Zustand store: `vaultDialogStore` (`isOpen`, `reason`, `onUnlocked?`).
- API dùng: `GET /v1/vault/status`, `POST /v1/vault`, `POST /v1/vault/unlock`, `POST /v1/vault/lock`, `POST /v1/vault/change-password`, `POST /v1/vault/reset`, `PUT /v1/vault/mode`, `GET /v1/secrets`, `PUT /v1/secrets/{ref}`, `DELETE /v1/secrets/{ref}`, `GET/PUT /v1/onboarding`, `POST /v1/onboarding/complete`; API provider của F04 trong `StepProvider`.
- Event SSE dùng (`/v1/events`): `vault.status` → cập nhật cache `['vault']` trực tiếp (không cần refetch) và invalidate `['secrets']`; `job.state` có `wait_reason="VAULT_LOCKED"` → toast một lần mỗi phút (gộp) "Tác vụ đang chờ mở vault" kèm nút "Mở khóa"; `wait_reason="SECRET_MISSING"` → toast dẫn tới nhập key.
- Đăng ký `ErrorAction` (F01 `app/errorActions.ts`): `unlock_vault` → mở `VaultUnlockDialog` với `onUnlocked` = thử lại request.
- Mật khẩu chỉ nằm trong state form, xóa khi đóng dialog/rời bước; không đưa vào store toàn cục, không log, không lưu `localStorage`.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Wizard: skeleton stepper; dialog: nút "Mở khóa" có spinner trong lúc KDF chạy (có thể mất vài trăm ms đến vài giây — chưa đo) |
| Rỗng | `SecretList` rỗng: "Chưa có API key nào. Thêm nhà cung cấp ở Mô hình AI" + liên kết |
| Lỗi (`code`) | `VAULT_PASSWORD_INVALID` (dưới ô), `VAULT_UNLOCK_THROTTLED` (đếm ngược), `VAULT_CORRUPT` (hộp lỗi + gợi ý khôi phục backup/đặt lại), `VALIDATION` (lỗi từng trường), lỗi khác → `ErrorState` (F01) |
| Thành công | Toast "Đã tạo vault"/"Đã mở vault"/"Đã khóa vault"; wizard sang bước kế |

## Tương tác, phím tắt, khả năng tiếp cận

- Wizard: Enter = "Tiếp tục" khi form hợp lệ; Esc không thoát wizard (tránh mất tiến độ); có nút "Quay lại".
- Dialog mở khóa: focus vào ô mật khẩu, Enter gửi, Esc đóng; `aria-describedby` trỏ tới dòng lý do; lỗi đọc qua `role="alert"`.
- Ô mật khẩu có nút hiện/ẩn (`aria-label` "Hiện mật khẩu"), `autocomplete="new-password"`/`"current-password"` phù hợp.
- Badge có `aria-label` đầy đủ ("Vault đang khóa, 3 tác vụ đang chờ. Bấm để mở khóa"); trạng thái có icon + chữ, không chỉ màu (UI §8).
- Stepper dùng `aria-current="step"`.

## Chuỗi giao diện (i18n)

Namespace `onboarding` và `vault`. Ví dụ khóa: `onboarding.title`, `onboarding.step.dataRoot`, `onboarding.step.security`, `onboarding.step.provider`, `onboarding.step.firstWork`, `onboarding.security.vault.title`, `onboarding.security.vault.noRecovery`, `onboarding.security.session.title`, `onboarding.skipAll`, `onboarding.firstWork.new`, `onboarding.firstWork.sample`; `vault.badge.locked`, `vault.badge.waiting` (`{{count}}`), `vault.unlock.title`, `vault.unlock.reason.jobs`, `vault.error.VAULT_PASSWORD_INVALID`, `vault.error.VAULT_UNLOCK_THROTTLED` (`{{seconds}}`), `vault.reset.confirmPhrase`, `vault.secrets.storage.vault`, `vault.secrets.storage.session`. MVP chỉ có `vi`.

## Việc cần làm

- [ ] `api/onboarding.ts`, `api/vault.ts` dùng generated types.
- [ ] `useOnboardingRedirect` gắn ở route gốc (chỉ chạy khi backend `ready`).
- [ ] Bốn bước wizard; `StepProvider` dùng component F04 (tạm placeholder liên kết tới Cài đặt nếu F04 chưa xong).
- [ ] `VaultUnlockDialog`, `vaultDialogStore`, đăng ký `unlock_vault` vào `errorActions`.
- [ ] `VaultBadge` trong header; xử lý `vault.status` và `job.state` (wait_reason) từ event bus.
- [ ] `SecuritySettingsPage` với tạo/đổi mật khẩu/khóa/đặt lại/danh sách key.
- [ ] Khóa i18n `onboarding`, `vault`.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| component | `StepSecurity`: mật khẩu không khớp/ngắn bị chặn; phải tick "không thể khôi phục"; chọn theo phiên gọi `PUT /v1/vault/mode` | `fe/src/features/onboarding/components/StepSecurity.test.tsx` |
| component | `VaultUnlockDialog`: sai mật khẩu hiện lỗi và xóa ô; throttle đếm ngược khóa nút; thành công gọi `onUnlocked` | `fe/src/features/settings/components/vault/VaultUnlockDialog.test.tsx` |
| component | `VaultBadge` theo từng tổ hợp `state`/`mode`/`waiting_jobs` | `fe/src/features/settings/components/vault/VaultBadge.test.tsx` |
| unit | Mật khẩu không xuất hiện trong store toàn cục/`localStorage` sau khi đóng dialog | `fe/src/features/settings/components/vault/vaultSecrets.test.ts` |
| e2e (mock backend) | Lần chạy đầu: vào `/onboarding` → tạo vault → bỏ qua provider → tạo truyện → không hiện lại onboarding khi reload | `fe/tests/e2e/onboarding.spec.ts` |
| e2e (mock backend) | Mock phát `job.state wait_reason=VAULT_LOCKED` → badge "1 chờ" → mở khóa → mock phát `vault.status unlocked` → badge đổi | `fe/tests/e2e/vault-locked-jobs.spec.ts` |

## Tên mới đề xuất

- Route `/onboarding`, section `/settings/security` (UI §5.6 chưa có mục Bảo mật).
- Component: `OnboardingPage`, `OnboardingStepper`, `StepDataRoot`, `StepSecurity`, `StepProvider`, `StepFirstWork`, `VaultUnlockDialog`, `VaultBadge`, `CreateVaultForm`, `ChangePasswordForm`, `ResetVaultDialog`, `SecretList`, `SecuritySettingsPage`.
- Hook/store: `useOnboardingRedirect`, `useOnboarding`, `useVaultStatus` (và các mutation ở trên), `vaultDialogStore`.
- Query keys `['vault']`, `['secrets']`, `['onboarding']`; namespace i18n `onboarding`, `vault`.
- Phụ thuộc tên chưa chốt của tính năng khác: form kết nối provider (F04), hành động "truyện mẫu" (F05).
