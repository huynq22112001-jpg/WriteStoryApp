import { expect, test } from "@playwright/test";

test("editor autosaves working copy and Ctrl+S requests a revision snapshot", async ({ page }) => {
  let writes = 0;
  let snapshots = 0;
  let forceConflict = false;
  await page.route("**/v1/events**", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
  await page.route("**/v1/onboarding", (route) => route.fulfill({ json: { status: "completed", step: null, revision: 1, steps: {}, platform: "test" } }));
  await page.route("**/v1/vault/status", (route) => route.fulfill({ json: { state: "absent", mode: "undecided", waiting_jobs: 0, revision: 1 } }));
  await page.route("**/v1/works/work-1/chapters", (route) => route.fulfill({ json: [{ id: "chapter-1", work_id: "work-1", chapter_no: 1, title: "Mở đầu", status: "draft", revision_count: 0, current_revision_id: null, syllable_count: 0 }] }));
  await page.route("**/v1/chapters/chapter-1/working-copy", async (route) => {
    if (route.request().method() === "PUT") {
      writes += 1;
      if (forceConflict) return route.fulfill({ status: 409, json: { code: "REVISION_CONFLICT", message: "new revision" } });
      const body = route.request().postDataJSON() as { doc_json: unknown; client_session_id: string };
      await route.fulfill({ json: { chapter_id: "chapter-1", base_revision_id: null, doc_json: body.doc_json, has_changes: true, client_seq: writes, client_session_id: body.client_session_id } });
    } else {
      await route.fulfill({ json: { chapter_id: "chapter-1", base_revision_id: null, doc_json: { type: "doc", content: [{ type: "paragraph", attrs: { paragraph_id: "para0001" } }] }, has_changes: false, client_seq: 0 } });
    }
  });
  await page.route("**/v1/chapters/chapter-1", (route) => route.fulfill({ json: { id: "chapter-1", work_id: "work-1", chapter_no: 1, title: "Mở đầu", status: "draft", revision_count: 0, current_revision_id: null, syllable_count: 0, is_base_locked: false } }));
  await page.route("**/v1/chapters/chapter-1/snapshot", async (route) => { snapshots += 1; await route.fulfill({ json: { created: true, revision: { revision_no: snapshots } } }); });
  await page.route("**/v1/chapters/chapter-1/revisions", (route) => route.fulfill({ json: [{ id: "rev-1", revision_no: 1, reason: "manual_snapshot", source: "human", created_at: "2026-10-03T00:00:00Z", plain_text: "Bản cũ.", paragraphs: [] }] }));
  await page.route("**/v1/chapters/chapter-1/revisions/rev-1/diff/working", (route) => route.fulfill({ json: { before: { plain_text: "Bản cũ." }, after: { paragraphs: [{ text: "Bản mới." }] } } }));
  await page.route("**/v1/chapters/chapter-1/revisions/rev-1/restore", (route) => route.fulfill({ json: { created: true, revision: { revision_no: 3 } } }));

  await page.goto("/#/works/work-1");
  const editor = page.locator('[contenteditable="true"]');
  await expect(editor).toBeVisible();
  await editor.fill("Một đoạn văn mới.");
  await expect.poll(() => writes).toBeGreaterThan(0);
  await expect(page.getByRole("status").first()).toContainText("Đã lưu");
  await page.getByRole("button", { name: "Lưu phiên bản Ctrl+S" }).click();
  await expect.poll(() => snapshots).toBe(1);
  await editor.focus();
  await page.keyboard.press("Control+s");
  await expect.poll(() => snapshots).toBe(2);
  forceConflict = true;
  const writesBeforeConflict = writes;
  await editor.fill("Bản nháp xung đột.");
  await expect.poll(() => writes).toBeGreaterThan(writesBeforeConflict);
  await expect(page.getByRole("alert")).toContainText("Chương vừa có bản mới");
  await expect(page.getByRole("button", { name: "Giữ bản của tôi" })).toBeVisible();
  forceConflict = false;
  await page.getByRole("button", { name: "Giữ bản của tôi" }).click();
  await page.getByRole("button", { name: "Lịch sử" }).click();
  await expect(page.getByText("Bản v1")).toBeVisible();
  await page.getByRole("button", { name: "So sánh" }).click();
  await expect(page.getByLabel("So sánh theo từ với bản đang sửa")).toContainText("mới.");
  await page.getByRole("button", { name: "Khôi phục" }).click();
});
