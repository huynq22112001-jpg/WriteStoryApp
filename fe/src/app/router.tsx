import {
  createHashHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";

import { LibraryPage } from "@/features/library";
import { SystemStatusPage } from "@/features/system";
import { ChapterEditor } from "@/features/editor/components/ChapterEditor";
import { PagePlaceholder } from "./PagePlaceholder";
import { NewWorkPage } from "@/features/library/pages/NewWorkPage";
import { WorkspacePage } from "@/features/editor/components/WorkspacePage";
import { AppearancePage } from "@/features/settings/pages/AppearancePage";
import { OnboardingPage } from "@/features/onboarding/pages/OnboardingPage";
import { SecuritySettingsPage } from "@/features/settings/pages/SecuritySettingsPage";
import { ModelsSettingsPage } from "@/features/settings/pages/ModelsSettingsPage";

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

const editorSpikeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/editor-spike",
  component: ChapterEditor,
});

const newWorkRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/new",
  validateSearch: (search: Record<string, unknown>) => ({
    workId: typeof search.workId === "string" ? search.workId : undefined,
    step: typeof search.step === "string" ? search.step : undefined,
  }),
  component: NewWorkPage,
});
const onboardingRoute = createRoute({ getParentRoute: () => rootRoute, path: "/onboarding", component: OnboardingPage });
const workRoute = createRoute({ getParentRoute: () => rootRoute, path: "/works/$workId", component: WorkspacePage });

const writingRoomRoute = createRoute({ getParentRoute: () => rootRoute, path: "/writing-room", component: () => <PagePlaceholder titleKey="nav.writingRoom" /> });
const settingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings", component: AppearancePage });
const securitySettingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings/security", component: SecuritySettingsPage });
const modelsSettingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings/models", component: ModelsSettingsPage });
const rolesSettingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings/roles", component: () => <ModelsSettingsPage initialTab="roles" /> });
const limitsSettingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings/limits", component: () => <ModelsSettingsPage initialTab="limits" /> });
const concurrencySettingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings/concurrency", component: () => <ModelsSettingsPage initialTab="limits" /> });
const writingSettingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings/writing", component: () => <ModelsSettingsPage initialTab="limits" /> });
const logsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/logs", component: () => <PagePlaceholder titleKey="nav.logs" /> });

const routeTree = rootRoute.addChildren([libraryRoute, systemRoute, editorSpikeRoute, newWorkRoute, onboardingRoute, workRoute, writingRoomRoute, settingsRoute, modelsSettingsRoute, rolesSettingsRoute, limitsSettingsRoute, concurrencySettingsRoute, writingSettingsRoute, securitySettingsRoute, logsRoute]);

export const router = createRouter({ routeTree, history: createHashHistory() });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
