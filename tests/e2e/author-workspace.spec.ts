import { randomUUID } from "node:crypto";
import type { Page } from "@playwright/test";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, apiOrigin, accounts, webOrigin } from "./fixtures";

type S = components["schemas"];

async function api(token: string, path: string, method = "GET", body?: unknown, expected = 200) {
  const response = await fetch(apiOrigin + "/api/v1" + path, {
    method, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  expect(response.status, "Authorized API status").toBe(expected);
  return response;
}

async function bank(page: Page, name: string) {
  await page.goto("/author");
  await page.getByLabel("Bank name").fill(name);
  await page.getByRole("button", { name: "Create bank", exact: true }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  return new URL(page.url()).pathname;
}

async function question(page: Page, bankPath: string, prompt: string, category: string) {
  await page.goto(bankPath + "/new");
  await page.getByLabel("Question type").selectOption("true_false");
  await page.getByLabel("Prompt", { exact: true }).fill(prompt);
  await page.getByLabel("Category", { exact: true }).fill(category);
  await page.getByRole("button", { name: "Add tag", exact: true }).click();
  await page.getByLabel("Tag 1", { exact: true }).fill("C03-exact");
  await page.getByLabel("Default points").fill("3");
  await page.getByRole("button", { name: "Create question", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
  const parts = new URL(page.url()).pathname.split("/");
  return { questionId: parts[3]!, versionId: parts[5]! };
}

test("C03 AT-03 owned organization search pagination move and archive", async ({ page, apps }) => {
  test.setTimeout(120_000);
  await login(page, "author");
  const token = (await apps.session(page)).access_token;
  const marker = "C03-needle-" + randomUUID();
  const source = await bank(page, marker);
  const targetName = "C03 destination " + randomUUID();
  const target = await bank(page, targetName);
  const first = await question(page, source, marker + " one", marker);
  const second = await question(page, source, marker + " two", marker);
  apps.assessmentContent.add(marker);
  await page.goto("/author/questions");
  await page.getByLabel("Search text", { exact: true }).fill(marker.toUpperCase());
  await page.getByLabel("Filter category").fill(marker);
  await page.getByLabel("Filter tag").fill("C03-exact");
  await page.getByLabel("Questions per page").fill("1");
  await page.getByRole("button", { name: "Search questions", exact: true }).click();
  await expect(page.getByRole("link", { name: "Read or edit question", exact: true })).toHaveCount(1);
  await page.getByRole("link", { name: "Next questions", exact: true }).click();
  await expect(page.getByLabel("Filter category")).toHaveValue(marker);
  await expect(page.getByRole("link", { name: "Read or edit question", exact: true })).toHaveCount(1);
  await expect(page.getByRole("link", { name: "Next questions", exact: true })).toHaveCount(0);
  await page.goto(`/author/questions/${first.questionId}`);
  while (await page.getByLabel("Destination bank").locator("option", { hasText: targetName }).count() === 0) {
    await page.getByRole("button", { name: "Next destination banks", exact: true }).click();
  }
  await page.getByLabel("Destination bank").selectOption({ label: targetName });
  await page.getByRole("button", { name: "Move question", exact: true }).click();
  await expect(page.getByRole("link", { name: "Back to bank", exact: true })).toHaveAttribute("href", target);
  const moved: S["QuestionVersion"] = await (await api(token, `/questions/${first.questionId}`)).json();
  expect(moved.versionId).toBe(first.versionId);
  await page.getByLabel("I understand history is retained when archiving").check();
  await page.getByRole("button", { name: "Archive question", exact: true }).click();
  await expect(page.getByText("This question is archived and read-only.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save new revision" })).toHaveCount(0);
  await api(token, `/questions/${first.questionId}/versions/${first.versionId}`);
  const search = await api(token, `/questions?text=${marker}`);
  const results: S["Page_QuestionSummary_"] = await search.json();
  expect(results.items.map((item) => item.questionId)).toEqual([second.questionId]);
  await page.goto(source);
  await page.getByLabel("I understand history is retained when archiving").check();
  await page.getByRole("button", { name: "Archive bank", exact: true }).click();
  await expect(page.getByText("This bank is archived and read-only.", { exact: true })).toBeVisible();
  const hidden: S["Page_QuestionSummary_"] = await (await api(token, `/questions?text=${marker}`)).json();
  expect(hidden.items).toEqual([]);
  await page.goto("/author");
  await page.getByRole("link", { name: "Include archived banks", exact: true }).click();
  // Direct archived route remains available even when history spans multiple bank pages.
  await page.goto(source);
  await expect(page.getByText("This bank is archived and read-only.", { exact: true })).toBeVisible();
});

async function compose(page: Page, title: string, bankId: string, prompt: string) {
  await page.goto("/author/quizzes");
  await page.getByLabel("Quiz title", { exact: true }).fill(title);
  await page.getByLabel("Selection bank ID").fill(bankId);
  await page.getByLabel("Selection search text").fill(prompt);
  await page.getByRole("button", { name: "Search available questions", exact: true }).click();
  await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).click();
  await page.getByRole("button", { name: "Create quiz", exact: true }).click();
  await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  const path = new URL(page.url()).pathname;
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft", exact: true }).click();
  await expect(page.getByRole("link", { name: "View published version", exact: true })).toBeVisible();
  return path;
}

test("C03 AT-04/05 explicit version update history close and archive preserve real attempts", async ({ page, apps }) => {
  test.setTimeout(180_000);
  await login(page, "combined");
  const token = (await apps.session(page)).access_token;
  const marker = "C03 lifecycle " + randomUUID();
  const bankPath = await bank(page, marker);
  const selection = await question(page, bankPath, marker, "C03 lifecycle");
  apps.assessmentContent.add(marker);
  const path = await compose(page, marker, bankPath.split("/").at(-1)!, marker);
  const quizId = path.split("/").at(-1)!;
  const quiz: S["Quiz"] = await (await api(token, `/quizzes/${quizId}`)).json();
  const firstPath = `/quizzes/${quizId}/versions/${quiz.publishedVersionId}`;
  const first: S["PublishedQuiz"] = await (await api(token, firstPath)).json();
  const otherPath = await compose(page, "C03 reuse " + randomUUID(), bankPath.split("/").at(-1)!, marker);
  const other: S["Quiz"] = await (await api(token, "/quizzes/" + otherPath.split("/").at(-1)!)).json();
  const otherVersion: S["PublishedQuiz"] = await (await api(token,
    `/quizzes/${other.id}/versions/${other.publishedVersionId}`)).json();
  expect(otherVersion.questions[0]!.question.versionId).toBe(selection.versionId);
  const assignment: S["Assignment"] = await (await api(token, "/assignments", "POST", {
    quizId, versionId: quiz.publishedVersionId, learnerId: accounts.combined!.id,
  }, 201)).json();
  const started = await fetch(`${apiOrigin}/api/v1/assignments/${assignment.id}/attempts`, {
    method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json",
      "Idempotency-Key": randomUUID() }, body: "{}",
  });
  expect(started.status).toBe(201);
  const attempt: S["Attempt"] = await started.json();
  const before = await apps.apiDb.query("SELECT row_to_json(t) AS row FROM quezo.attempt_questions t WHERE attempt_id = $1", [attempt.id]);
  await page.goto(`/author/questions/${selection.questionId}`);
  await page.getByLabel("Prompt", { exact: true }).fill("C03 revised " + marker);
  await page.getByLabel("Default points").fill("100");
  await page.getByLabel("Correct option 2", { exact: true }).check();
  await page.getByLabel("Explanatory feedback").fill("C03 changed private feedback");
  apps.assessmentContent.add("C03 changed private feedback");
  await page.getByRole("button", { name: "Save new revision", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 2" })).toBeVisible();
  await page.goto(path);
  await page.getByRole("button", { name: "Create new revision draft", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Edit draft revision 2" })).toBeVisible();
  await expect(page.getByText(selection.versionId, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Use latest revision for question 1", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "explicitly selected revision 2" })).toBeVisible();
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Edit draft revision 3" })).toBeVisible();
  await page.getByRole("link", { name: "Preview saved draft", exact: true }).click();
  await expect(page.getByText("C03 revised " + marker, { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Back to quiz", exact: true }).click();
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft", exact: true }).click();
  await expect(page.getByRole("link", { name: "Publication from draft revision 3", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Publication from draft revision 1", exact: true })).toBeVisible();
  expect(await (await api(token, firstPath)).json()).toEqual(first);
  expect(await (await api(token, `/attempts/${attempt.id}`)).json()).toEqual(attempt);
  await page.getByLabel("I confirm this lifecycle change and retained history").check();
  await page.getByRole("button", { name: "Close quiz", exact: true }).click();
  await expect(page.getByText("State: closed.", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save draft", exact: true })).toHaveCount(0);
  await page.getByLabel("I confirm this lifecycle change and retained history").check();
  await page.getByRole("button", { name: "Archive quiz", exact: true }).click();
  await expect(page.locator("main").getByRole("alert")).toBeVisible();
  await api(token, `/attempts/${attempt.id}/submission`, "POST", {});
  const { serverTime: beforeTime, ...result }: S["LearnerResult"] = await (await api(token, `/attempts/${attempt.id}/result`)).json();
  expect(beforeTime).toBeTruthy();
  await page.getByRole("button", { name: "Archive quiz", exact: true }).click();
  await expect(page.getByText("This quiz is archived and read-only.", { exact: false })).toBeVisible();
  await page.goto(`/author/questions/${selection.questionId}`);
  await page.getByLabel("I understand history is retained when archiving").check();
  await page.getByRole("button", { name: "Archive question", exact: true }).click();
  await expect(page.getByText("This question is archived and read-only.", { exact: true })).toBeVisible();
  expect(await (await api(token, firstPath)).json()).toEqual(first);
  expect(await (await api(token, `/quizzes/${other.id}/versions/${other.publishedVersionId}`)).json()).toEqual(otherVersion);
  const { serverTime: afterTime, ...afterResult }: S["LearnerResult"] = await (await api(token, `/attempts/${attempt.id}/result`)).json();
  expect(afterTime).toBeTruthy();
  expect(afterResult).toEqual(result);
  expect((await apps.apiDb.query("SELECT row_to_json(t) AS row FROM quezo.attempt_questions t WHERE attempt_id = $1", [attempt.id])).rows).toEqual(before.rows);
  await api(token, "/quizzes", "POST", { title: "Cannot reuse archived", questions: [selection] }, 409);
});

test("C03 real foreign author cannot discover search history or mutate nested organization", async ({ page, apps, browser }) => {
  test.setTimeout(120_000);
  await login(page, "author");
  const token = (await apps.session(page)).access_token;
  const marker = "C03 private " + randomUUID();
  const bankPath = await bank(page, marker);
  const selection = await question(page, bankPath, marker, marker);
  const quiz: S["Quiz"] = await (await api(token, "/quizzes", "POST", { title: marker, questions: [selection] }, 201)).json();
  const context = await browser.newContext({ baseURL: webOrigin });
  try {
    const other = await context.newPage();
    await login(other, "combined");
    const foreign = (await apps.session(other)).access_token;
    for (const path of [`/questions?text=${encodeURIComponent(marker)}`, `/questions?category=${encodeURIComponent(marker)}`,
      "/questions?tag=C03-exact", "/question-banks?includeArchived=true", "/quizzes?includeArchived=true"]) {
      const payload = await (await api(foreign, path)).text();
      expect(payload.includes(marker) || payload.includes(selection.questionId), "No foreign search disclosure").toBe(false);
    }
    await api(foreign, `/questions/${selection.questionId}/organization`, "GET", undefined, 404);
    await api(foreign, `/questions/${selection.questionId}/archive`, "POST", undefined, 404);
    await api(foreign, `/question-banks/${bankPath.split("/").at(-1)}/archive`, "POST", undefined, 404);
    await api(foreign, `/quizzes/${quiz.id}/versions`, "GET", undefined, 404);
    await api(foreign, `/quizzes/${quiz.id}/close`, "POST", { expectedRevision: 1 }, 404);
    await api(foreign, `/quizzes/${quiz.id}/archive`, "POST", { expectedRevision: 1 }, 404);
    await api(foreign, `/questions/${selection.questionId}/move`, "POST", {
      bankId: bankPath.split("/").at(-1), expectedRevision: 1,
    }, 404);
    for (const path of [`/author/questions/${selection.questionId}`, `/author/quizzes/${quiz.id}`, bankPath]) {
      const response = await other.goto(path);
      await expect(other.locator("main").getByRole("alert")).toBeVisible();
      expect((await response!.text()).includes(marker), "No foreign HTML/RSC disclosure").toBe(false);
    }
  } finally { await context.close(); }
});
