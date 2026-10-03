import { expect, test } from "@playwright/test";

test("workspace loads a base-locked chapter and exposes focus controls", async ({ page }) => {
  let pauseRequests = 0;
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", (route) => route.fulfill({ json: { status: "completed", step: null, revision: 1, steps: {}, platform: "test" } }));
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/works/work-1/chapters", (route) => route.fulfill({ json: [
    { id: "chapter-1", work_id: "work-1", chapter_no: 1, title: "Mở đầu", status: "draft", revision_count: 1, current_revision_id: "rev-1", syllable_count: 4 },
    { id: "chapter-2", work_id: "work-1", chapter_no: 2, title: "Gặp gỡ", status: "draft", revision_count: 0, current_revision_id: null, syllable_count: 0 },
  ] }));
  await page.route("**/v1/chapters/chapter-1/working-copy", (route) => route.fulfill({ json: { chapter_id: "chapter-1", base_revision_id: "rev-1", doc_json: { type: "doc", content: [{ type: "paragraph", attrs: { paragraph_id: "para0001" }, content: [{ type: "text", text: "Mở đầu." }] }] }, has_changes: false, client_seq: 0 } }));
  await page.route("**/v1/chapters/chapter-1", (route) => route.fulfill({ json: { id: "chapter-1", work_id: "work-1", chapter_no: 1, title: "Mở đầu", status: "draft", revision_count: 1, current_revision_id: "rev-1", syllable_count: 4, is_base_locked: true } }));
  await page.route("**/v1/works/work-1/autowrite/pause", async (route) => { pauseRequests += 1; await route.fulfill({ json: { accepted: true } }); });

  await page.goto("/#/works/work-1");
  await expect(page.getByRole("navigation", { name: "Cây chương" })).toContainText("Ch.1 Mở đầu");
  await expect(page.getByRole("status").filter({ hasText: "chế độ chỉ đọc" })).toBeVisible();
  await expect(page.getByTestId("chapter-editor")).toHaveAttribute("aria-readonly", "true");
  await page.getByRole("button", { name: "Tạm dừng để sửa" }).click();
  await expect.poll(() => pauseRequests).toBe(1);
  await expect(page.getByText("Đang dừng sau bước hiện tại…")).toBeVisible();
  await page.getByRole("button", { name: "Chế độ tập trung" }).click();
  await expect(page.getByRole("button", { name: "Thoát chế độ tập trung" })).toBeVisible();
});
