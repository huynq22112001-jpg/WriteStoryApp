import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currentSession, createApiClient } from "@/shared/api/client";
import { useBootStore } from "@/app/boot/store";
import { confirmDataRoot, pickDataRootFolder } from "@/shared/desktop/bridge";

type Onboarding = { status: "pending" | "completed" | "skipped"; step: "security" | "provider" | "first_work" | null; revision: number; steps: Record<string, string>; platform: string };
const steps = ["security", "provider", "first_work"] as const;

export function OnboardingPage() {
  const session = currentSession();
  const api = session ? createApiClient(session) : null;
  const dataRoot = useBootStore((state) => state.bootState.data_root);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.anthropic.com");
  const [apiKey, setApiKey] = useState("");
  const [securityMode, setSecurityMode] = useState<"vault" | "session" | null>(null);
  const [vaultPassword, setVaultPassword] = useState("");
  const [vaultPasswordConfirm, setVaultPasswordConfirm] = useState("");
  const [understandsVaultRisk, setUnderstandsVaultRisk] = useState(false);
  const [dataRootPath, setDataRootPath] = useState<string | null>(null);
  const stateQuery = useQuery({ queryKey: ["onboarding"], enabled: !!api, queryFn: () => api!.get<Onboarding>("/v1/onboarding") });

  async function selectSessionSecurity() {
    if (!api) return;
    try {
      const status = await api.get<{ revision?: number }>("/v1/vault/status");
      await api.put("/v1/vault/mode", { mode: "session_only", expected_revision: status.revision ?? 1 });
      setSecurityMode("session");
      toast.success("API key chỉ được giữ trong phiên này");
    } catch { toast.error("Không thể lưu lựa chọn bảo mật"); }
  }

  async function createVault() {
    if (!api || vaultPassword.length < 12 || vaultPassword !== vaultPasswordConfirm || !understandsVaultRisk) return;
    try {
      await api.post("/v1/vault", { password: vaultPassword, password_confirm: vaultPasswordConfirm, import_session_secrets: true });
      setVaultPassword(""); setVaultPasswordConfirm(""); setSecurityMode("vault");
      toast.success("Đã tạo vault bảo vệ API key");
    } catch { toast.error("Không thể tạo vault. Kiểm tra lại mật khẩu và trạng thái bảo mật."); }
  }

  async function addProvider() {
    if (!api || !name.trim()) return;
    try {
      const vault = await api.get<{ mode: string }>("/v1/vault/status");
      const provider = await api.post<{ id: string }>("/v1/providers", { name: name.trim(), protocol: "anthropic", base_url: baseUrl, api_key: apiKey || undefined, key_storage: apiKey ? vault.mode === "vault" ? "vault" : "session" : "none", auto_discover: true });
      setApiKey("");
      const discovery = await api.post<{ status: string }>(`/v1/providers/${provider.id}/discover`, {});
      toast[discovery.status === "ok" ? "success" : "warning"](discovery.status === "ok" ? "Đã kết nối và lấy danh sách model" : "Đã lưu nhà cung cấp; chưa lấy được danh sách model");
    } catch { toast.error("Không thể lưu nhà cung cấp"); }
  }

  async function advance() {
    if (!api || !stateQuery.data) return;
    if (step === 0) { setStep(1); return; }
    if (step === 1 && !securityMode) { toast.error("Hãy chọn cách bảo vệ API key trước khi tiếp tục"); return; }
    const persistedStep = steps[step - 1];
    if (!persistedStep) return;
    try {
      await api.put("/v1/onboarding", { step: persistedStep, expected_revision: stateQuery.data.revision });
      await queryClient.invalidateQueries({ queryKey: ["onboarding"] });
      if (step < steps.length) setStep(step + 1);
      else {
        await api.post("/v1/onboarding/complete", { skipped: false });
        await queryClient.invalidateQueries({ queryKey: ["onboarding"] });
        await navigate({ to: "/" });
      }
    } catch { toast.error("Không thể cập nhật tiến độ lần chạy đầu"); }
  }

  async function skip() {
    if (!api) return;
    try { await api.post("/v1/onboarding/complete", { skipped: true }); await navigate({ to: "/" }); }
    catch { toast.error("Không thể bỏ qua lần chạy đầu"); }
  }

  async function createFirstWork() {
    if (!api) return;
    try {
      await api.post("/v1/onboarding/complete", { skipped: false });
      await queryClient.invalidateQueries({ queryKey: ["onboarding"] });
      await navigate({ to: "/new", search: { workId: undefined, step: undefined } });
    } catch { toast.error("Không thể lưu xong thiết lập lần đầu"); }
  }

  return <main className="mx-auto min-h-full max-w-3xl px-6 py-10"><header className="text-center"><p className="text-sm font-medium text-emerald-800">WriteStoryApp · {step + 1}/4</p><h1 className="mt-2 text-3xl font-semibold">Bắt đầu viết truyện</h1><p className="mt-2 text-stone-500">Thiết lập những phần cần thiết. Bạn có thể đổi lại trong Cài đặt.</p></header>
    <ol className="mt-8 grid grid-cols-4 gap-2" aria-label="Các bước thiết lập">{["Dữ liệu", "Bảo mật", "Kết nối AI", "Truyện đầu tiên"].map((label, index) => <li key={label} aria-current={index === step ? "step" : undefined} className={`rounded-lg border p-3 text-center text-xs ${index === step ? "border-emerald-700 bg-emerald-50 text-emerald-950" : index < step ? "border-stone-200 bg-white" : "border-stone-200 text-stone-500"}`}>{index < step ? <Check className="mx-auto mb-1 size-4"/> : <span className="mb-1 block">{index + 1}</span>}{label}</li>)}</ol>
    <section className="mt-6 min-h-64 rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
      {step === 0 && <><h2 className="text-xl font-semibold">Thư mục dữ liệu</h2><p className="mt-1 text-sm text-stone-500">{dataRoot ? `Dữ liệu nằm tại: ${dataRoot}` : dataRootPath ? `Đã chọn: ${dataRootPath}` : "Thư mục dữ liệu đã được chọn ở màn khởi động."}</p>{stateQuery.data?.platform === "darwin" && <Button className="mt-4" variant="secondary" onClick={async () => { const selected = await pickDataRootFolder(); if (selected) { await confirmDataRoot(selected, true); setDataRootPath(selected); } }}>Chọn thư mục dữ liệu</Button>}</>}
      {step === 1 && <><h2 className="text-xl font-semibold">Bảo vệ API key</h2><p className="mt-1 text-sm text-stone-500">Chọn cách lưu thông tin truy cập nhà cung cấp.</p><div className="mt-5 grid gap-3 sm:grid-cols-2"><button aria-pressed={securityMode === "vault"} className="rounded-lg border p-4 text-left hover:border-emerald-700" onClick={() => setSecurityMode("vault")}><b>Đặt mật khẩu vault</b><p className="mt-1 text-sm text-stone-500">Mã hóa key trên thiết bị; quên mật khẩu thì key không khôi phục được.</p></button><button aria-pressed={securityMode === "session"} className="rounded-lg border p-4 text-left hover:border-emerald-700" onClick={() => void selectSessionSecurity()}><b>Chỉ dùng key trong phiên này</b><p className="mt-1 text-sm text-stone-500">Key sẽ mất khi đóng ứng dụng.</p></button></div>{securityMode === "vault" && <div className="mt-4 grid gap-3"><Label htmlFor="onboarding-vault-password">Mật khẩu vault (tối thiểu 12 ký tự)</Label><Input id="onboarding-vault-password" type="password" autoComplete="new-password" value={vaultPassword} onChange={(event) => setVaultPassword(event.target.value)} /><Label htmlFor="onboarding-vault-confirm">Nhập lại mật khẩu</Label><Input id="onboarding-vault-confirm" type="password" autoComplete="new-password" value={vaultPasswordConfirm} onChange={(event) => setVaultPasswordConfirm(event.target.value)} /><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={understandsVaultRisk} onChange={(event) => setUnderstandsVaultRisk(event.target.checked)} />Tôi hiểu rằng quên mật khẩu sẽ mất API key trong vault.</label><Button variant="secondary" disabled={vaultPassword.length < 12 || vaultPassword !== vaultPasswordConfirm || !understandsVaultRisk} onClick={() => void createVault()}>Tạo vault</Button></div>}</>}
      {step === 2 && <><h2 className="text-xl font-semibold">Kết nối nhà cung cấp AI</h2><p className="mt-1 text-sm text-stone-500">Key được gửi trực tiếp tới backend cục bộ và không hiện lại sau khi lưu.</p><div className="mt-5 grid gap-4"><div className="grid gap-2"><Label htmlFor="provider-name">Tên nhà cung cấp</Label><Input id="provider-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Anthropic" /></div><div className="grid gap-2"><Label htmlFor="provider-url">Địa chỉ API</Label><Input id="provider-url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} /></div><div className="grid gap-2"><Label htmlFor="provider-key">API key (tùy chọn)</Label><Input id="provider-key" type="password" autoComplete="off" value={apiKey} onChange={(event) => setApiKey(event.target.value)} /></div><Button variant="secondary" onClick={() => void addProvider()}>Lưu và kiểm tra kết nối</Button></div></>}
      {step === 3 && <><h2 className="text-xl font-semibold">Tạo truyện đầu tiên</h2><p className="mt-1 text-sm text-stone-500">Thư mục dữ liệu: {dataRoot || "Đã chọn trong bước khởi động"}</p><div className="mt-5 flex flex-wrap gap-3"><Button onClick={() => void createFirstWork()}>Tạo truyện mới</Button><Button variant="secondary" onClick={() => void advance()}>Hoàn tất và vào thư viện</Button></div></>}
    </section>
    <footer className="mt-5 flex items-center justify-between"><Button variant="ghost" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}><ChevronLeft className="size-4"/>Quay lại</Button><div className="flex gap-2"><Button variant="ghost" onClick={() => void skip()}>Để sau</Button>{step < 3 && <Button onClick={() => void advance()}>Tiếp tục<ChevronRight className="size-4"/></Button>}</div></footer>
  </main>;
}
