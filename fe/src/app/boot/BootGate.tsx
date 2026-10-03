import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { RouterProvider } from "@tanstack/react-router";

import { clearSession, setSession } from "@/shared/api/client";
import { startEventBus, subscribeEventBus } from "@/shared/api/eventBus";
import { getBackendSession } from "@/shared/desktop/bridge";
import { router } from "@/app/router";

import { ConnectionBanner } from "./ConnectionBanner";
import { BackendCrashedScreen, DataRootScreen, StartingScreen, StartupErrorScreen, TranslocatedScreen } from "./Screens";
import { useBootStore } from "./store";
import { useBootState } from "./useBootState";

export function BootGate() {
  useBootState();
  const queryClient = useQueryClient();
  const state = useBootStore((store) => store.bootState);
  const setSessionState = useBootStore((store) => store.setSession);
  const setConnection = useBootStore((store) => store.setConnection);
  const wasReady = useRef(false);

  useEffect(() => {
    if (state.phase !== "ready") {
      setSessionState(null);
      setConnection("closed");
      clearSession();
      void queryClient.cancelQueries();
      queryClient.removeQueries({ queryKey: ["backend-session"] });
      return;
    }

    let active = true;
    let stopEventBus: (() => void) | undefined;
    if (wasReady.current) void queryClient.invalidateQueries();
    wasReady.current = true;

    void getBackendSession().then((session) => {
      if (!active) return;
      setSessionState(session);
      if (session) {
        setSession(session);
        queryClient.setQueryData(["backend-session"], session);
        stopEventBus = startEventBus(session);
        // Keep the global stream status in the boot store for ConnectionBanner.
        const unsubscribeStatus = subscribeEventBus(() => {}, setConnection);
        const previousStop = stopEventBus;
        stopEventBus = () => { unsubscribeStatus(); previousStop(); };
      } else {
        clearSession();
        setConnection("closed");
      }
    }).catch(() => {
      if (active) {
        setSessionState(null);
        clearSession();
      }
    });

    return () => {
      active = false;
      stopEventBus?.();
    };
  }, [queryClient, setConnection, setSessionState, state.phase]);

  switch (state.phase) {
    case "resolving_data_root":
    case "starting_backend":
    case "shutting_down":
      return <StartingScreen state={state} />;
    case "needs_data_root":
    case "data_root_error":
      return <DataRootScreen state={state} />;
    case "translocated":
      return <TranslocatedScreen />;
    case "backend_crashed":
      return <BackendCrashedScreen state={state} />;
    case "locked_by_other_instance":
    case "startup_failed":
    case "protocol_mismatch":
      return <StartupErrorScreen state={state} />;
    case "ready":
      return (
        <>
          <ConnectionBanner />
          <RouterProvider router={router} />
        </>
      );
  }
}
