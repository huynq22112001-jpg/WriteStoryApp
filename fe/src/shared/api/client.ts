import type { BackendSession } from "@/shared/desktop/bridge";

import { networkError, toApiError } from "./errors";

export interface RequestOptions {
  signal?: AbortSignal;
  /** Bắt buộc với POST tạo job (F01 §A.6). Mỗi thao tác người dùng một key. */
  idempotencyKey?: string;
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

export interface ApiClient {
  get<T>(path: string, options?: RequestOptions): Promise<T>;
  post<T>(path: string, body: unknown, options?: RequestOptions): Promise<T>;
}

export function createApiClient(session: BackendSession): ApiClient {
  async function request<T>(
    method: string,
    path: string,
    body: unknown,
    options: RequestOptions = {},
  ): Promise<T> {
    const headers: Record<string, string> = { Authorization: `Bearer ${session.token}` };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

    let response: Response;
    try {
      response = await fetch(`${session.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: options.signal,
      });
    } catch (cause) {
      throw networkError(cause);
    }
    if (!response.ok) throw await toApiError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    get: (path, options) => request("GET", path, undefined, options),
    post: (path, body, options) => request("POST", path, body, options),
  };
}
