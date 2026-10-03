import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currentSession, createApiClient, newIdempotencyKey } from "@/shared/api/client";

type Vault = { state: "absent" | "locked" | "unlocked"; mode: string; waiting_jobs: number; revision: number };
type Secret = { ref: string; storage: "vault" | "session"; available: boolean; label?: string };

export function SecuritySettingsPage() {
  const session = currentSession();
  const api = session ? createApiClient(session) : null;
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [nextConfirm, setNextConfirm] = useState("");
  const vault = useQuery({ queryKey: ["vault"], enabled: !!api, queryFn: () => api!.get<Vault>("/v1/vault/status") });
  const secrets = useQuery({ queryKey: ["secrets"], enabled: !!api, queryFn: () => api!.get<Secret[]>("/v1/secrets") });
  async function run(action: () => Promise<unknown>, message: string) {
    try { await action(); await queryClient.invalidateQueries({ queryKey: ["vault"] }); await queryClient.invalidateQueries({ queryKey: ["secrets"] }); toast.success(message); }
    catch { toast.error("Không thể thực hiện thao tác bảo mật"); }
  }
  const current = vault.data;
  return <section className="mx-auto max-w-3xl p-8"><h1 className="text-2xl font-semibold">Bảo mật & API key</h1><p className="mt-1 text-sm text-stone-500">API key không được hiển thị sau khi lưu.</p>
    <section className="mt-6 rounded-xl border border-stone-200 bg-white p-5"><div className="flex items-start justify-between"><div><h2 className="font-semibold">Vault</h2><p className="mt-1 text-sm text-stone-500">Trạng thái: {current?.state ?? "Đang tải"} · Chế độ: {current?.mode ?? "—"}</p></div>{current?.state === "unlocked" && <Button variant="secondary" onClick={() => void run(() => api!.post("/v1/vault/lock", {}), "Đã khóa vault")}>Khóa vault</Button>}</div>
      {current?.state === "absent" && <form className="mt-4 grid max-w-md gap-3" onSubmit={(event) => { event.preventDefault(); void run(async () => { await api!.post("/v1/vault", { password, password_confirm: confirm, import_session_secrets: true }); setPassword(""); setConfirm(""); }, "Đã tạo vault"); }}><div className="grid gap-2"><Label htmlFor="new-vault-password">Mật khẩu mới</Label><Input id="new-vault-password" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="confirm-vault-password">Nhập lại mật khẩu</Label><Input id="confirm-vault-password" type="password" autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></div><Button type="submit">Tạo vault</Button></form>}
      {current?.state === "locked" && <p className="mt-4 text-sm">Vault đang khóa. Mở khóa ở nút trên thanh ứng dụng để dùng key đã lưu.</p>}
      {current?.state === "unlocked" && <form className="mt-5 grid max-w-md gap-3 border-t border-stone-100 pt-4" onSubmit={(event) => { event.preventDefault(); void run(async () => { await api!.post("/v1/vault/change-password", { current_password: currentPassword, new_password: nextPassword, new_password_confirm: nextConfirm }); setCurrentPassword(""); setNextPassword(""); setNextConfirm(""); }, "Đã đổi mật khẩu vault"); }}><h3 className="text-sm font-semibold">Đổi mật khẩu vault</h3><div className="grid gap-2"><Label htmlFor="current-vault-password">Mật khẩu hiện tại</Label><Input id="current-vault-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="next-vault-password">Mật khẩu mới</Label><Input id="next-vault-password" type="password" autoComplete="new-password" value={nextPassword} onChange={(event) => setNextPassword(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="next-vault-password-confirm">Nhập lại mật khẩu mới</Label><Input id="next-vault-password-confirm" type="password" autoComplete="new-password" value={nextConfirm} onChange={(event) => setNextConfirm(event.target.value)} required /></div><Button type="submit" variant="secondary">Đổi mật khẩu</Button></form>}
      {current?.state === "unlocked" && <div className="mt-4"><Button variant="destructive" onClick={() => { if (window.confirm("Xóa vault và các API key đã mã hóa?")) void run(() => api!.post("/v1/vault/reset", { confirm: "XÓA VAULT" }, { idempotencyKey: newIdempotencyKey() }), "Đã đặt lại vault"); }}>Đặt lại vault</Button></div>}
    </section>
    <section className="mt-5 rounded-xl border border-stone-200 bg-white p-5"><h2 className="font-semibold">Danh sách API key</h2><p className="mt-1 text-sm text-stone-500">Chỉ hiển thị tên tham chiếu và nơi lưu, không hiển thị giá trị.</p>{!secrets.data?.length ? <p className="mt-4 text-sm text-stone-500">Chưa có API key nào. Thêm nhà cung cấp ở Mô hình AI.</p> : <ul className="mt-4 divide-y divide-stone-100">{secrets.data.map((secret) => <li key={secret.ref} className="flex items-center justify-between gap-3 py-3 text-sm"><span>{secret.label ?? secret.ref}</span><span className="text-stone-500">{secret.storage === "vault" ? "Vault" : "Phiên hiện tại"}</span><Button variant="ghost" className="min-h-8 text-red-700" onClick={() => { if (window.confirm(`Xóa API key ${secret.label ?? secret.ref}?`)) void run(() => api!.delete(`/v1/secrets/${encodeURIComponent(secret.ref)}`), "Đã xóa API key"); }}>Xóa</Button></li>)}</ul>}</section>
  </section>;
}
