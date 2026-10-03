import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ErrorState } from "./states";

describe("ErrorState", () => {
  it("runs retry action and shows a useful label", () => {
    const retry = vi.fn();
    render(<ErrorState title="Không tải được" action="retry" onRetry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("opens the vault dialog through the registered action event", () => {
    const listener = vi.fn();
    window.addEventListener("vault:unlock-requested", listener);
    render(<ErrorState title="Vault đang khóa" action="unlock_vault" />);
    fireEvent.click(screen.getByRole("button", { name: "Mở khóa vault" }));
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener("vault:unlock-requested", listener);
  });
});
