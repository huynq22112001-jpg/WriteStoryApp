export type ErrorAction =
  | "retry"
  | "reload"
  | "wait"
  | "unlock_vault"
  | "open_provider_settings"
  | "open_resync"
  | "view_diff"
  | "edit_instruction"
  | "change_model"
  | "adjust_budget";

export function runErrorAction(action: ErrorAction, retry?: () => void) {
  if (action === "retry") return retry?.();
  if (action === "reload") return window.location.reload();
  if (action === "open_provider_settings" || action === "change_model") {
    window.location.hash = "#/settings/models";
    return;
  }
  if (action === "unlock_vault") {
    window.dispatchEvent(new CustomEvent("vault:unlock-requested"));
    return;
  }
  window.dispatchEvent(new CustomEvent("app:error-action", { detail: { action } }));
}

export const errorActionLabels: Partial<Record<ErrorAction, string>> = {
  retry: "Thử lại",
  reload: "Tải lại ứng dụng",
  wait: "Đóng",
  unlock_vault: "Mở khóa vault",
  open_provider_settings: "Mở cài đặt model",
  open_resync: "Mở đồng bộ lại",
  view_diff: "Xem so sánh",
  edit_instruction: "Sửa hướng dẫn",
  change_model: "Đổi model",
  adjust_budget: "Điều chỉnh ngân sách",
};
