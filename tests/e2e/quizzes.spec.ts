import { randomUUID } from "node:crypto";
import type { Page } from "@playwright/test";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, apiOrigin, webOrigin } from "./fixtures";

type S = components["schemas"];

async function questions(page: Page) {
  await page.getByRole("link", { name: "Manage question banks" }).click();
  await page.getByLabel("Bank name").fill("C02 bank " + randomUUID());
  await page.getByRole("button", { name: "Create bank", exact: true }).click();
  await expect(page.getByRole("link", { name: "Create question", exact: true })).toBeVisible();
  const bank = page.url();
  const prompts: string[] = [];
  for (const kind of ["mcq", "true_false"] as const) {
    await page.goto(bank);
    await page.getByRole("link", { name: "Create question", exact: true }).click();
    const prompt = `C02 ${kind} ${randomUUID()}`;
    prompts.push(prompt);
    await page.getByLabel("Question type").selectOption(kind);
    await page.getByLabel("Prompt", { exact: true }).fill(prompt);
    await page.getByLabel("Default points").fill("3");
    await page.getByLabel("Explanatory feedback").fill("C02 private feedback sentinel");
    if (kind === "mcq") {
      await page.getByLabel("Option 1", { exact: true }).fill("First choice");
      await page.getByLabel("Option 2", { exact: true }).fill("Second choice");
    }
    await page.getByLabel("Correct option 1", { exact: true }).check();
    await page.getByRole("button", { name: "Create question", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
  }
  return prompts;
}

async function compose(page: Page, title: string, prompts: string[]) {
  await page.goto("/author/quizzes");
  await page.getByLabel("Quiz title").fill(title);
  await page.getByLabel("Instructions", { exact: true }).fill("C02 literal <b>instructions</b>");
  for (const prompt of prompts) {
    while (await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).count() === 0) {
      await page.getByRole("button", { name: "Next available questions" }).click();
    }
    await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).click();
  }
  await page.getByLabel("Point override for question 1").fill("7");
  await page.getByRole("button", { name: "Create quiz", exact: true }).click();
  await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  return new URL(page.url()).pathname;
}

async function quizSnapshot(token: string, path: string) {
  const quizResponse = await fetch(apiOrigin + "/api/v1/quizzes/" + path.split("/").at(-1), {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(quizResponse.status).toBe(200);
  const quiz: S["Quiz"] = await quizResponse.json();
  const response = await fetch(`${apiOrigin}/api/v1/quizzes/${quiz.id}/versions/${quiz.publishedVersionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status).toBe(200);
  const version: S["PublishedQuiz"] = await response.json();
  return version;
}

test("C02 AT-04/05 author composes previews publishes and explicitly revises immutable quizzes", async ({ page, apps }) => {
  test.setTimeout(120_000);
  await login(page, "author");
  const token = (await apps.session(page)).access_token;
  const prompts = await questions(page);
  prompts.forEach((prompt) => apps.assessmentContent.add(prompt));
  apps.assessmentContent.add("C02 private feedback sentinel");
  const title = "C02 quiz " + randomUUID();
  const path = await compose(page, title, prompts);
  await page.getByRole("button", { name: "Move question 2 up" }).click();
  await page.getByLabel("Release preset").selectOption("never");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Edit draft revision 2" })).toBeVisible();
  const before = await apps.apiDb.query("SELECT count(*)::int AS n FROM quezo.quiz_publication_events");
  await page.getByRole("link", { name: "Preview saved draft" }).click();
  await expect(page.getByRole("heading", { name: `Preview: ${title}`, exact: true })).toBeVisible();
  await expect(page.getByText("Possible points: 10", { exact: true })).toBeVisible();
  await expect(page.locator("main fieldset").first()).toContainText(prompts[1]!);
  await page.getByLabel("True", { exact: true }).check();
  const previewHtml = await page.content();
  expect(previewHtml.includes("C02 private feedback sentinel") || previewHtml.includes("correctOptionId"),
    "Preview HTML/RSC never contains private grading fields").toBe(false);
  expect((await apps.apiDb.query("SELECT count(*)::int AS n FROM quezo.quiz_publication_events")).rows).toEqual(before.rows);
  await page.getByRole("link", { name: "Back to quiz" }).click();
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft" }).click();
  await expect(page.getByRole("link", { name: "View published version" })).toBeVisible();
  const first = await quizSnapshot(token, path);
  expect(first.policy.scoreRelease).toBe("never");
  expect(first.questions.map((item) => item.effectivePoints)).toEqual([3, 7]);
  await page.getByRole("link", { name: "View published version" }).click();
  await expect(page.getByRole("heading", { name: `Published: ${title}`, exact: true })).toBeVisible();
  const publishedPath = page.url();
  await page.reload();
  await expect(page.getByText("Possible points: 10", { exact: true })).toBeVisible();
  const secondPath = await compose(page, "C02 reused " + randomUUID(), [prompts[0]!]);
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft" }).click();
  await expect(page.getByRole("link", { name: "View published version" })).toBeVisible();
  const second = await quizSnapshot(token, secondPath);
  expect(second.questions[0]!.question.versionId).toBe(first.questions[1]!.question.versionId);
  await page.goto(`/author/questions/${first.questions[1]!.question.questionId}`);
  await page.getByLabel("Prompt", { exact: true }).fill("C02 changed question");
  await page.getByRole("button", { name: "Save new revision" }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 2" })).toBeVisible();
  await page.goto(path);
  await page.getByRole("button", { name: "Create new revision draft" }).click();
  await expect(page.getByRole("heading", { name: "Edit draft revision 3" })).toBeVisible();
  await page.getByLabel("Quiz title").fill("C02 revised quiz");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Edit draft revision 4" })).toBeVisible();
  expect(await quizSnapshot(token, path)).toEqual(first);
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft" }).click();
  await expect(page.getByRole("button", { name: "Create new revision draft" })).toBeVisible();
  const revised = await quizSnapshot(token, path);
  expect(revised.id).not.toBe(first.id);
  expect(revised.questions).toEqual(first.questions);
  await page.goto(publishedPath);
  await expect(page.getByRole("heading", { name: `Published: ${title}`, exact: true })).toBeVisible();
});

test("C02 stale composition and publication outage fail visibly without losing edits", async ({ page, apps, context }) => {
  test.setTimeout(120_000);
  await login(page, "combined");
  const prompts = await questions(page);
  const path = await compose(page, "C02 conflict " + randomUUID(), [prompts[0]!]);
  const second = await context.newPage();
  try {
    await second.goto(path);
    await second.getByLabel("Quiz title").fill("C02 other tab");
    await second.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(second.getByRole("heading", { name: "Edit draft revision 2" })).toBeVisible();
    await page.getByLabel("Quiz title").fill("C02 unsaved");
    await page.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(page.locator("main").getByRole("alert")).toContainText("changed in another tab");
    await expect(page.getByLabel("Quiz title")).toHaveValue("C02 unsaved");
    await page.reload();
    await page.getByLabel("I confirm publication of this saved draft").check();
    await apps.stopApi();
    try {
      await page.getByRole("button", { name: "Publish saved draft" }).click();
      await expect(page.locator("main").getByRole("alert")).toContainText("unavailable");
      await expect(page.getByRole("link", { name: "View published version" })).toHaveCount(0);
    } finally { await apps.startApi(); }
    await page.getByRole("button", { name: "Publish saved draft" }).click();
    await expect(page.getByRole("link", { name: "View published version" })).toBeVisible();
  } finally { await second.close(); }
});

test("C02 real login ownership and publish retry are enforced before disclosure", async ({ page, apps, browser }) => {
  test.setTimeout(120_000);
  await login(page, "author");
  const token = (await apps.session(page)).access_token;
  const prompts = await questions(page);
  const path = await compose(page, "C02 private " + randomUUID(), [prompts[0]!]);
  const id = path.split("/").at(-1)!;
  const key = randomUUID();
  const send = (bearer: string, expectedRevision = 1) => fetch(`${apiOrigin}/api/v1/quizzes/${id}/publish`, {
    method: "POST", headers: { Authorization: `Bearer ${bearer}`, "Content-Type": "application/json", "Idempotency-Key": key },
    body: JSON.stringify({ expectedRevision }),
  });
  const first = await send(token);
  expect(first.status).toBe(201);
  const ack = await first.json();
  await apps.stopApi();
  await apps.startApi();
  const retry = await send(token);
  expect(retry.status).toBe(200);
  expect(await retry.json()).toEqual(ack);
  expect((await send(token, 2)).status).toBe(409);
  for (const name of ["combined", "learner", "administrator"]) {
    const context = await browser.newContext({ baseURL: webOrigin });
    const other = await context.newPage();
    try {
      await login(other, name);
      const otherToken = (await apps.session(other)).access_token;
      expect((await send(otherToken)).status).toBe(name === "combined" ? 404 : 403);
      for (const url of [path, `${path}/preview`, `${path}/versions/${ack.versionId}`]) {
        const response = await other.goto(url);
        await expect(other.locator("main").getByRole("alert")).toBeVisible();
        expect((await response!.text()).includes(prompts[0]!), "No foreign prompt in HTML/RSC").toBe(false);
      }
    } finally { await context.close(); }
  }
});
