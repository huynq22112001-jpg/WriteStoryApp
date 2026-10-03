export type BootPhase =
  | "resolving_data_root"
  | "needs_data_root"
  | "translocated"
  | "data_root_error"
  | "locked_by_other_instance"
  | "starting_backend"
  | "ready"
  | "backend_crashed"
  | "startup_failed"
  | "protocol_mismatch"
  | "shutting_down";

export interface BootState {
  phase: BootPhase;
  platform: string;
  data_root?: string;
  data_id?: string;
  error?: { code: string; message: string; detail?: unknown };
  backend?: { base_url: string; protocol_version: number; pid: number };
  restart_count: number;
  progress?: { stage: string };
}

export interface BackendSession {
  base_url: string;
  token: string;
  protocol_version: number;
}
