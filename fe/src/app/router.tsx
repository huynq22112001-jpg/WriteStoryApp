import {
  createHashHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";

import { LibraryPage } from "@/features/library";
import { SystemStatusPage } from "@/features/system";

import { AppShell } from "./layouts/AppShell";

// Hash history: Tauri nạp file tĩnh, không có server để fallback route (UI §4).
const rootRoute = createRootRoute({ component: AppShell });

const libraryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: LibraryPage,
});

const systemRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/system",
  component: SystemStatusPage,
});

const routeTree = rootRoute.addChildren([libraryRoute, systemRoute]);

export const router = createRouter({ routeTree, history: createHashHistory() });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
