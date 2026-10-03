import { expect, test } from "@playwright/test";

test("new work wizard has seven steps and saves each completed step", async ({ page }) => {
  let revision = 1;
  const savedSteps: string[] = [];
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", (route) => route.fulfill({ json: { status: "completed", step: null, revision: 1, steps: {}, platform: "test" } }));
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/works**", async (route) => {
    if (route.request().url().endsWith("/chapters")) {
      await route.fulfill({ json: [] });
    } else if (route.request().method() === "GET" && route.request().url().endsWith("wizard-work")) {
      await route.fulfill({ json: { id: "wizard-work", revision, title: "Hành trình mới", genre: null, brief: "", target_chapters: 20, chapter_length_min: 1500, chapter_length_max: 2500, autowrite_mode_default: "review_each", wizard_step: savedSteps.at(-1) ?? "basics", wizard_completed_steps: savedSteps, style_profile: { revision: 1, vocab_register: "balanced", dialogue_style: "dash", tone_mark_style: "new" } } });
    } else if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { wizard_step: string };
      savedSteps.push(body.wizard_step); revision = 1;
      await route.fulfill({ status: 201, json: { id: "wizard-work", revision } });
    } else if (route.request().method() === "PATCH") {
      const body = route.request().postDataJSON() as { wizard_step: string | null };
      if (body.wizard_step) savedSteps.push(body.wizard_step);
      revision += 1;
      await route.fulfill({ json: { id: "wizard-work", revision } });
    } else {
      await route.fulfill({ json: { items: [], next_cursor: null } });
    }
  });

  await page.goto("/#/new");
  await expect(page.getByRole("navigation", { name: "Các bước tạo truyện" }).getByRole("button")).toHaveCount(7);
  await page.getByLabel("Tên truyện").fill("Hành trình mới");
  for (let step = 0; step < 6; step += 1) await page.getByRole("button", { name: "Lưu và tiếp tục" }).click();
  await expect(page.getByRole("heading", { name: "Kiểm tra thông tin truyện" })).toBeVisible();
  expect(savedSteps).toContain("writing_config");
  await page.getByRole("button", { name: "Hoàn tất" }).click();
  await expect(page).toHaveURL(/wizard-work/);
});

test("wizard reopens a saved draft at its persisted step with saved fields", async ({ page }) => {
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", (route) => route.fulfill({ json: { status: "completed", step: null, revision: 1, steps: {}, platform: "test" } }));
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/works/wizard-work", (route) => route.fulfill({ json: {
    id: "wizard-work", revision: 3, title: "Bản nháp tiếp tục", genre: "urban", brief: "Nhân vật tìm đường về nhà.", target_chapters: 30,
    chapter_length_min: 1200, chapter_length_max: 2100, autowrite_mode_default: "review_each", wizard_step: "brief", wizard_completed_steps: ["basics"],
    style_profile: { revision: 2, vocab_register: "thuan_viet", dialogue_style: "quotes", tone_mark_style: "old" },
  } }));
  await page.goto("/#/new?workId=wizard-work&step=brief");
  await expect(page.getByRole("heading", { name: "Tạo truyện mới" })).toBeVisible();
  await expect(page.getByLabel("Tóm tắt truyện")).toHaveValue("Nhân vật tìm đường về nhà.");
  await expect(page.getByText("Bước 2 / 7")).toBeVisible();
});
