import { Link, Outlet } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

const navClass =
  "rounded-md px-3 py-1.5 text-sm text-stone-600 hover:bg-stone-200 hover:text-stone-900";
const activeClass = "bg-stone-900 text-white hover:bg-stone-900 hover:text-white";

export function AppShell() {
  const { t } = useTranslation();
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-6 border-b border-stone-200 bg-white px-4 py-2">
        <span className="font-semibold">{t("appName")}</span>
        <nav className="flex gap-1">
          <Link to="/" className={navClass} activeProps={{ className: activeClass }}>
            {t("nav.library")}
          </Link>
          <Link to="/system" className={navClass} activeProps={{ className: activeClass }}>
            {t("nav.system")}
          </Link>
        </nav>
      </header>
      <main className="min-h-0 flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
