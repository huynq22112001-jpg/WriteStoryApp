import { expect, test } from "@playwright/test";

test("library uses a mock API and creates a work", async ({ page }) => {
  const works: { id: string; title: string; genre: string | null; committed_chapters: number; target_chapters: number | null; badge: { label_key: string }; updated_at: string }[] = [];
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", (route) => route.fulfill({ json: { status: "completed", step: null, revision: 1, steps: {}, platform: "test" } }));
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/works**", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { title: string };
      works.push({ id: "work-1", title: body.title, genre: null, committed_chapters: 0, target_chapters: null, badge: { label_key: "Bản nháp" }, updated_at: new Date().toISOString() });
      await route.fulfill({ status: 201, json: { id: "work-1" } });
      return;
    }
    await route.fulfill({ json: { items: works, next_cursor: null } });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Thư viện" })).toBeVisible();
  await page.getByRole("button", { name: "Tạo truyện", exact: true }).click();
  await page.getByLabel("Tên truyện").fill("Mùa gió mới");
  await page.getByRole("button", { name: "Tạo truyện", exact: true }).last().click();
  await expect(page).toHaveURL(/work-1/);
});
