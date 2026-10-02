import type { ErrorAction, ErrorResponse } from "./types";

/** Lỗi API theo hợp đồng Plan §23.1.D. `code = "NETWORK"` khi không tới được backend. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly detail: Record<string, unknown> | null;
  readonly retryable: boolean;
  readonly action: ErrorAction | null;
  readonly requestId: string | null;

  constructor(body: ErrorResponse, status: number) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.status = status;
    this.detail = body.detail ?? null;
    this.retryable = body.retryable;
    this.action = body.action ?? null;
    this.requestId = body.request_id ?? null;
  }
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as ErrorResponse).code === "string" &&
    typeof (value as ErrorResponse).retryable === "boolean"
  );
}

export async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Body không phải JSON (proxy, lỗi lạ): vẫn trả ApiError có mã để UI xử lý thống nhất.
  }
  if (isErrorResponse(body)) {
    return new ApiError(body, response.status);
  }
  return new ApiError(
    {
      code: "INTERNAL",
      message: `HTTP ${response.status}`,
      retryable: response.status >= 500,
      request_id: response.headers.get("X-Request-Id"),
    },
    response.status,
  );
}

export function networkError(cause: unknown): ApiError {
  const error = new ApiError(
    { code: "NETWORK", message: "Không kết nối được tới backend", retryable: true, action: "retry" },
    0,
  );
  error.cause = cause;
  return error;
}
