import { describe, expect, it } from "vitest";

import fixture from "./types.fixture.json";
import type { BackendSession, BootState, BootPhase } from "./types";

const bootState: BootState = { ...fixture.bootState, phase: fixture.bootState.phase as BootPhase };
const backendSession: BackendSession = fixture.backendSession;

describe("desktop Rust JSON fixture", () => {
  it("matches the snake_case BootState and BackendSession contract", () => {
    expect(bootState.backend?.base_url).toBe("http://127.0.0.1:54321");
    expect(bootState.restart_count).toBe(0);
    expect(backendSession.protocol_version).toBe(1);
  });
});
