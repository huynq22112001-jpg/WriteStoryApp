import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import common from "./vi/common.json";
import errors from "./vi/errors.json";
import boot from "./vi/boot.json";

// Đa ngôn ngữ về kiến trúc, MVP chỉ có tiếng Việt (Plan §1). Thêm ngôn ngữ = thêm thư mục <lang>/.
export const resources = {
  vi: { common, errors, boot },
} as const;

void i18n.use(initReactI18next).init({
  resources,
  lng: "vi",
  fallbackLng: "vi",
  defaultNS: "common",
  ns: ["common", "errors", "boot"],
  interpolation: { escapeValue: false },
});

/** Thông báo lỗi theo `code` (FE ưu tiên i18n; `message` từ BE là bản dự phòng – §23.1.D). */
export function errorMessage(code: string, fallback?: string): string {
  return i18n.exists(code, { ns: "errors" }) ? i18n.t(code, { ns: "errors" }) : (fallback ?? code);
}

export default i18n;
