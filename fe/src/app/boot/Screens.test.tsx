import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as bridge from "@/shared/desktop/bridge";

import { DataRootScreen } from "./Screens";

describe("DataRootScreen", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("asks before accepting a cloud-synced data-root and retries with the flag", async () => {
    const command = vi.spyOn(bridge, "confirmDataRoot")
      .mockRejectedValueOnce(new Error("DATA_ROOT_CLOUD_SYNC: cloud folder"))
      .mockResolvedValue({ phase: "starting_backend", platform: "test", restart_count: 0 });
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<DataRootScreen state={{
      phase: "needs_data_root",
      platform: "test",
      data_root: "C:/Stories",
      restart_count: 0,
    }} />);

    fireEvent.click(screen.getByRole("button", { name: "Dùng thư mục này" }));
    await waitFor(() => expect(command).toHaveBeenCalledTimes(2));
    expect(command).toHaveBeenNthCalledWith(1, "C:/Stories", false);
    expect(command).toHaveBeenNthCalledWith(2, "C:/Stories", true);
    expect(window.confirm).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
