export interface BackendSession {
  baseUrl: string;
  token: string;
}

/**
 * Lấy URL + token của backend.
 * - Trình duyệt dev (S06): đọc `VITE_DEV_BACKEND_URL` / `VITE_DEV_BACKEND_TOKEN`.
 * - Desktop (S07): gọi Tauri command `get_backend_session`; token không bao giờ nằm trong URL.
 */
export async function getBackendSession(): Promise<BackendSession | null> {
  const baseUrl = import.meta.env.VITE_DEV_BACKEND_URL;
  const token = import.meta.env.VITE_DEV_BACKEND_TOKEN;
  if (!baseUrl || !token) return null;
  return { baseUrl: baseUrl.replace(/\/$/, ""), token };
}
