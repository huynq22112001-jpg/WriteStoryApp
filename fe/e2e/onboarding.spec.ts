import { expect, test } from "@playwright/test";

test("onboarding advances from security to provider setup using a mocked backend", async ({ page }) => {
  let revision = 1;
  const steps: Record<string, string> = {};
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", async (route) => {
    if (route.request().method() === "PUT") {
      const body = route.request().postDataJSON() as { step: string };
      steps[body.step] = "done"; revision += 1;
      await route.fulfill({ json: { status: "pending", step: body.step, revision, steps, platform: "test" } });
      return;
    }
    await route.fulfill({ json: { status: "pending", step: "security", revision, steps, platform: "test" } });
  });
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/vault/mode", (route) => route.fulfill({ json: { state: "absent", mode: "session_only", revision: 2 } }));

  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: "Thư mục dữ liệu" })).toBeVisible();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page.getByRole("heading", { name: "Bảo vệ API key" })).toBeVisible();
  await page.getByRole("button", { name: "Chỉ dùng key trong phiên này" }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page.getByRole("heading", { name: "Kết nối nhà cung cấp AI" })).toBeVisible();
  expect(steps.security).toBe("done");
});

test("onboarding completes into the new-work wizard", async ({ page }) => {
  let revision = 1;
  let completed = false;
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", async (route) => {
    if (route.request().method() === "PUT") { revision += 1; await route.fulfill({ json: { status: "pending", step: "provider", revision, steps: { data_root: "done", security: "done", provider: "pending", first_work: "pending" }, platform: "test" } }); return; }
    await route.fulfill({ json: { status: completed ? "completed" : "pending", step: completed ? null : "security", revision, steps: { data_root: "done", security: completed ? "done" : "pending", provider: completed ? "skipped" : "pending", first_work: completed ? "done" : "pending" }, platform: "test" } });
  });
  await page.route("**/v1/onboarding/complete", async (route) => { completed = true; await route.fulfill({ json: { status: "completed", step: null, revision: revision + 1, steps: { data_root: "done", security: "done", provider: "skipped", first_work: "done" }, platform: "test" } }); });
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/vault/mode", (route) => route.fulfill({ json: { state: "absent", mode: "session_only", revision: 2 } }));
  await page.goto("/onboarding");
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await page.getByRole("button", { name: "Chỉ dùng key trong phiên này" }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page.getByRole("heading", { name: "Kết nối nhà cung cấp AI" })).toBeVisible();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page.getByRole("heading", { name: "Tạo truyện đầu tiên" })).toBeVisible();
  await page.getByRole("button", { name: "Tạo truyện mới" }).click();
  await expect(page).toHaveURL(/#\/new/);
});
