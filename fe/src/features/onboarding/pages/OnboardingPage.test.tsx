import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OnboardingPage } from "./OnboardingPage";

vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("@/shared/api/client", () => ({ currentSession: () => null, createApiClient: vi.fn() }));

describe("OnboardingPage", () => {
  it("shows the data-root step before the security choice", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><OnboardingPage /></QueryClientProvider>);
    expect(screen.getByRole("heading", { name: "Thư mục dữ liệu" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tiếp tục" })).toBeTruthy();
    expect(screen.getByRole("list", { name: "Các bước thiết lập" })).toBeTruthy();
  });
});
