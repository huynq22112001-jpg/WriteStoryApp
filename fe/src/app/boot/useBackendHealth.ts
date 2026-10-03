import { useBootStore } from "./store";

export function useBackendHealth() {
  const phase = useBootStore((state) => state.bootState.phase);
  const connection = useBootStore((state) => state.connection);
  return { phase, connection, ready: phase === "ready" };
}
