import { useEffect } from "react";

import { getBootState, onBootState } from "@/shared/desktop/bridge";

import { useBootStore } from "./store";

/** Subscribe first; ignore the initial snapshot if a newer event arrived while it loaded. */
export function useBootState() {
  const setBootState = useBootStore((state) => state.setBootState);

  useEffect(() => {
    let active = true;
    let eventRevision = 0;
    let unlisten: (() => void) | undefined;

    void (async () => {
      const stop = await onBootState((state) => {
        eventRevision += 1;
        setBootState(state);
      });
      if (!active) {
        stop();
        return;
      }
      unlisten = stop;
      const beforeSnapshot = eventRevision;
      try {
        const snapshot = await getBootState();
        if (active && eventRevision === beforeSnapshot) setBootState(snapshot);
      } catch {
        // Keep the latest event or resolving screen; the next event can recover the gate.
      }
    })();

    return () => {
      active = false;
      unlisten?.();
    };
  }, [setBootState]);
}
