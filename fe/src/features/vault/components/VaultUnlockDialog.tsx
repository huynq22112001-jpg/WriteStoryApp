import { useEffect, useState, type ReactElement } from "react";
import { LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currentSession, createApiClient } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";

export function VaultUnlockDialog({ waitingJobs = 0, onUnlocked, trigger }: { waitingJobs?: number; onUnlocked?: () => void; trigger?: ReactElement }) {
  const [password, setPassword] = useState("");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [retryAfter, setRetryAfter] = useState(0);
  useEffect(() => {
    const openDialog = () => setOpen(true);
    window.addEventListener("vault:unlock-requested", openDialog);
    return () => window.removeEventListener("vault:unlock-requested", openDialog);
  }, []);
  useEffect(() => {
    if (!retryAfter) return;
    const timer = window.setTimeout(() => setRetryAfter((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [retryAfter]);
  useEffect(() => {
    if (!open) { setPassword(""); setError(""); }
  }, [open]);
  async function unlock() {
    const session = currentSession();
    if (!session) return;
    try {
      await createApiClient(session).post("/v1/vault/unlock", { password });
      setPassword(""); setError(""); setOpen(false); toast.success("Đã mở khóa vault"); onUnlocked?.();
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "VAULT_PASSWORD_INVALID") { setPassword(""); setError("Mật khẩu vault không đúng."); }
      else if (cause instanceof ApiError && cause.code === "VAULT_UNLOCK_THROTTLED") {
        const seconds = Number(cause.detail?.retry_after_seconds ?? 30);
        setRetryAfter(Number.isFinite(seconds) ? Math.max(1, seconds) : 30);
        setError("Thử quá nhiều lần. Hãy chờ trước khi thử lại.");
      } else setError("Không mở được vault. Hãy kiểm tra trạng thái vault.");
      toast.error("Không mở được vault");
    }
  }
  return <Dialog open={open} onOpenChange={setOpen} trigger={trigger ?? <Button variant="secondary"><LockKeyhole className="size-4"/>Mở khóa vault</Button>} title="Mở khóa vault" description={waitingJobs ? `${waitingJobs} tác vụ đang chờ vault.` : "Nhập mật khẩu để dùng các API key đã lưu."}>
    <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void unlock(); }}><div className="grid gap-2"><Label htmlFor="vault-unlock-password">Mật khẩu vault</Label><Input id="vault-unlock-password" type="password" autoComplete="current-password" autoFocus value={password} onChange={(event) => { setPassword(event.target.value); setError(""); }} required />{error && <p role="alert" className="text-sm text-red-700">{error}</p>}</div><Button type="submit" className="w-full" disabled={retryAfter > 0}>{retryAfter > 0 ? `Thử lại sau ${retryAfter} giây` : "Mở khóa"}</Button></form>
  </Dialog>;
}
