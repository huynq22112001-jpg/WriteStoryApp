# F08 — Frontend

FE không chứa logic kiểm tra tiếng Việt (nằm ở AI). FE chịu trách nhiệm: hạ tầng i18n cho toàn app, chuẩn hóa NFC tại chỗ khi dán, đếm âm tiết hiển thị (cùng thuật toán với AI qua bộ golden chung), UI sửa style profile/cụm sáo, và hiển thị finding tiếng Việt.

## Route và màn hình

| Route | Màn hình | Ghi chú |
|---|---|---|
| `/settings/language` | Cài đặt → Ngôn ngữ | Ngôn ngữ giao diện (chỉ "Tiếng Việt", bị khóa), danh sách cụm sáo toàn app |
| `/settings/roles` | Cài đặt → Vai trò & effort (F04) | Thêm khối "Đánh giá tiếng Việt" và kết quả `model_evals` |
| `/works/$workId/bible/style` | Story Bible → Văn phong | `style_profile` của truyện: kiểu bỏ dấu, thoại, Hán Việt, cụm sáo riêng |
| `/new` (F05) | Wizard bước "Ngôn ngữ + thể loại + style profile" | Dùng lại component của F08 |
| `/works/$workId?tab=review` | Tab Review (F11) | Hiển thị finding `source=check` của F08 |

## Component

```text
fe/src/shared/i18n/
  index.ts                 init i18next + react-i18next, lng "vi", namespaces
  i18next.d.ts             CustomTypeOptions: khóa có type từ vi/*.json
  format.ts                Intl "vi-VN": số (2.341), ngày, tiền
  errors.ts                tErrorCode(code) → {title, action}
  vi/common.json, errors.json, library.json, editor.json, ai.json, continuity.json,
     bible.json, settings.json, language.json, review.json, jobs.json
fe/src/shared/lib/vi/
  syllables.ts             countSyllables(text), countChars(text) – cùng spec với ai length.py
  nfc.ts                   normalizePaste(text) → NFC, bỏ zero-width; detectLegacyEncoding(text)
fe/src/features/language/
  components/StyleProfileForm.tsx
  components/AccentStyleSelect.tsx
  components/DialogueStyleSelect.tsx
  components/SlopListEditor.tsx
  components/SlopTester.tsx
  components/LanguageFindingItem.tsx
  components/LengthBadge.tsx
  components/ModelEvalPanel.tsx
  hooks/usePasteNormalize.ts
  api/languageApi.ts
```

| Component | Trách nhiệm |
|---|---|
| `StyleProfileForm` | Form react-hook-form + zod: `tone_mark_style`, `dialogue_style`, `dialogue_dash_char`, `punctuation_rules` (`quote_chars`, `ellipsis`), `vocab_register`, `voice_samples` (tối đa 2 đoạn style anchor – Plan §23.3 #7); lưu tự động từng trường với `expected_revision` (UI §5.6.3); ghi chú "áp từ chương kế tiếp" khi truyện đang chạy (UI §5.4) |
| `AccentStyleSelect` | Hai lựa chọn kèm ví dụ trực quan: "hoà, thuý, khoẻ (kiểu cũ)" / "hòa, thúy, khỏe (kiểu mới)"; khi đổi, hiển thị cảnh báo số chương đang dùng kiểu khác (từ API) |
| `SlopListEditor` | Bảng ảo hóa: cụm, regex?, phạm vi (đầu đoạn/mọi nơi), ngưỡng/1.000 âm tiết, bật/tắt mục có sẵn; thêm/xóa mục người dùng; hai cấp: toàn app và theo truyện |
| `SlopTester` | Dán đoạn văn mẫu → gọi `/text/check` với `checks=["vi.slop"]` → tô sáng chỗ khớp; giúp kiểm regex trước khi lưu |
| `LanguageFindingItem` | Hiển thị một finding: icon + chữ mức độ (⛔/⚠/ⓘ, không chỉ màu – UI §8), nhãn loại (Xưng hô, Tên riêng, Lớp từ, Cụm sáo, Chính tả, Kiểu bỏ dấu, Thoại), trích dẫn, gợi ý; bấm → nhảy tới `paragraph_id` trong editor; nút "Bỏ qua" (dismiss, F11) và "Mở quy tắc xưng hô" (dẫn tới tab Xưng hô ở Story Bible – UI §5.4) |
| `LengthBadge` | "2.341 âm tiết · 10.512 ký tự" ở thanh tiêu đề chương (UI §5.2); tooltip giải thích cách đếm |
| `ModelEvalPanel` | Chọn model cần so → chạy job → bảng chỉ số (xưng hô, chính tả, lẫn từ ngoại, cụm sáo, điểm tự nhiên của giám khảo, token/âm tiết) + gợi ý vai trò; không tự đổi cấu hình vai trò |
| `usePasteNormalize` | Tiptap `handlePaste`/`transformPastedText`: NFC + bỏ zero-width tại chỗ; nếu `detectLegacyEncoding` nghi ngờ → gọi `/normalize` `mode=paste` và mở hộp xác nhận "Văn bản có vẻ dùng bảng mã TCVN3. Chuyển sang Unicode?" |

## State và dữ liệu

- TanStack Query keys: `['languages']`, `['languages', code, 'genre-presets']`, `['languages', code, 'slop-list']`, `['works', workId, 'style-profile']`, `['evals', 'language-models', 'vi']`.
- Zustand: không cần store riêng; trạng thái hộp xác nhận dán nằm trong component.
- API dùng: các endpoint ở [be.md](./be.md#api); `GET /v1/works/{id}/findings?status=open` (F11) lọc `source=check`.
- Event SSE (`/v1/events`): `finding.added` (cập nhật danh sách finding của chương đang mở), `job.step`/`job.state` cho job `language_eval`.

## Trạng thái giao diện

| Trạng thái | Hiển thị |
|---|---|
| Đang tải | Skeleton form/bảng (mẫu thống nhất Plan §23.4 #7) |
| Rỗng | Danh sách cụm sáo người dùng rỗng: "Chưa thêm cụm nào. Danh sách có sẵn vẫn được dùng."; chưa có kết quả đánh giá: nút "Chạy đánh giá" + ước tính số request |
| Lỗi (`code`) | `VALIDATION` (regex sai) → báo dưới ô nhập kèm vị trí; `REVISION_CONFLICT` → "Danh sách vừa được sửa ở nơi khác" + nút tải lại; `VAULT_LOCKED` → mở hộp thoại mở khóa vault |
| Thành công | Toast sonner "Đã lưu"; finding cập nhật theo SSE |

## Tương tác, phím tắt, khả năng tiếp cận

- Dán: không chặn gõ; chuẩn hóa NFC đồng bộ (rẻ), chỉ chuyển bảng mã khi người dùng xác nhận.
- Không tự sửa chính tả trong editor; finding chính tả chỉ là gợi ý.
- `aria-label` tiếng Việt cho mọi nút icon (bật/tắt cụm sáo, xóa, chạy thử).
- `LengthBadge` cập nhật debounce cùng nhịp autosave (không đếm lại toàn chương mỗi phím; đếm theo đoạn thay đổi).

## Chuỗi giao diện (i18n)

Cấu hình i18next:

```text
lng: "vi", fallbackLng: "vi", supportedLngs: ["vi"], ns: [common, errors, ...], defaultNS: "common"
interpolation.escapeValue: false (React đã escape); returnNull: false
resources nạp tĩnh (import JSON), không tải mạng – chạy offline
```

- Kiểu khóa: `i18next.d.ts` khai báo `resources` từ `vi/*.json` để `t('language:accent.old')` được kiểm tra khi build.
- Lint: bật quy tắc cấm chuỗi literal trong JSX (ví dụ `i18next/no-literal-string`), ngoại lệ cho tên class/test id.
- Mã lỗi API → `errors:<CODE>.title|action` (Plan §23.1.D); message từ BE dùng khi FE chưa có khóa.
- Số và đơn vị: dùng `format.ts` (`Intl.NumberFormat('vi-VN')`) → "2.341 âm tiết".
- Namespace `language`, ví dụ khóa: `language:accent.old`, `language:accent.new`, `language:dialogue.dash`, `language:finding.kind.address`, `language:finding.kind.anachronism`, `language:finding.address.mismatch` ("{{speaker}} gọi {{listener}} là “{{found}}”, quy tắc là “{{expected}}” từ chương {{from}}"), `language:paste.legacy.confirm`.
- Thêm ngôn ngữ UI sau này = thêm thư mục `shared/i18n/<lang>/` (UI §9); MVP chỉ `vi`.

## Việc cần làm

- [ ] Dựng `shared/i18n` + type khóa + lint cấm chuỗi cứng (R0/R1, trước khi có nhiều màn hình).
- [ ] `syllables.ts` theo spec ai.md; chạy chung golden `tests/fixtures/language/vi/length_cases.json`.
- [ ] `nfc.ts` + `usePasteNormalize` gắn vào editor F07.
- [ ] `StyleProfileForm`, `AccentStyleSelect`, `DialogueStyleSelect` (dùng lại ở wizard F05).
- [ ] `SlopListEditor` hai cấp + `SlopTester`.
- [ ] `LanguageFindingItem` dùng trong tab Review (F11) và Nhớ (F09).
- [ ] `ModelEvalPanel` trong Cài đặt → Vai trò.
- [ ] Ánh xạ mã lỗi `errors.json` cho các mã Plan §23.1.D.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | `countSyllables` khớp golden (cùng file với Python) | `fe/src/shared/lib/vi/syllables.test.ts` |
| unit | `normalizePaste`: NFD → NFC, bỏ U+200B/U+FEFF; `detectLegacyEncoding` nhận mẫu TCVN3/VNI | `fe/src/shared/lib/vi/nfc.test.ts` |
| component | `SlopListEditor` thêm regex sai → hiện lỗi; tắt mục có sẵn → gửi `disabled` | `fe/src/features/language/components/SlopListEditor.test.tsx` |
| component | `LanguageFindingItem` hiển thị chữ + icon theo mức độ, bấm nhảy đoạn | `fe/src/features/language/components/LanguageFindingItem.test.tsx` |
| component | i18n: mọi khóa dùng trong code tồn tại trong `vi/*.json` (script quét) | `fe/tests/i18n/keys.test.ts` |
| e2e (mock backend) | Dán văn bản TCVN3 → hộp xác nhận → nội dung Unicode trong editor | `fe/tests/e2e/language-paste.spec.ts` |
| e2e (mock backend) | Đổi kiểu bỏ dấu ở Story Bible → cảnh báo số chương khác kiểu | `fe/tests/e2e/style-profile.spec.ts` |

Luồng: [T13](../../tests/flows/T13-kiem-tra-tieng-viet.md), phần IME/dán của [T12](../../tests/flows/T12-editor-autosave-ime.md).

## Tên mới đề xuất

- Thư mục `fe/src/features/language/`, `fe/src/shared/lib/vi/`; file `shared/i18n/index.ts`, `i18next.d.ts`, `format.ts`, `errors.ts`.
- Route `/settings/language`, `/works/$workId/bible/style`.
- Namespace i18n: `common`, `errors`, `library`, `editor`, `ai`, `continuity`, `bible`, `settings`, `language`, `review`, `jobs`.
- Fixture dùng chung `tests/fixtures/language/vi/length_cases.json`.
