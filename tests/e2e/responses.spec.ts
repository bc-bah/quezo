import { randomUUID } from "node:crypto";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, accounts, apiOrigin } from "./fixtures";

type S = components["schemas"];

test("D02 AT-07/08 durable answers and D03 pending-save submission and lost completion response", async ({ page, apps }) => {
  test.setTimeout(240_000);
  page.setDefaultTimeout(15_000);
  console.log("D02 Chromium version: " + page.context().browser()!.version());
  await login(page, "author");
  await page.getByRole("link", { name: "Manage question banks" }).click();
  await page.getByLabel("Bank name").fill("D02 bank " + randomUUID());
  await page.getByRole("button", { name: "Create bank", exact: true }).click();
  await expect(page.getByRole("link", { name: "Create question", exact: true })).toBeVisible();
  const bank = page.url();
  const prompts: string[] = [];
  const feedback = "D02 private scoring sentinel " + randomUUID();
  apps.assessmentContent.add(feedback);
  for (const kind of ["mcq", "true_false"] as const) {
    await page.goto(bank);
    await page.getByRole("link", { name: "Create question", exact: true }).click();
    const prompt = "D02 " + kind + " " + randomUUID();
    prompts.push(prompt); apps.assessmentContent.add(prompt);
    await page.getByLabel("Question type").selectOption(kind);
    await page.getByLabel("Prompt", { exact: true }).fill(prompt);
    await page.getByLabel("Explanatory feedback").fill(feedback);
    if (kind === "mcq") {
      await page.getByLabel("Option 1", { exact: true }).fill("D02 first");
      await page.getByLabel("Option 2", { exact: true }).fill("D02 second");
    }
    await page.getByLabel("Correct option 1", { exact: true }).check();
    await page.getByRole("button", { name: "Create question", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
  }
  const title = "D02 quiz " + randomUUID();
  await page.goto("/author/quizzes");
  await page.getByLabel("Quiz title").fill(title);
  for (const prompt of prompts) {
    while (await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).count() === 0) {
      await page.getByRole("button", { name: "Next available questions" }).click();
    }
    await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).click();
  }
  await page.getByRole("button", { name: "Create quiz", exact: true }).click();
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft" }).click();
  await page.getByRole("link", { name: "View published version" }).click();
  await page.getByLabel("Active learner").selectOption(accounts.learner!.id);
  await page.getByRole("button", { name: "Assign learner", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Assignment confirmed");
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  // Local logout deliberately retains provider SSO; start a fresh browser identity for the learner.
  await page.context().clearCookies();
  await login(page, "learner");
  console.log("D02 checkpoint: learner signed in");
  await page.getByRole("link", { name: "My assignments", exact: true }).click();
  await page.getByRole("region", { name: title, exact: true }).getByRole("button", { name: "Start attempt", exact: true }).click();
  await expect(page).toHaveURL(/\/learner\/attempts\/[0-9a-f-]+$/);
  const url = page.url();
  const attemptId = new URL(url).pathname.split("/").at(-1)!;
  const token = (await apps.session(page)).access_token;
  const snapshot = async () => {
    const response = await fetch(`${apiOrigin}/api/v1/attempts/${attemptId}`, { headers: { Authorization: `Bearer ${token}` } });
    expect(response.status).toBe(200);
    const raw = await response.text();
    expect([feedback, "correctOptionId", "defaultPoints", "fingerprint"].some((key) => raw.includes(key)),
      "Learner JSON excludes private scoring and request ledger").toBe(false);
    return JSON.parse(raw) as S["Attempt"];
  };
  const initial = await snapshot();
  expect(initial.questions.map((q) => q.response.revision)).toEqual([0, 0]);
  const q = page.locator("[data-question-id]").first();
  await expect(q.getByRole("status")).toHaveText("Unanswered");
  await q.getByLabel("D02 first", { exact: true }).check();
  await q.getByRole("button", { name: "Save answer", exact: true }).click();
  await expect(q.getByRole("status")).toHaveText("Saved");
  console.log("D02 checkpoint: initial save acknowledged");
  await page.reload();
  await expect(q.getByLabel("D02 first", { exact: true })).toBeChecked();
  await apps.stopApi(); await apps.startApi(); await apps.restartWeb();
  await page.reload();
  await expect(q.getByLabel("D02 first", { exact: true })).toBeChecked();
  expect((await snapshot()).questions[0]!.response.revision).toBe(1);
  console.log("D02 checkpoint: application restart preserved answer");
  expect((await page.content()).includes(feedback), "Learner HTML/RSC omits private feedback").toBe(false);
  await q.getByRole("button", { name: "Clear answer" }).click();
  await q.getByRole("button", { name: "Save answer", exact: true }).click();
  await expect(q.getByRole("status")).toHaveText("Saved");
  await page.reload();
  expect(await q.getByRole("radio", { checked: true }).count()).toBe(0);
  const secondQuestion = page.locator("[data-question-id]").nth(1);
  await page.getByRole("navigation", { name: "Questions" }).getByRole("link", { name: "Question 2" }).click();
  await secondQuestion.getByLabel("True", { exact: true }).check();
  await secondQuestion.getByRole("button", { name: "Save answer", exact: true }).click();
  await expect(secondQuestion.getByRole("status")).toHaveText("Saved");

  const other = await page.context().newPage();
  try {
    await other.goto(url);
    const otherQ = other.locator("[data-question-id]").first();
    await otherQ.getByLabel("D02 second", { exact: true }).check();
    await q.getByLabel("D02 first", { exact: true }).check();
    await q.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect(q.getByRole("status")).toHaveText("Saved");
    await otherQ.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect(otherQ.getByRole("status")).toContainText("Conflict");
    await expect(otherQ.getByLabel("D02 second", { exact: true })).toBeChecked();
    await expect(otherQ.getByRole("button", { name: "Save answer", exact: true })).toBeDisabled();
    await expect(other.getByRole("button", { name: "Submit attempt", exact: true })).toBeDisabled();
    await otherQ.getByRole("button", { name: "Keep my local answer" }).click();
    await otherQ.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect(otherQ.getByRole("status")).toHaveText("Saved");
    await page.getByRole("button", { name: "Reconcile saved answers" }).click();
    await expect(q.getByLabel("D02 second", { exact: true })).toBeChecked();
  } finally { await other.close(); }
  console.log("D02 checkpoint: cross-tab conflict resolved");

  await page.context().setOffline(true);
  await q.getByLabel("D02 first", { exact: true }).check();
  await expect(page.getByText("Offline - local edits are not saved.", { exact: false })).toBeVisible();
  await expect(q.getByRole("button", { name: "Save answer", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Submit attempt", exact: true })).toBeDisabled();
  const dialog = page.waitForEvent("dialog");
  const leave = page.getByRole("link", { name: "My assignments", exact: true }).click();
  const warning = await dialog;
  expect(warning.message()).toContain("discard unsaved");
  await warning.dismiss(); await leave;
  expect(page.url()).toContain(attemptId);
  await page.context().setOffline(false);
  await expect(page.getByRole("status").first()).toContainText("Persisted answers reconciled");
  await q.getByRole("button", { name: "Save answer", exact: true }).click();
  await expect(q.getByRole("status")).toHaveText("Saved");
  console.log("D02 checkpoint: offline edit reconciled and saved");

  const held = await apps.apiDb.connect();
  try {
    await held.query("BEGIN");
    await held.query("SELECT id FROM quezo.attempts WHERE id = $1 FOR UPDATE", [attemptId]);
    await q.getByLabel("D02 second", { exact: true }).check();
    await q.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect(q.getByRole("status")).toHaveText("Saving");
    await expect(page.getByText("Waiting for pending saves before submission.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Submit attempt", exact: true })).toBeDisabled();
    await q.getByLabel("D02 first", { exact: true }).check();
    await held.query("COMMIT");
    await expect(q.getByRole("status")).toContainText("newer edit");
    await expect(page.getByRole("button", { name: "Submit attempt", exact: true })).toBeDisabled();
    await expect(q.getByLabel("D02 first", { exact: true })).toBeChecked();
    await q.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect(q.getByRole("status")).toHaveText("Saved");
    console.log("D02 checkpoint: newer edit preserved during save");

    const before = (await snapshot()).questions[0]!.response.revision;
    await held.query("BEGIN");
    await held.query("SELECT id FROM quezo.attempts WHERE id = $1 FOR UPDATE", [attemptId]);
    await q.getByLabel("D02 second", { exact: true }).check();
    await q.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect.poll(async () => (await apps.apiDb.query(
      "SELECT count(*)::int AS n FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'",
    )).rows[0].n).toBeGreaterThan(0);
    await apps.backendTransport.close();
    await held.query("COMMIT");
    await expect.poll(async () => (await apps.apiDb.query(
      "SELECT revision::int FROM quezo.attempt_responses WHERE question_id = $1", [initial.questions[0]!.attemptQuestionId],
    )).rows[0].revision).toBe(before + 1);
    await expect(q.getByRole("status")).toContainText("not confirmed saved");
    await expect(page.getByRole("button", { name: "Submit attempt", exact: true })).toBeDisabled();
    await apps.backendTransport.open();
    await page.getByRole("button", { name: "Reconcile saved answers" }).click();
    await expect(page.getByRole("status").first()).toContainText("Persisted answers reconciled");
    await q.getByRole("button", { name: "Retry save" }).click();
    await expect(q.getByRole("status")).toHaveText("Saved");
    expect((await snapshot()).questions[0]!.response.revision).toBe(before + 1);
    console.log("D02 checkpoint: lost acknowledgement replayed without revision increment");
    await page.getByRole("button", { name: "Reconcile saved answers" }).click();
    await expect(page.getByRole("status").first()).toContainText("Persisted answers reconciled");
  } finally {
    await held.query("ROLLBACK"); held.release();
    await page.context().setOffline(false);
  }

  await apps.stopApi();
  try {
    await q.getByLabel("D02 first", { exact: true }).check();
    await q.getByRole("button", { name: "Save answer", exact: true }).click();
    await expect(q.getByRole("status")).toContainText("not confirmed saved");
    await expect(q.getByLabel("D02 first", { exact: true })).toBeChecked();
  } finally { await apps.startApi(); }
  await page.getByRole("button", { name: "Reconcile saved answers" }).click();
  await expect(page.getByRole("status").first()).toContainText("Persisted answers reconciled");
  await q.getByRole("button", { name: "Retry save" }).click();
  await expect(q.getByRole("status")).toHaveText("Saved");
  await page.reload();
  await expect(q.getByLabel("D02 first", { exact: true })).toBeChecked();
  expect((await snapshot()).questions[1]!.response.revision).toBe(1);
  console.log("D02 checkpoint: safe failure recovery and final refresh complete");
  await secondQuestion.getByRole("button", { name: "Clear answer" }).click();
  await secondQuestion.getByRole("button", { name: "Save answer", exact: true }).click();
  await expect(secondQuestion.getByRole("status")).toHaveText("Saved");
  page.once("dialog", async (confirmation) => {
    expect(confirmation.message()).toContain("1 unanswered question");
    await confirmation.dismiss();
  });
  await page.getByRole("button", { name: "Submit attempt", exact: true }).click();
  expect((await snapshot()).state).toBe("in_progress");
  const completionLock = await apps.apiDb.connect();
  try {
    await completionLock.query("BEGIN");
    await completionLock.query("SELECT id FROM quezo.attempts WHERE id = $1 FOR UPDATE", [attemptId]);
    page.once("dialog", (confirmation) => confirmation.accept());
    await page.getByRole("button", { name: "Submit attempt", exact: true }).click();
    await expect(page.getByRole("button", { name: "Submitting", exact: true })).toBeDisabled();
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    await expect(page.getByRole("status").first()).toHaveText("Submitting saved answers. Please wait.");
    await expect(page.getByRole("button", { name: "Reconcile saved answers" })).toBeDisabled();
    await expect.poll(async () => (await apps.apiDb.query(
      "SELECT count(*)::int AS n FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock'",
    )).rows[0].n).toBeGreaterThan(0);
    await apps.backendTransport.close();
    await completionLock.query("COMMIT");
    await expect.poll(async () => (await apps.apiDb.query(
      "SELECT count(*)::int AS n FROM quezo.grades WHERE attempt_id=$1", [attemptId],
    )).rows[0].n).toBe(1);
    await expect(page.getByRole("status").first()).toContainText("Submission outcome is not confirmed");
    await expect(q.getByRole("radio").first()).toBeDisabled();
    await apps.backendTransport.open();
    await page.getByRole("button", { name: "Retry submission", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Submission confirmed", exact: true })).toBeVisible();
  } finally {
    await completionLock.query("ROLLBACK"); completionLock.release();
  }
  const completed = await snapshot();
  expect(completed.completion?.completionReason).toBe("submitted");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Submission confirmed", exact: true })).toBeVisible();
  await expect(q.getByRole("radio").first()).toBeDisabled();
  expect((await snapshot()).completion).toEqual(completed.completion);
  const html = await page.content();
  expect([feedback, "earnedPoints", "correctOptionId", "gradeId", '"outcome"'].some((key) => html.includes(key)),
    "Completion HTML/RSC omits withheld grade, key and feedback").toBe(false);
  expect((await apps.apiDb.query(
    "SELECT count(*)::int AS n FROM quezo.grades WHERE attempt_id=$1", [attemptId],
  )).rows[0].n).toBe(1);
});
