import { BootGate } from "./boot/BootGate";
import { AppProviders } from "./providers";
import { useEffect } from "react";
import { useAppearanceStore } from "./appearanceStore";

function ApplyAppearance() {
  const { theme, fontScale } = useAppearanceStore();
  useEffect(() => {
    const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.style.fontSize = `${fontScale * 100}%`;
  }, [theme, fontScale]);
  return null;
}

export function App() {
  return (
    <AppProviders>
      <ApplyAppearance />
      <BootGate />
    </AppProviders>
  );
}
