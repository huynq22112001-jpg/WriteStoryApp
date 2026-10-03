import { create } from "zustand";

import type { StreamStatus } from "@/shared/api/sse";
import type { BackendSession, BootState } from "@/shared/desktop/bridge";

interface BootStore {
  bootState: BootState;
  session: BackendSession | null;
  connection: StreamStatus;
  setBootState: (bootState: BootState) => void;
  setSession: (session: BackendSession | null) => void;
  setConnection: (connection: StreamStatus) => void;
}

export const useBootStore = create<BootStore>((set) => ({
  bootState: { phase: "resolving_data_root", platform: "unknown", restart_count: 0 },
  session: null,
  connection: "closed",
  setBootState: (bootState) => set({ bootState }),
  setSession: (session) => set({ session }),
  setConnection: (connection) => set({ connection }),
}));
