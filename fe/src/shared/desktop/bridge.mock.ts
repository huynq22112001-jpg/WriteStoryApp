import type { BackendSession, BootState } from "./types";

const initialState: BootState = {
  phase: "ready",
  platform: "web",
  restart_count: 0,
};

let state = initialState;
let listeners = new Set<(state: BootState) => void>();
let selectedFolder: string | null = null;

export async function mockGetBootState(): Promise<BootState> {
  return state;
}

export async function mockOnBootState(callback: (state: BootState) => void) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

export async function mockPickDataRootFolder(): Promise<string | null> {
  return selectedFolder;
}

export async function mockConfirmDataRoot(path: string): Promise<BootState> {
  state = { ...state, phase: "starting_backend", data_root: path, progress: { stage: "starting" } };
  listeners.forEach((listener) => listener(state));
  return state;
}

export async function mockGetBackendSession(): Promise<BackendSession | null> {
  const baseUrl = import.meta.env.VITE_DEV_BACKEND_URL;
  const token = import.meta.env.VITE_DEV_BACKEND_TOKEN;
  if (!baseUrl || !token) return null;
  return { base_url: baseUrl.replace(/\/$/, ""), token, protocol_version: 1 };
}

export async function mockRestartBackend(): Promise<BootState> {
  state = { ...state, phase: "ready", restart_count: state.restart_count + 1, error: undefined };
  listeners.forEach((listener) => listener(state));
  return state;
}

export async function mockOpenLogsFolder(): Promise<void> {}
export async function mockQuitApp(): Promise<void> {}

/** Helpers reserved for component tests. */
export function setMockBootState(next: BootState) {
  state = next;
  listeners.forEach((listener) => listener(state));
}

export function setMockSelectedFolder(path: string | null) {
  selectedFolder = path;
}

export function resetMockBridge() {
  state = initialState;
  selectedFolder = null;
  listeners = new Set();
}
