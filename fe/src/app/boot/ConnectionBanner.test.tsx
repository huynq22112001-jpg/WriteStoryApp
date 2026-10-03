import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useBootStore } from "./store";
import { ConnectionBanner } from "./ConnectionBanner";

describe("ConnectionBanner", () => {
  afterEach(() => vi.useRealTimers());

  it("appears after two seconds reconnecting and hides after reconnect", () => {
    vi.useFakeTimers();
    useBootStore.setState({ connection: "reconnecting" });
    render(<ConnectionBanner />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(2000));
    expect(screen.getByRole("status")).toHaveTextContent("Mất kết nối tới backend");
    act(() => useBootStore.setState({ connection: "open" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
