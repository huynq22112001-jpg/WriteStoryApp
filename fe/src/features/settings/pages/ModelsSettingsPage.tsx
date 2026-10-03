import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Plus, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currentSession, createApiClient } from "@/shared/api/client";

type Provider = { id: string; name: string; protocol: "anthropic" | "openai_compatible" | "ollama_lmstudio"; base_url: string; has_key: boolean; revision: number; discovery_status: string; default_effort: string | null; auto_discover: boolean; prefer_long_context: boolean };
type Model = { model_id: string; display_name: string | null; source: string; missing_since: string | null; max_input_tokens: number | null; max_tokens: number | null; supported_efforts: string[] | null; price_input_per_mtok: number | null; price_output_per_mtok: number | null; allowed_roles: string[] | null; max_concurrent_requests: number | null };
type ModelList = { revision: number; effective: Model[]; others: Model[]; default_model_id: string | null };
const roles = ["planner", "writer", "checker", "reviewer", "summary"] as const;

export function ModelsSettingsPage({ initialTab = "models" }: { initialTab?: "models" | "roles" | "limits" }) {
  const session = currentSession();
  const api = session ? createApiClient(session) : null;
  const cache = useQueryClient();
  const [providerId, setProviderId] = useState("");
  const [tab, setTab] = useState<"models" | "roles" | "limits">(initialTab);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.anthropic.com");
  const [key, setKey] = useState("");
  const [protocol, setProtocol] = useState<"anthropic" | "openai_compatible" | "ollama_lmstudio">("anthropic");
  const [defaultEffort, setDefaultEffort] = useState("");
  const [autoDiscover, setAutoDiscover] = useState(true);
  const [preferLongContext, setPreferLongContext] = useState(false);
  const [renamingModel, setRenamingModel] = useState<string | null>(null);
  const [modelDisplayName, setModelDisplayName] = useState("");
  const providersQuery = useQuery({ queryKey: ["providers"], enabled: !!api, queryFn: () => api!.get<Provider[]>("/v1/providers") });
  const providers = providersQuery.data ?? [];
  useEffect(() => { if (!providerId && providers[0]) setProviderId(providers[0].id); }, [providerId, providers]);
  useEffect(() => {
    const provider = providers.find((item) => item.id === providerId);
    if (!provider) return;
    setName(provider.name); setBaseUrl(provider.base_url); setProtocol(provider.protocol);
    setDefaultEffort(provider.default_effort ?? ""); setAutoDiscover(provider.auto_discover);
    setPreferLongContext(provider.prefer_long_context);
  }, [providerId, providers]);
  const modelsQuery = useQuery({ queryKey: ["provider-models", providerId], enabled: !!api && !!providerId, queryFn: () => api!.get<ModelList>(`/v1/providers/${providerId}/models`) });
  const rolesQuery = useQuery({ queryKey: ["roles"], enabled: !!api && tab === "roles", queryFn: () => api!.get<{ roles: { role: string; provider_id: string | null; model_id: string | null; effort: string | null }[] }>("/v1/settings/roles") });
  const limitsQuery = useQuery({ queryKey: ["provider-limits", providerId], enabled: !!api && !!providerId && tab === "limits", queryFn: () => api!.get<{ max_concurrent_requests: number; rpm: number | null; tpm: number | null; max_retries: number }>(`/v1/providers/${providerId}/limits`) });
  const appLimitsQuery = useQuery({ queryKey: ["settings-limits"], enabled: !!api && tab === "limits", queryFn: () => api!.get<{ worker_pool: number; app_daily_usd: number | null; app_daily_tokens: number | null; work_daily_usd_default: number | null; timezone: string; autowrite_mode_default: string; review_every_k: number; max_repair_rounds: number; chapter_length_min: number; chapter_length_max: number }>("/v1/settings/limits") });
  const [roleModels, setRoleModels] = useState<Record<string, string>>({});
  const [roleEfforts, setRoleEfforts] = useState<Record<string, string>>({});
  useEffect(() => { const next: Record<string, string> = {}; const efforts: Record<string, string> = {}; for (const row of rolesQuery.data?.roles ?? []) { next[row.role] = row.model_id ?? ""; efforts[row.role] = row.effort ?? ""; } setRoleModels(next); setRoleEfforts(efforts); }, [rolesQuery.data]);
  const list = modelsQuery.data;

  async function addProvider(event: React.FormEvent) {
    event.preventDefault(); if (!api || !name.trim()) return;
    try {
      const created = await api.post<Provider>("/v1/providers", { name: name.trim(), protocol, base_url: baseUrl, api_key: key || undefined, key_storage: key ? "session" : "none", auto_discover: autoDiscover, prefer_long_context: preferLongContext, default_effort: defaultEffort || null });
      setKey(""); setProviderId(created.id); setName("");
      await cache.invalidateQueries({ queryKey: ["providers"] });
      toast.success("Đã thêm nhà cung cấp");
    } catch { toast.error("Không thể thêm nhà cung cấp"); }
  }

  async function testConnection() {
    if (!api) return;
    try {
      const result = await api.post<{ ok: boolean; latency_ms: number; error?: { message?: string } }>("/v1/providers/test", { protocol, base_url: baseUrl, api_key: key || undefined });
      if (result.ok) toast.success(`Kết nối thành công · ${result.latency_ms} ms`);
      else toast.error(result.error?.message ?? "Provider chưa phản hồi thành công");
    } catch { toast.error("Không kết nối được provider. Kiểm tra địa chỉ và API key."); }
  }

  async function saveProvider() {
    const provider = providers.find((item) => item.id === providerId);
    if (!api || !provider) return;
    try {
      await api.patch(`/v1/providers/${provider.id}`, { expected_revision: provider.revision, name: name.trim(), protocol, base_url: baseUrl, api_key: key || undefined, key_storage: key ? "session" : undefined, auto_discover: autoDiscover, prefer_long_context: preferLongContext, default_effort: defaultEffort || null });
      setKey(""); await cache.invalidateQueries({ queryKey: ["providers"] }); toast.success("Đã lưu cấu hình provider");
    } catch { toast.error("Không lưu được cấu hình provider; có thể cấu hình đã đổi ở nơi khác"); }
  }

  async function discover() {
    if (!api || !providerId) return;
    try { const result = await api.post<{ status: string; found: number }>(`/v1/providers/${providerId}/discover`, {}); await cache.invalidateQueries({ queryKey: ["provider-models", providerId] }); await cache.invalidateQueries({ queryKey: ["providers"] }); toast[result.status === "ok" ? "success" : "warning"](result.status === "ok" ? `Đã tìm thấy ${result.found} model` : "Không lấy được danh sách model"); }
    catch { toast.error("Không thể kết nối provider"); }
  }

  async function moveModel(index: number, delta: -1 | 1) {
    await reorderModel(index, index + delta);
  }

  async function reorderModel(index: number, target: number) {
    if (!api || !list) return;
    const items = [...list.effective];
    if (target < 0 || target >= items.length) return;
    [items[index], items[target]] = [items[target]!, items[index]!];
    try { await api.put(`/v1/providers/${providerId}/models`, { expected_revision: list.revision, items: items.map((item) => ({ model_id: item.model_id, display_name: item.display_name })) }); await cache.invalidateQueries({ queryKey: ["provider-models", providerId] }); }
    catch { toast.error("Danh sách model vừa được thay đổi ở nơi khác"); }
  }

  async function updateEffectiveModels(items: Model[]) {
    if (!api || !list) return;
    try {
      await api.put(`/v1/providers/${providerId}/models`, { expected_revision: list.revision, items: items.map((item) => ({ model_id: item.model_id, display_name: item.display_name })) });
      await cache.invalidateQueries({ queryKey: ["provider-models", providerId] });
    } catch { toast.error("Danh sách model vừa thay đổi ở nơi khác"); }
  }

  async function saveRoles() {
    if (!api) return;
    try { await api.put("/v1/settings/roles", { roles: roles.map((role) => ({ role, provider_id: providerId || null, model_id: roleModels[role] || null, effort: roleEfforts[role] || null })) }); toast.success("Đã lưu vai trò model"); }
    catch { toast.error("Model không hợp lệ cho vai trò đã chọn"); }
  }

  async function saveLimits(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!api || !providerId) return;
    const form = new FormData(event.currentTarget);
    try { await api.put(`/v1/providers/${providerId}/limits`, { max_concurrent_requests: Number(form.get("concurrency")), rpm: form.get("rpm") ? Number(form.get("rpm")) : null, tpm: form.get("tpm") ? Number(form.get("tpm")) : null, max_retries: Number(form.get("retries")) }); await cache.invalidateQueries({ queryKey: ["provider-limits", providerId] }); toast.success("Đã lưu giới hạn provider"); }
    catch { toast.error("Không thể lưu giới hạn"); }
  }

  async function saveAppLimits(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!api) return;
    const form = new FormData(event.currentTarget);
    const numberOrNull = (key: string, current: number | null) => form.get(key) ? Number(form.get(key)) : current;
    try {
      const current = appLimitsQuery.data;
      await api.put("/v1/settings/limits", { worker_pool: Number(form.get("worker_pool") || current?.worker_pool || 4), app_daily_usd: numberOrNull("app_daily_usd", current?.app_daily_usd ?? null), app_daily_tokens: numberOrNull("app_daily_tokens", current?.app_daily_tokens ?? null), work_daily_usd_default: numberOrNull("work_daily_usd_default", current?.work_daily_usd_default ?? null), timezone: String(form.get("timezone") || current?.timezone || "Asia/Bangkok"), autowrite_mode_default: form.get("autowrite_mode_default") || current?.autowrite_mode_default || "review_each", review_every_k: Number(form.get("review_every_k") || current?.review_every_k || 5), max_repair_rounds: Number(form.get("max_repair_rounds") || current?.max_repair_rounds || 2), chapter_length_min: Number(form.get("chapter_length_min") || current?.chapter_length_min || 1500), chapter_length_max: Number(form.get("chapter_length_max") || current?.chapter_length_max || 2500) });
      await cache.invalidateQueries({ queryKey: ["settings-limits"] }); toast.success("Đã lưu ngân sách toàn ứng dụng");
    } catch { toast.error("Không thể lưu ngân sách"); }
  }

  return <section className="mx-auto max-w-5xl p-8"><h1 className="text-2xl font-semibold">Mô hình AI</h1><p className="mt-1 text-sm text-stone-500">Quản lý kết nối, thứ tự model và vai trò.</p>
    <div className="mt-5 grid gap-5 lg:grid-cols-[17rem_1fr]"><aside className="space-y-3"><div className="rounded-xl border border-stone-200 bg-white p-3"><h2 className="mb-2 text-sm font-semibold">Nhà cung cấp</h2>{providers.map((provider) => <button key={provider.id} onClick={() => setProviderId(provider.id)} className={`mb-1 flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm ${providerId === provider.id ? "bg-stone-900 text-white" : "hover:bg-stone-100"}`}><span>{provider.name}</span><span className="text-xs" aria-label={provider.discovery_status}>{provider.discovery_status === "ok" ? "● Đã lấy model" : provider.discovery_status === "error" ? "● Lỗi" : provider.discovery_status === "waiting_vault" ? "● Chờ vault" : provider.has_key ? "● Có key" : "○ Chưa có key"}</span></button>)}<form onSubmit={(event) => void addProvider(event)} className="mt-3 space-y-2 border-t border-stone-100 pt-3"><Label htmlFor="provider-name">Thêm nhà cung cấp</Label><Input id="provider-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Tên hiển thị" required/><Label htmlFor="provider-protocol">Giao thức</Label><select id="provider-protocol" value={protocol} onChange={(event) => setProtocol(event.target.value as typeof protocol)} className="h-9 w-full rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="anthropic">Anthropic</option><option value="openai_compatible">OpenAI-compatible</option><option value="ollama_lmstudio">Ollama / LM Studio</option></select><Input aria-label="Địa chỉ API" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)}/>{protocol !== "ollama_lmstudio" && <Input aria-label="API key" type="password" autoComplete="off" value={key} onChange={(event) => setKey(event.target.value)} placeholder="API key (tùy chọn)"/>}<Label htmlFor="provider-default-effort">Effort mặc định</Label><select id="provider-default-effort" value={defaultEffort} onChange={(event) => setDefaultEffort(event.target.value)} className="h-9 w-full rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="">Theo model</option>{["low", "medium", "high", "xhigh", "max"].map((effort) => <option key={effort} value={effort}>{effort}</option>)}</select><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={autoDiscover} onChange={(event) => setAutoDiscover(event.target.checked)}/>Tự lấy danh sách model</label>{protocol === "anthropic" && <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={preferLongContext} onChange={(event) => setPreferLongContext(event.target.checked)}/>Ưu tiên context dài</label>}<Button type="button" variant="secondary" className="w-full" onClick={() => void testConnection()}>Kiểm tra kết nối</Button><Button type="button" variant="secondary" className="w-full" disabled={!providerId} onClick={() => void saveProvider()}><Save className="size-4"/>Lưu provider đang chọn</Button><Button type="submit" variant="secondary" className="w-full"><Plus className="size-4"/>Thêm provider</Button></form></div></aside>
      <div className="min-w-0"><nav className="flex gap-2 border-b border-stone-200">{(["models", "roles", "limits"] as const).map((value) => <button key={value} onClick={() => setTab(value)} className={`px-3 py-2 text-sm ${tab === value ? "border-b-2 border-emerald-700 font-medium" : "text-stone-500"}`}>{({ models: "Danh sách model", roles: "Vai trò & effort", limits: "Đồng thời & ngân sách" })[value]}</button>)}</nav>
          {tab === "models" && <div className="mt-4 rounded-xl border border-stone-200 bg-white p-5"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold">Model khả dụng</h2><p className="text-sm text-stone-500">Kéo thả hoặc dùng mũi tên để đổi thứ tự. Model đầu tiên là mặc định.</p></div><Button variant="secondary" onClick={() => void discover()} disabled={!providerId}><RefreshCw className="size-4"/>Lấy danh sách model</Button></div>{!providerId ? <p className="mt-5 text-sm text-stone-500">Thêm provider để xem model.</p> : <div className="mt-4 space-y-2">{(list?.effective ?? []).map((model, index) => <div key={model.model_id} draggable onDragStart={(event) => event.dataTransfer.setData("text/model-index", String(index))} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const from = Number(event.dataTransfer.getData("text/model-index")); if (Number.isInteger(from)) void reorderModel(from, index); }} className="flex items-center gap-3 rounded-lg border border-stone-200 p-3"><span aria-label="Kéo để sắp xếp" className="cursor-grab select-none text-stone-400">⋮⋮</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{model.display_name ?? model.model_id}</p><p className="truncate text-xs text-stone-500">{model.model_id}</p>{renamingModel === model.model_id && <div className="mt-2 flex gap-2"><Input aria-label={`Tên hiển thị ${model.model_id}`} value={modelDisplayName} onChange={(event) => setModelDisplayName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void updateEffectiveModels((list?.effective ?? []).map((item) => item.model_id === model.model_id ? { ...item, display_name: modelDisplayName.trim() || null } : item)); setRenamingModel(null); } }} /><Button variant="secondary" className="min-h-8" onClick={() => { void updateEffectiveModels((list?.effective ?? []).map((item) => item.model_id === model.model_id ? { ...item, display_name: modelDisplayName.trim() || null } : item)); setRenamingModel(null); }}>Lưu tên</Button></div>}<details className="mt-1 text-xs text-stone-500"><summary className="cursor-pointer">Chi tiết model</summary><div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1"><span>Context: {model.max_input_tokens ?? "chưa rõ"}</span><span>Output: {model.max_tokens ?? "chưa rõ"}</span><span>Effort: {model.supported_efforts?.join(", ") ?? "chưa rõ"}</span><span>Vai trò: {model.allowed_roles?.join(", ") ?? "mọi vai trò"}</span><span>Input/1M: {model.price_input_per_mtok ?? "chưa rõ"}</span><span>Output/1M: {model.price_output_per_mtok ?? "chưa rõ"}</span><span>Đồng thời: {model.max_concurrent_requests ?? "theo provider"}</span><span>Nguồn: {model.source}</span></div></details></div>{index === 0 && <Badge>Mặc định</Badge>}{model.missing_since && <Badge className="border-amber-300 bg-amber-50">Không còn trên máy chủ</Badge>}<Button variant="ghost" aria-label={`Đổi tên ${model.model_id}`} onClick={() => { setRenamingModel(model.model_id); setModelDisplayName(model.display_name ?? ""); }}>Đổi tên</Button><Button variant="ghost" aria-label="Đưa lên" disabled={index === 0} onClick={() => void moveModel(index, -1)}><ArrowUp className="size-4"/></Button><Button variant="ghost" aria-label="Đưa xuống" disabled={index === (list?.effective.length ?? 0) - 1} onClick={() => void moveModel(index, 1)}><ArrowDown className="size-4"/></Button><Button variant="ghost" aria-label="Bỏ khỏi danh sách ưu tiên" onClick={() => void updateEffectiveModels((list?.effective ?? []).filter((item) => item.model_id !== model.model_id))}>×</Button></div>)}{(list?.others ?? []).map((model) => <div key={model.model_id} className="flex items-center justify-between rounded-lg border border-dashed border-stone-200 p-3 text-sm text-stone-500"><span>{model.display_name ?? model.model_id} · chưa được ưu tiên</span><Button variant="secondary" className="min-h-8" onClick={() => void updateEffectiveModels([...(list?.effective ?? []), model])}>Thêm</Button></div>)}</div>}</div>}
        {tab === "roles" && <div className="mt-4 rounded-xl border border-stone-200 bg-white p-5"><h2 className="font-semibold">Gán model theo vai trò</h2><div className="mt-4 space-y-3">{roles.map((role) => { const selectedModel = list?.effective.find((model) => model.model_id === roleModels[role]); const effortOptions = selectedModel?.supported_efforts; return <div key={role} className="grid items-center gap-2 sm:grid-cols-[8rem_1fr_10rem]"><Label htmlFor={`role-${role}`}>{({ planner: "Lập kế hoạch", writer: "Viết", checker: "Kiểm tra", reviewer: "Review", summary: "Tóm tắt" })[role]}</Label><select id={`role-${role}`} value={roleModels[role] ?? ""} onChange={(event) => setRoleModels((current) => ({ ...current, [role]: event.target.value }))} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="">Mặc định</option>{(list?.effective ?? []).map((model) => <option key={model.model_id} value={model.model_id}>{model.display_name ?? model.model_id}</option>)}</select><select aria-label={`Effort ${role}`} value={roleEfforts[role] ?? ""} disabled={!selectedModel || effortOptions === null || effortOptions === undefined || effortOptions.length === 0} onChange={(event) => setRoleEfforts((current) => ({ ...current, [role]: event.target.value }))} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm disabled:opacity-50"><option value="">Effort mặc định</option>{(effortOptions ?? []).map((effort) => <option key={effort} value={effort}>{effort}</option>)}</select></div>; })}</div><Button className="mt-5" onClick={() => void saveRoles()}><Save className="size-4"/>Lưu vai trò</Button></div>}
        {tab === "limits" && <div className="mt-4 grid gap-4"><form key={limitsQuery.data ? "provider-limits-loaded" : "provider-limits-loading"} className="grid max-w-xl gap-4 rounded-xl border border-stone-200 bg-white p-5" onSubmit={(event) => void saveLimits(event)}><h2 className="font-semibold">Giới hạn của provider</h2>{([["concurrency", "Số request đồng thời", limitsQuery.data?.max_concurrent_requests ?? 4], ["rpm", "Request mỗi phút", limitsQuery.data?.rpm ?? ""], ["tpm", "Token mỗi phút", limitsQuery.data?.tpm ?? ""], ["retries", "Số lần thử lại", limitsQuery.data?.max_retries ?? 3]] as const).map(([id, label, value]) => <div key={id} className="grid gap-2"><Label htmlFor={id}>{label}</Label><Input id={id} name={id} type="number" min={id === "concurrency" ? 1 : 0} defaultValue={value}/></div>)}<Button type="submit"><Save className="size-4"/>Lưu giới hạn</Button></form><form key={appLimitsQuery.data ? "app-limits-loaded" : "app-limits-loading"} className="grid max-w-xl gap-4 rounded-xl border border-stone-200 bg-white p-5" onSubmit={(event) => void saveAppLimits(event)}><h2 className="font-semibold">Đồng thời & ngân sách toàn ứng dụng</h2>{([["worker_pool", "Số truyện xử lý song song", appLimitsQuery.data?.worker_pool ?? 4], ["app_daily_usd", "Ngân sách mỗi ngày (USD)", appLimitsQuery.data?.app_daily_usd ?? ""], ["app_daily_tokens", "Token mỗi ngày", appLimitsQuery.data?.app_daily_tokens ?? ""], ["work_daily_usd_default", "Ngân sách mặc định mỗi truyện (USD)", appLimitsQuery.data?.work_daily_usd_default ?? ""]] as const).map(([id, label, value]) => <div key={id} className="grid gap-2"><Label htmlFor={id}>{label}</Label><Input id={id} name={id} type="number" min={id === "worker_pool" ? 1 : 0} defaultValue={value}/></div>)}<div className="grid gap-2"><Label htmlFor="timezone">Múi giờ ngân sách</Label><Input id="timezone" name="timezone" defaultValue={appLimitsQuery.data?.timezone ?? "Asia/Bangkok"}/></div><Button type="submit"><Save className="size-4"/>Lưu ngân sách</Button></form><form key={appLimitsQuery.data ? "writing-defaults-loaded" : "writing-defaults-loading"} className="grid max-w-xl gap-4 rounded-xl border border-stone-200 bg-white p-5" onSubmit={(event) => void saveAppLimits(event)}><h2 className="font-semibold">Thiết lập viết mặc định</h2><div className="grid gap-2"><Label htmlFor="autowrite_mode_default">Chế độ auto-write</Label><select id="autowrite_mode_default" name="autowrite_mode_default" defaultValue={appLimitsQuery.data?.autowrite_mode_default ?? "review_each"} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="auto">Tự động</option><option value="review_each">Duyệt từng chương</option><option value="review_every_k">Duyệt theo lô</option></select></div>{([["review_every_k", "Duyệt sau mỗi K chương", appLimitsQuery.data?.review_every_k ?? 5], ["max_repair_rounds", "Số vòng sửa tối đa", appLimitsQuery.data?.max_repair_rounds ?? 2], ["chapter_length_min", "Độ dài chương tối thiểu (âm tiết)", appLimitsQuery.data?.chapter_length_min ?? 1500], ["chapter_length_max", "Độ dài chương tối đa (âm tiết)", appLimitsQuery.data?.chapter_length_max ?? 2500]] as const).map(([id, label, value]) => <div key={id} className="grid gap-2"><Label htmlFor={id}>{label}</Label><Input id={id} name={id} type="number" min={0} defaultValue={value}/></div>)}<Button type="submit"><Save className="size-4"/>Lưu thiết lập viết</Button></form></div>}
      </div>
    </div>
  </section>;
}

