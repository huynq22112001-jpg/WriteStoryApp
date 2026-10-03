import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ModelsSettingsPage } from "./ModelsSettingsPage";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ currentSession: () => ({}), createApiClient: () => api }));

describe("ModelsSettingsPage", () => {
  afterEach(cleanup);
  beforeEach(() => { api.get.mockReset(); api.post.mockReset(); api.put.mockReset().mockResolvedValue({}); api.patch.mockReset(); });
  it("offers provider protocols and separates model, role and limit settings", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ModelsSettingsPage /></QueryClientProvider>);
    expect(screen.getByRole("heading", { name: "Mô hình AI" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "OpenAI-compatible" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Ollama / LM Studio" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Vai trò & effort" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Đồng thời & ngân sách" })).toBeTruthy();
  });

  it("edits a model display name and persists it with the model list", async () => {
    api.get.mockImplementation((path: string) => {
      if (path === "/v1/providers") return Promise.resolve([{ id: "p1", name: "Provider", protocol: "anthropic", base_url: "https://api.example.test", has_key: true, revision: 1, discovery_status: "ok", default_effort: null, auto_discover: true, prefer_long_context: false }]);
      if (path === "/v1/providers/p1/models") return Promise.resolve({ revision: 4, effective: [{ model_id: "m1", display_name: null, supported_efforts: ["low", "high"] }], others: [], default_model_id: "m1" });
      return Promise.resolve({});
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ModelsSettingsPage /></QueryClientProvider>);
    await screen.findAllByText("m1");
    fireEvent.click(screen.getByRole("button", { name: "Đổi tên m1" }));
    const input = screen.getByRole("textbox", { name: "Tên hiển thị m1" });
    fireEvent.change(input, { target: { value: "Tên model" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu tên" }));
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/v1/providers/p1/models", { expected_revision: 4, items: [{ model_id: "m1", display_name: "Tên model" }] }));
  });

  it("checks a provider connection and requests model discovery", async () => {
    api.get.mockImplementation((path: string) => path === "/v1/providers"
      ? Promise.resolve([{ id: "p1", name: "Provider", protocol: "anthropic", base_url: "https://api.example.test", has_key: true, revision: 1, discovery_status: "idle", default_effort: null, auto_discover: true, prefer_long_context: false }])
      : Promise.resolve({ revision: 1, effective: [], others: [], default_model_id: null }));
    api.post.mockImplementation((path: string) => Promise.resolve(path === "/v1/providers/test" ? { ok: true, latency_ms: 12 } : { status: "ok", found: 2 }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ModelsSettingsPage /></QueryClientProvider>);
    await screen.findByText("Provider");
    await waitFor(() => expect((screen.getByLabelText("Địa chỉ API") as HTMLInputElement).value).toBe("https://api.example.test"));
    fireEvent.click(screen.getAllByRole("button", { name: "Kiểm tra kết nối" }).at(-1)!);
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/v1/providers/test", expect.objectContaining({ protocol: "anthropic", base_url: "https://api.example.test" })));
    fireEvent.click(screen.getAllByRole("button", { name: "Lấy danh sách model" }).at(-1)!);
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/v1/providers/p1/discover", {}));
  });

  it("shows supported effort values for each assigned model", async () => {
    api.get.mockImplementation((path: string) => {
      if (path === "/v1/providers") return Promise.resolve([{ id: "p1", name: "Provider", protocol: "anthropic", base_url: "https://api.example.test", has_key: true, revision: 1, discovery_status: "ok", default_effort: null, auto_discover: true, prefer_long_context: false }]);
      if (path === "/v1/providers/p1/models") return Promise.resolve({ revision: 4, effective: [{ model_id: "m1", display_name: null, supported_efforts: ["low", "high"] }, { model_id: "m2", display_name: null, supported_efforts: ["medium"] }], others: [], default_model_id: "m1" });
      if (path === "/v1/settings/roles") return Promise.resolve({ roles: [{ role: "writer", provider_id: "p1", model_id: "m1", effort: null }] });
      return Promise.resolve({});
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ModelsSettingsPage /></QueryClientProvider>);
    await screen.findAllByText("m1");
    expect(screen.getByText("Mặc định")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Vai trò & effort" }).at(-1)!);
    const effort = await screen.findByRole("combobox", { name: "Effort writer" });
    await waitFor(() => expect(Array.from((effort as HTMLSelectElement).options).map((option) => option.value)).toEqual(["", "low", "high"]));
    expect((screen.getByLabelText("Effort planner") as HTMLSelectElement).disabled).toBe(true);
  });

  it("saves role assignments and provider concurrency settings", async () => {
    api.get.mockImplementation((path: string) => {
      if (path === "/v1/providers") return Promise.resolve([{ id: "p1", name: "Provider", protocol: "anthropic", base_url: "https://api.example.test", has_key: true, revision: 1, discovery_status: "ok", default_effort: null, auto_discover: true, prefer_long_context: false }]);
      if (path === "/v1/providers/p1/models") return Promise.resolve({ revision: 4, effective: [{ model_id: "m1", display_name: null, supported_efforts: ["low", "high"] }], others: [], default_model_id: "m1" });
      if (path === "/v1/settings/roles") return Promise.resolve({ roles: [{ role: "writer", provider_id: "p1", model_id: null, effort: null }] });
      if (path === "/v1/providers/p1/limits") return Promise.resolve({ max_concurrent_requests: 4, rpm: 60, tpm: 10000, max_retries: 3 });
      if (path === "/v1/settings/limits") return Promise.resolve({ worker_pool: 4, app_daily_usd: 50, app_daily_tokens: 500000, work_daily_usd_default: 10, timezone: "Asia/Bangkok", autowrite_mode_default: "review_each", review_every_k: 5, max_repair_rounds: 2, chapter_length_min: 1500, chapter_length_max: 2500 });
      return Promise.resolve({});
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ModelsSettingsPage /></QueryClientProvider>);
    await screen.findAllByText("m1");
    fireEvent.click(screen.getAllByRole("button", { name: "Vai trò & effort" }).at(-1)!);
    await screen.findAllByRole("combobox", { name: "Effort writer" });
    fireEvent.change(screen.getAllByRole("combobox", { name: "Effort writer" }).at(-1)!, { target: { value: "high" } });
    fireEvent.change(screen.getAllByLabelText("Viết").at(-1)!, { target: { value: "m1" } });
    fireEvent.change(screen.getAllByRole("combobox", { name: "Effort writer" }).at(-1)!, { target: { value: "high" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Lưu vai trò" }).at(-1)!);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/v1/settings/roles", expect.objectContaining({ roles: expect.any(Array) })));
    fireEvent.click(screen.getAllByRole("button", { name: "Đồng thời & ngân sách" }).at(-1)!);
    await screen.findByRole("heading", { name: "Giới hạn của provider" });
    fireEvent.click(screen.getAllByRole("button", { name: "Lưu giới hạn" }).at(-1)!);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/v1/providers/p1/limits", expect.objectContaining({ max_concurrent_requests: 4, max_retries: 3 })));
  });

  it("saves app budget and writing defaults", async () => {
    api.get.mockImplementation((path: string) => {
      if (path === "/v1/providers") return Promise.resolve([{ id: "p1", name: "Provider", protocol: "anthropic", base_url: "https://api.example.test", has_key: true, revision: 1, discovery_status: "ok", default_effort: null, auto_discover: true, prefer_long_context: false }]);
      if (path === "/v1/providers/p1/models") return Promise.resolve({ revision: 1, effective: [], others: [], default_model_id: null });
      if (path === "/v1/providers/p1/limits") return Promise.resolve({ max_concurrent_requests: 4, rpm: null, tpm: null, max_retries: 3 });
      if (path === "/v1/settings/limits") return Promise.resolve({ worker_pool: 4, app_daily_usd: 50, app_daily_tokens: 500000, work_daily_usd_default: 10, timezone: "Asia/Bangkok", autowrite_mode_default: "review_each", review_every_k: 5, max_repair_rounds: 2, chapter_length_min: 1500, chapter_length_max: 2500 });
      return Promise.resolve({});
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ModelsSettingsPage initialTab="limits" /></QueryClientProvider>);
    await screen.findByRole("heading", { name: "Đồng thời & ngân sách toàn ứng dụng" });
    await waitFor(() => expect((screen.getByLabelText("Ngân sách mỗi ngày (USD)") as HTMLInputElement).value).toBe("50"));
    fireEvent.click(screen.getAllByRole("button", { name: "Lưu ngân sách" }).at(-1)!);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/v1/settings/limits", expect.objectContaining({ worker_pool: 4, app_daily_usd: 50, timezone: "Asia/Bangkok", chapter_length_min: 1500, chapter_length_max: 2500 })));
  });
});
