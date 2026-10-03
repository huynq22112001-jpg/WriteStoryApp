import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setMockBootState, resetMockBridge } from "@/shared/desktop/bridge.mock";
import { clearSession, currentSession } from "@/shared/api/client";
import * as eventBus from "@/shared/api/eventBus";

import { BootGate } from "./BootGate";
import { useBootStore } from "./store";
import { AppProviders } from "../providers";

const testCases = [
  ["resolving_data_root", "Đang khởi động WriteStoryApp…"],
  ["needs_data_root", "Chọn thư mục dữ liệu"],
  ["translocated", "Di chuyển ứng dụng vào Applications"],
  ["data_root_error", "Chọn thư mục dữ liệu"],
  ["locked_by_other_instance", "Dữ liệu đang được ứng dụng khác sử dụng"],
  ["starting_backend", "Đang khởi động WriteStoryApp…"],
  ["ready", "Thư viện"],
  ["backend_crashed", "Backend đã dừng bất ngờ"],
  ["startup_failed", "Không thể khởi động backend"],
  ["protocol_mismatch", "Không thể khởi động backend"],
  ["shutting_down", "Đang đóng WriteStoryApp…"],
] as const;

function renderGate() {
  return render(<AppProviders><BootGate /></AppProviders>);
}

describe("BootGate", () => {
  beforeEach(() => {
    resetMockBridge();
    clearSession();
    useBootStore.setState({
      bootState: { phase: "resolving_data_root", platform: "web", restart_count: 0 },
      session: null,
      connection: "closed",
    });
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it.each(testCases)("renders the expected screen for %s", async (phase, title) => {
    setMockBootState({
      phase,
      platform: "test",
      restart_count: 0,
      error: phase === "backend_crashed" ? { code: "BACKEND_EXITED", message: "exited" } : undefined,
    });
    renderGate();
    expect((await screen.findAllByText(title)).length).toBeGreaterThan(0);
  });

  it("subscribes before reading the snapshot and keeps the newer boot event", async () => {
    renderGate();
    setMockBootState({ phase: "backend_crashed", platform: "test", restart_count: 1 });
    expect(await screen.findByText("Backend đã dừng bất ngờ")).toBeInTheDocument();
    await waitFor(() => expect(useBootStore.getState().bootState.phase).toBe("backend_crashed"));
  });

  it("clears and reinstalls the in-memory session across a crash and restart", async () => {
    vi.stubEnv("VITE_DEV_BACKEND_URL", "http://127.0.0.1:8765");
    vi.stubEnv("VITE_DEV_BACKEND_TOKEN", "test-token");
    vi.spyOn(eventBus, "startEventBus").mockReturnValue(() => {});
    setMockBootState({ phase: "ready", platform: "test", restart_count: 0 });
    renderGate();

    await waitFor(() => expect(currentSession()?.token).toBe("test-token"));
    setMockBootState({ phase: "backend_crashed", platform: "test", restart_count: 0 });
    expect(await screen.findByText("Backend đã dừng bất ngờ")).toBeInTheDocument();
    await waitFor(() => expect(currentSession()).toBeNull());

    setMockBootState({ phase: "ready", platform: "test", restart_count: 1 });
    await waitFor(() => expect(currentSession()?.token).toBe("test-token"));
  });
});
