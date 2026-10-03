import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

import * as mock from "./bridge.mock";
import type { BackendSession, BootState } from "./types";

export type { BackendSession, BootPhase, BootState } from "./types";

export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export async function getBootState(): Promise<BootState> {
  return isTauri() ? invoke<BootState>("get_boot_state") : mock.mockGetBootState();
}

export async function onBootState(callback: (state: BootState) => void): Promise<() => void> {
  return isTauri()
    ? listen<BootState>("boot:state", (event) => callback(event.payload))
    : mock.mockOnBootState(callback);
}

export async function pickDataRootFolder(): Promise<string | null> {
  return isTauri() ? invoke<string | null>("pick_data_root_folder") : mock.mockPickDataRootFolder();
}

export async function confirmDataRoot(
  path: string,
  acceptCloudSyncWarning = false,
): Promise<BootState> {
  return isTauri()
    ? invoke<BootState>("confirm_data_root", {
        path,
        accept_cloud_sync_warning: acceptCloudSyncWarning,
      })
    : mock.mockConfirmDataRoot(path);
}

/** Tauri returns a token held only in this page's RAM; web dev reads Vite env. */
export async function getBackendSession(): Promise<BackendSession | null> {
  if (isTauri()) return invoke<BackendSession>("get_backend_session");
  return mock.mockGetBackendSession();
}

export async function restartBackend(): Promise<BootState> {
  return isTauri() ? invoke<BootState>("restart_backend") : mock.mockRestartBackend();
}

export async function openLogsFolder(): Promise<void> {
  if (isTauri()) return invoke("open_logs_folder");
  return mock.mockOpenLogsFolder();
}

export async function quitApp(): Promise<void> {
  if (isTauri()) return invoke("quit_app");
  return mock.mockQuitApp();
}
