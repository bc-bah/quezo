import { randomUUID } from "node:crypto";
import type { Page } from "@playwright/test";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, apiOrigin, accounts, webOrigin } from "./fixtures";

async function createBank(page: Page) {
  await page.getByRole("link", { name: "Manage question banks" }).click();
  await page.getByLabel("Bank name").fill("C01 synthetic bank " + randomUUID());
  await page.getByRole("button", { name: "Create bank", exact: true }).click();
  await expect(page.getByRole("link", { name: "Create question", exact: true })).toBeVisible();
  return new URL(page.url()).pathname;
}

async function fillQuestion(page: Page, kind: "mcq" | "true_false", prompt: string) {
  await page.getByRole("link", { name: "Create question", exact: true }).click();
  await page.getByLabel("Question type").selectOption(kind);
  await page.getByLabel("Prompt", { exact: true }).fill(prompt);
  await page.getByLabel("Default points").fill("0");
  await page.getByLabel("Explanatory feedback").fill("C01 literal explanation <b>not markup</b>");
  if (kind === "mcq") {
    await page.getByLabel("Option 1", { exact: true }).fill("First literal choice");
    await page.getByLabel("Option 2", { exact: true }).fill("Second literal choice");
    await page.getByRole("button", { name: "Add option" }).click();
    await page.getByLabel("Option 3", { exact: true }).fill("Third literal choice");
  } else {
    await expect(page.getByLabel("Option 1", { exact: true })).toHaveValue("True");
    await expect(page.getByLabel("Option 2", { exact: true })).toHaveValue("False");
    await expect(page.getByRole("button", { name: "Add option" })).toHaveCount(0);
  }
  await page.getByLabel("Correct option 2", { exact: true }).check();
}

async function exactVersion(page: Page, token: string) {
  const parts = new URL(page.url()).pathname.split("/");
  const questionId = parts[3]!, versionId = parts[5]!;
  const response = await fetch(`${apiOrigin}/api/v1/questions/${questionId}/versions/${versionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("private, no-store");
  const version: components["schemas"]["QuestionVersion"] = await response.json();
  expect(version.versionId).toBe(versionId);
  return version;
}

for (const kind of ["mcq", "true_false"] as const) {
  test(`C01 AT-03/04 ${kind} author creates edits and selects immutable revisions`, async ({ page, apps }) => {
    await login(page, "author");
    const token = (await apps.session(page)).access_token;
    const bankPath = await createBank(page);
    await page.getByLabel("Bank name").fill("Renamed C01 " + kind);
    await page.getByRole("button", { name: "Save bank name" }).click();
    await expect(page.getByRole("heading", { name: "Renamed C01 " + kind, exact: true })).toBeVisible();
    const prompt = `C01 ${kind} <img src=x onerror=alert(1)> literal ${randomUUID()}`;
    apps.assessmentContent.add(prompt);
    apps.assessmentContent.add("C01 literal explanation <b>not markup</b>");
    await fillQuestion(page, kind, prompt);
    await page.getByRole("button", { name: "Create question", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
    const firstPath = new URL(page.url()).pathname;
    const initial = await exactVersion(page, token);
    apps.assessmentContent.add(initial.correctOptionId);
    expect(initial.questionType).toBe(kind);
    expect(initial.defaultPoints).toBe(0);
    await expect(page.getByTestId("question-prompt")).toHaveText(prompt);
    await expect(page.locator("main img")).toHaveCount(0);
    await page.reload();
    await expect(page.getByLabel("Selected version ID")).toHaveValue(initial.versionId);
    await page.getByRole("link", { name: "Edit current revision or select another" }).click();
    await expect(page.getByRole("heading", { name: "Question revisions", exact: true })).toBeVisible();
    await page.getByLabel("Prompt", { exact: true }).fill(" ");
    await page.getByRole("button", { name: "Save new revision" }).click();
    await expect(page.locator("main").getByRole("alert")).toContainText("invalid");
    await expect(page.getByLabel("Prompt", { exact: true })).toHaveValue(" ");
    await page.getByLabel("Prompt", { exact: true }).fill("Revised " + prompt);
    await page.getByLabel("Default points").fill("10000");
    await page.getByLabel("Explanatory feedback").fill("Revised feedback");
    if (kind === "mcq") await page.getByLabel("Option 1", { exact: true }).fill("Revised first choice");
    await page.getByLabel("Correct option 1", { exact: true }).check();
    await page.getByRole("button", { name: "Save new revision" }).click();
    await expect(page.getByRole("heading", { name: "Selected question revision 2" })).toBeVisible();
    const revised = await exactVersion(page, token);
    expect(revised.questionId).toBe(initial.questionId);
    expect(revised.versionId).not.toBe(initial.versionId);
    expect(revised.options.map((option) => option.id)).toEqual(initial.options.map((option) => option.id));
    expect(revised.options[0]!.text).toBe(kind === "mcq" ? "Revised first choice" : "True");
    expect(revised.correctOptionId).toBe(initial.options[0]!.id);
    expect(revised.defaultPoints).toBe(10000);
    await page.goto(firstPath);
    expect(await exactVersion(page, token)).toEqual(initial);
    await expect(page.getByTestId("question-prompt")).toHaveText(prompt);
    await page.goto(bankPath);
    await page.getByRole("link", { name: "Read or edit question", exact: true }).click();
    await page.getByRole("link", { name: "Select revision 1", exact: true }).click();
    await expect(page.getByLabel("Selected version ID")).toHaveValue(initial.versionId);
  });
}

test("C01 signed-in foreign author and non-author roles cannot discover keys", async ({ page, apps, browser }) => {
  test.setTimeout(120_000);
  await login(page, "author");
  const token = (await apps.session(page)).access_token;
  const bankPath = await createBank(page);
  const prompt = "C01 private prompt " + randomUUID();
  await fillQuestion(page, "mcq", prompt);
  await page.getByRole("button", { name: "Create question", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
  const path = new URL(page.url()).pathname;
  const initial = await exactVersion(page, token);
  for (const name of ["combined", "learner", "administrator"]) {
    const context = await browser.newContext({ baseURL: webOrigin });
    const other = await context.newPage();
    try {
      await login(other, name);
      const otherToken = (await apps.session(other)).access_token;
      for (const url of [
        "/api/v1/question-banks", "/api/v1/questions", `/api/v1/questions/${initial.questionId}`,
        `/api/v1/questions/${initial.questionId}/versions/${initial.versionId}`,
        `/api/v1/questions?bankId=${initial.bankId}`,
      ]) {
        const response = await fetch(apiOrigin + url, { headers: { Authorization: `Bearer ${otherToken}` } });
        const payload = await response.text();
        expect(payload.includes(prompt) || payload.includes(initial.correctOptionId), "No foreign assessment disclosure").toBe(false);
        expect(response.status).toBe(name === "combined" ? (url === "/api/v1/question-banks" || url === "/api/v1/questions" ? 200 : 404) : 403);
      }
      for (const url of [bankPath, path, `/author/questions/${initial.questionId}`]) {
        const response = await other.goto(webOrigin + url);
        await expect(other.locator("main").getByRole("alert")).toBeVisible();
        expect((await response!.text()).includes(prompt), "Protected HTML and RSC exclude foreign content").toBe(false);
        await expect(other.getByRole("button", { name: "Save new revision" })).toHaveCount(0);
      }
    } finally { await context.close(); }
  }
});

test("C01 stale browser edit and live role revocation fail visibly", async ({ page, apps, context }) => {
  await login(page, "combined");
  const bankPath = await createBank(page);
  await fillQuestion(page, "true_false", "C01 concurrent question");
  await page.getByRole("button", { name: "Create question", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
  await page.getByRole("link", { name: "Edit current revision or select another" }).click();
  const editPath = page.url();
  const second = await context.newPage();
  try {
    await second.goto(editPath);
    await second.getByLabel("Prompt", { exact: true }).fill("Other tab's revision");
    await second.getByRole("button", { name: "Save new revision" }).click();
    await expect(second.getByRole("heading", { name: "Selected question revision 2" })).toBeVisible();
    await page.getByLabel("Prompt", { exact: true }).fill("Unsaved local edit");
    await page.getByRole("button", { name: "Save new revision" }).click();
    await expect(page.locator("main").getByRole("alert")).toContainText("changed in another tab");
    await expect(page.getByLabel("Prompt", { exact: true })).toHaveValue("Unsaved local edit");
    await page.reload();
    await expect(page.getByRole("heading", { name: "Edit revision 2", exact: true })).toBeVisible();
    await expect(page.getByLabel("Prompt", { exact: true })).toHaveValue("Other tab's revision");
    await apps.apiDb.query("DELETE FROM quezo.account_roles WHERE account_id = $1 AND role = 'author'", [accounts.combined!.id]);
    await page.getByRole("button", { name: "Save new revision" }).click();
    await expect(page.locator("main").getByRole("alert")).toContainText("author role is required");
    await page.goto(bankPath);
    await expect(page.locator("main").getByRole("alert")).toContainText("author role is required");
  } finally {
    await apps.apiDb.query("INSERT INTO quezo.account_roles (account_id, role) VALUES ($1, 'author') ON CONFLICT DO NOTHING", [accounts.combined!.id]);
    await second.close();
  }
});

test("C01 dependency outage retains unsaved form and never reports success", async ({ page, apps }) => {
  await login(page, "author");
  await createBank(page);
  await fillQuestion(page, "mcq", "C01 recoverable edit");
  await apps.stopApi();
  try {
    await page.getByRole("button", { name: "Create question", exact: true }).click();
    await expect(page.locator("main").getByRole("alert")).toContainText("unavailable");
    await expect(page.getByLabel("Prompt", { exact: true })).toHaveValue("C01 recoverable edit");
    await expect(page.getByRole("heading", { name: /Selected question/ })).toHaveCount(0);
  } finally { await apps.startApi(); }
  await page.getByRole("button", { name: "Create question", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
});
