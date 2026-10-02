// Kiểu tạm viết tay cho base. Từ S05, DTO lấy từ `generated/schema.d.ts` (sinh từ OpenAPI);
// không khai báo trùng DTO ở đây nữa (Plan §8).

export type ErrorAction =
  | "retry"
  | "reload"
  | "wait"
  | "view_diff"
  | "open_resync"
  | "unlock_vault"
  | "open_provider_settings"
  | "edit_instruction"
  | "change_model"
  | "adjust_budget";

export interface ErrorResponse {
  code: string;
  message: string;
  detail?: Record<string, unknown> | null;
  retryable: boolean;
  action?: ErrorAction | null;
  request_id?: string | null;
}

export interface EventEnvelope {
  v: number;
  seq: number;
  ts: string;
  type: string;
  work_id?: string | null;
  job_id?: string | null;
  chapter_no?: number | null;
  payload: Record<string, unknown>;
}

export interface HealthResponse {
  status: "ok";
  protocol_version: number;
  app_version: string;
  schema_version: string | null;
  data_id: string | null;
  started_at: string;
  pid: number;
}
