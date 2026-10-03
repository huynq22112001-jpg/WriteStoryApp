import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SecuritySettingsPage } from "./SecuritySettingsPage";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ currentSession: () => ({}), createApiClient: () => api, newIdempotencyKey: () => "key" }));

describe("SecuritySettingsPage", () => {
  afterEach(cleanup);
  beforeEach(() => {
    api.get.mockReset().mockImplementation((path: string) => Promise.resolve(path === "/v1/vault/status" ? { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } : []));
    api.post.mockReset().mockResolvedValue({});
    api.delete.mockReset().mockResolvedValue({});
  });
  it("does not display API key values and explains the secret list", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><SecuritySettingsPage /></QueryClientProvider>);
    expect(screen.getByRole("heading", { name: "Bảo mật & API key" })).toBeTruthy();
    expect(screen.getByText(/không hiển thị giá trị/i)).toBeTruthy();
  });

  it("creates a vault using a password pair without exposing saved keys", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><SecuritySettingsPage /></QueryClientProvider>);
    fireEvent.change(await screen.findByLabelText("Mật khẩu mới"), { target: { value: "mot mat khau dai hon 12" } });
    fireEvent.change(screen.getByLabelText("Nhập lại mật khẩu"), { target: { value: "mot mat khau dai hon 12" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Tạo vault" }).at(-1)!);
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/v1/vault", { password: "mot mat khau dai hon 12", password_confirm: "mot mat khau dai hon 12", import_session_secrets: true }));
  });
});
