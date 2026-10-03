import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { BookOpen, Command, FileText, Library, Settings, WandSparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Command as CommandMenu } from "cmdk";
import { useHotkeys } from "react-hotkeys-hook";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { BackendStatusBar } from "@/app/boot/BackendStatusBar";
import { Button } from "@/components/ui/button";
import { currentSession, createApiClient } from "@/shared/api/client";
import { subscribeEventBus } from "@/shared/api/eventBus";
import { VaultUnlockDialog } from "@/features/vault/components/VaultUnlockDialog";

const items = [
  { to: "/", key: "nav.library", icon: Library },
  { to: "/writing-room", key: "nav.writingRoom", icon: WandSparkles },
  { to: "/settings", key: "nav.settings", icon: Settings },
  { to: "/logs", key: "nav.logs", icon: FileText },
] as const;

export function AppShell() {
  const { t } = useTranslation();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const lastVaultNoticeAt = useRef(0);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const session = currentSession();
  const navigate = useNavigate();
  const onboarding = useQuery({ queryKey: ["onboarding"], enabled: !!session, queryFn: () => createApiClient(session!).get<{ status: string }>("/v1/onboarding") });
  const queryClient = useQueryClient();
  const vault = useQuery({ queryKey: ["vault"], enabled: !!session, queryFn: () => createApiClient(session!).get<{ state: string; waiting_jobs: number }>("/v1/vault/status") });
  useEffect(() => subscribeEventBus((event) => {
    if (event.type === "vault.status") {
      void queryClient.invalidateQueries({ queryKey: ["vault"] });
      void queryClient.invalidateQueries({ queryKey: ["secrets"] });
    }
    if (event.type === "job.state") {
      const reason = event.payload?.wait_reason;
      const now = Date.now();
      if (reason === "VAULT_LOCKED" && now - lastVaultNoticeAt.current >= 60_000) {
        lastVaultNoticeAt.current = now;
        toast("Tác vụ đang chờ mở vault", { action: { label: "Mở khóa", onClick: () => window.dispatchEvent(new CustomEvent("vault:unlock-requested")) } });
      } else if (reason === "SECRET_MISSING" && now - lastVaultNoticeAt.current >= 60_000) {
        lastVaultNoticeAt.current = now;
        toast("Tác vụ đang chờ API key", { action: { label: "Cài đặt mô hình", onClick: () => void navigate({ to: "/settings/models" }) } });
      }
    }
  }), [navigate, queryClient]);
  useEffect(() => {
    if (pathname !== "/onboarding" && onboarding.data?.status === "pending") void navigate({ to: "/onboarding" });
  }, [navigate, onboarding.data?.status, pathname]);
  useHotkeys("ctrl+k, meta+k", (event) => { event.preventDefault(); setPaletteOpen((open) => !open); }, { enableOnFormTags: true });
  useHotkeys("ctrl+shift+w, meta+shift+w", (event) => { event.preventDefault(); void navigate({ to: "/writing-room" }); }, { enableOnFormTags: true }, [navigate]);

  return <div className="flex h-full flex-col bg-stone-50 text-stone-900">
    <header className="flex min-h-14 items-center gap-5 border-b border-stone-200 bg-white px-4">
      <Link to="/" className="flex items-center gap-2 font-semibold"><BookOpen className="size-5 text-emerald-700" />{t("appName")}</Link>
      <nav aria-label={t("nav.primary")} className="flex min-w-0 flex-1 items-center gap-1">
        {items.map(({ to, key, icon: Icon }) => <Link key={to} to={to} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-stone-600 hover:bg-stone-100" activeProps={{ className: "bg-stone-900 text-white hover:bg-stone-900" }}><Icon className="size-4" />{t(key)}</Link>)}
      </nav>
      <Button variant="secondary" className="min-h-8" onClick={() => setPaletteOpen(true)}><Command className="size-4"/><span>{t("command.open")}</span><kbd className="ml-2 rounded border border-stone-300 px-1 text-xs">Ctrl K</kbd></Button>
      <div className="hidden text-right text-xs text-stone-500 lg:block"><div>{t("header.running", { count: 0 })}</div><div>{t("header.cost", { cost: "0,00" })}</div></div>
      {vault.data?.state === "locked" && <VaultUnlockDialog waitingJobs={vault.data.waiting_jobs} onUnlocked={() => void queryClient.invalidateQueries({ queryKey: ["vault"] })} trigger={<Button variant="secondary" aria-label={`Vault đang khóa, ${vault.data.waiting_jobs} tác vụ đang chờ. Mở khóa vault`}><span aria-hidden="true">🔒</span>Vault khóa</Button>} />}
      {vault.data?.state === "unlocked" && <Button variant="secondary" aria-label="Khóa vault" onClick={async () => { try { await createApiClient(session!).post("/v1/vault/lock", {}); await queryClient.invalidateQueries({ queryKey: ["vault"] }); } catch { toast.error("Không thể khóa vault"); } }}>Vault mở · Khóa</Button>}
    </header>
    <main className="min-h-0 flex-1 overflow-auto"><Outlet /></main>
    <BackendStatusBar />
    {paletteOpen && <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 px-4 pt-[15vh]" onMouseDown={(event) => { if (event.target === event.currentTarget) setPaletteOpen(false); }}>
      <CommandMenu className="w-full max-w-xl overflow-hidden rounded-xl border border-stone-200 bg-white shadow-2xl">
        <CommandMenu.Input autoFocus placeholder={t("command.placeholder")} className="h-12 w-full border-b border-stone-200 px-4 outline-none" />
        <CommandMenu.List className="max-h-80 overflow-auto p-2"><CommandMenu.Empty className="p-4 text-sm text-stone-500">{t("command.empty")}</CommandMenu.Empty>
          <CommandMenu.Group heading={t("command.navigation")} className="px-2 text-xs text-stone-500">
            {items.map(({ to, key, icon: Icon }) => <CommandMenu.Item key={to} onSelect={() => { window.location.hash = `#${to}`; setPaletteOpen(false); }} className="flex cursor-pointer items-center gap-2 rounded px-2 py-2 text-sm text-stone-800 aria-selected:bg-stone-100"><Icon className="size-4" />{t(key)}</CommandMenu.Item>)}
          </CommandMenu.Group>
          <CommandMenu.Separator className="my-2 h-px bg-stone-100" />
          <div className="px-3 pb-2 text-xs text-stone-400">{pathname}</div>
        </CommandMenu.List>
      </CommandMenu>
    </div>}
  </div>;
}
