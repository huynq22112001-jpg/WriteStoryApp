import { beforeEach, describe, expect, it, vi } from "vitest";

import { getBackendSession, isTauri } from "./bridge";

describe("desktop bridge", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_DEV_BACKEND_URL", "http://localhost:8765/");
    vi.stubEnv("VITE_DEV_BACKEND_TOKEN", "dev-token");
    localStorage.clear();
    sessionStorage.clear();
  });

  it("uses the web mock outside Tauri and reads only the dev environment", async () => {
    expect(isTauri()).toBe(false);
    await expect(getBackendSession()).resolves.toEqual({
      base_url: "http://localhost:8765",
      token: "dev-token",
      protocol_version: 1,
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
