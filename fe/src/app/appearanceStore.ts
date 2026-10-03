import { create } from "zustand";

type AppearanceState = { theme: "light" | "dark" | "system"; fontScale: number; setTheme: (theme: AppearanceState["theme"]) => void; setFontScale: (value: number) => void };
export const useAppearanceStore = create<AppearanceState>((set) => ({
  theme: "system",
  fontScale: 1,
  setTheme: (theme) => set({ theme }),
  setFontScale: (fontScale) => set({ fontScale: Math.min(1.3, Math.max(0.85, fontScale)) }),
}));
