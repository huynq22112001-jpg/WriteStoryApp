import { describe, expect, it } from "vitest";

import { errorMessage } from "@/shared/i18n";

import { ApiError, networkError, toApiError } from "./errors";

describe("toApiError", () => {
  it("đọc ErrorResponse theo hợp đồng", async () => {
    const response = new Response(
      JSON.stringify({
        code: "REVISION_CONFLICT",
        message: "Nội dung đã thay đổi",
        detail: { current_revision: 4 },
        retryable: false,
        action: "view_diff",
        request_id: "abc",
      }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );
    const error = await toApiError(response);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("REVISION_CONFLICT");
    expect(error.status).toBe(409);
    expect(error.action).toBe("view_diff");
    expect(error.detail).toEqual({ current_revision: 4 });
    expect(error.requestId).toBe("abc");
  });

  it("body không phải JSON vẫn thành ApiError có mã", async () => {
    const response = new Response("Bad gateway", {
      status: 502,
      headers: { "X-Request-Id": "r1" },
    });
    const error = await toApiError(response);
    expect(error.code).toBe("INTERNAL");
    expect(error.retryable).toBe(true);
    expect(error.requestId).toBe("r1");
  });

  it("lỗi mạng có mã NETWORK và thông báo tiếng Việt", () => {
    const error = networkError(new TypeError("Failed to fetch"));
    expect(error.code).toBe("NETWORK");
    expect(errorMessage(error.code)).toBe("Không kết nối được tới backend.");
  });

  it("mã lạ dùng thông điệp dự phòng từ BE", () => {
    expect(errorMessage("MA_CHUA_CO", "Thông điệp BE")).toBe("Thông điệp BE");
  });
});
