import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VaultUnlockDialog } from "./VaultUnlockDialog";

const post = vi.hoisted(() => vi.fn());
vi.mock("@/shared/api/client", () => ({ currentSession: () => ({}), createApiClient: () => ({ post }) }));

describe("VaultUnlockDialog", () => {
  beforeEach(() => post.mockReset());

  it("opens on a vault request and clears the password after successful unlock", async () => {
    post.mockResolvedValue({ state: "unlocked" });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><VaultUnlockDialog waitingJobs={2} /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: /mở khóa vault/i }));
    expect(await screen.findByText("2 tác vụ đang chờ vault.")).toBeTruthy();
    const input = await screen.findByLabelText("Mật khẩu vault");
    fireEvent.change(input, { target: { value: "bí mật không được lưu" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Mở khóa" }).at(-1)!);
    await waitFor(() => expect(post).toHaveBeenCalledWith("/v1/vault/unlock", { password: "bí mật không được lưu" }));
    await waitFor(() => expect(screen.queryByDisplayValue("bí mật không được lưu")).toBeNull());
  });
});
