import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NewWorkPage } from "./NewWorkPage";

vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn(), useSearch: () => ({ workId: undefined, step: undefined }) }));
vi.mock("@/shared/api/client", () => ({ currentSession: () => null, createApiClient: vi.fn(), newIdempotencyKey: () => "id" }));

describe("NewWorkPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the seven wizard steps and starts at the basics page", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><NewWorkPage /></QueryClientProvider>);
    expect(screen.getByRole("heading", { name: "Tạo truyện mới" })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Các bước tạo truyện" }).querySelectorAll("button")).toHaveLength(7);
    expect(screen.getByLabelText("Tên truyện")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Quay lại" })).toHaveProperty("disabled", true);
  });
});
