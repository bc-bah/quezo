import { randomUUID } from "node:crypto";
import type { Page } from "@playwright/test";
import { createApiClient } from "../../frontend/quezo/src/lib/api/client";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, privatePage, privateIdentity, accounts, apiOrigin } from "./fixtures";

type S = components["schemas"];

function authenticatedClient(token: string) {
  return createApiClient(apiOrigin, async (input, init) => {
    const request = new Request(input, init);
    request.headers.set("Authorization", `Bearer ${token}`);
    return fetch(request);
  });
}

function presentation(attempt: S["Attempt"]) {
  return attempt.questions.map(({ response, ...question }) => question);
}

async function compose(page: Page, title: string, prompts: string[], preset: "never" | "after_finalization") {
  await page.goto("/author/quizzes");
  await page.getByLabel("Quiz title").fill(title);
  await page.getByLabel("Release preset").selectOption(preset);
  for (const prompt of prompts) {
    const add = page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true });
    while (await add.count() === 0) {
      await page.getByRole("button", { name: "Next available questions" }).click();
    }
    await add.click();
  }
  await page.getByLabel("Point override for question 1").fill("5");
  await page.getByRole("button", { name: "Create quiz", exact: true }).click();
  await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  return new URL(page.url()).pathname.split("/").at(-1)!;
}

async function publish(page: Page) {
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft" }).click();
  await page.getByRole("link", { name: "View published version" }).click();
  return new URL(page.url()).pathname.split("/").at(-1)!;
}

for (const preset of ["after_finalization", "never"] as const) {
  const name = preset === "never" ? "fully withheld" : "score-only";
  test(`T01 AT-03 through AT-12 ${name} author-to-result lifecycle preserves frozen history and live access`, async ({ page, apps, browser }) => {
    test.setTimeout(180_000);
    await login(page, "author");
    const author = authenticatedClient((await apps.session(page)).access_token);
    await page.getByRole("link", { name: "Manage question banks" }).click();
    await page.getByLabel("Bank name").fill("T01 bank " + randomUUID());
    await page.getByRole("button", { name: "Create bank", exact: true }).click();
    await expect(page.getByRole("link", { name: "Create question", exact: true })).toBeVisible();
    const bank = page.url();
    const feedback = "T01 private explanation " + randomUUID();
    apps.assessmentContent.add(feedback);
    const originals: S["QuestionVersion"][] = [];
    for (const kind of ["mcq", "true_false"] as const) {
      await page.goto(bank);
      await page.getByRole("link", { name: "Create question", exact: true }).click();
      const prompt = "T01 " + kind + " " + randomUUID();
      apps.assessmentContent.add(prompt);
      await page.getByLabel("Question type").selectOption(kind);
      await page.getByLabel("Prompt", { exact: true }).fill(prompt);
      await page.getByLabel("Default points").fill("2");
      await page.getByLabel("Explanatory feedback").fill(feedback);
      if (kind === "mcq") {
        await page.getByLabel("Option 1", { exact: true }).fill("T01 first");
        await page.getByLabel("Option 2", { exact: true }).fill("T01 second");
      }
      await page.getByLabel("Correct option 1", { exact: true }).check();
      await page.getByRole("button", { name: "Create question", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
      const parts = new URL(page.url()).pathname.split("/");
      const result = await author.GET("/api/v1/questions/{question_id}/versions/{version_id}", {
        params: { path: { question_id: parts[3]!, version_id: parts[5]! } },
      });
      expect(result.response.status).toBe(200);
      originals.push(result.data!);
    }
    const prompts = originals.map((question) => question.prompt);
    const title = "T01 " + name + " " + randomUUID();
    const quizId = await compose(page, title, prompts, preset);
    const counts = () => apps.apiDb.query(`
      SELECT (SELECT count(*)::int FROM quezo.assignments) AS assignments,
        (SELECT count(*)::int FROM quezo.attempts) AS attempts,
        (SELECT count(*)::int FROM quezo.grades) AS grades,
        (SELECT count(*)::int FROM quezo.attempt_start_commands) AS starts,
        (SELECT count(*)::int FROM quezo.quiz_publication_events) AS publications,
        (SELECT count(*)::int FROM quezo.attempt_completion_events) AS completions
    `);
    const beforePreview = (await counts()).rows;
    await page.getByRole("link", { name: "Preview saved draft" }).click();
    await expect(page.getByRole("heading", { name: "Preview: " + title, exact: true })).toBeVisible();
    await page.getByLabel("True", { exact: true }).check();
    const preview = await page.content();
    expect([feedback, "correctOptionId"].some((value) => preview.includes(value)), "Learner-shaped preview").toBe(false);
    expect((await counts()).rows).toEqual(beforePreview);
    await page.getByRole("link", { name: "Back to quiz" }).click();
    const versionId = await publish(page);
    const publishedPath = new URL(page.url()).pathname;
    const publication = await author.GET("/api/v1/quizzes/{quiz_id}/versions/{version_id}", {
      params: { path: { quiz_id: quizId, version_id: versionId } },
    });
    expect(publication.response.status).toBe(200);
    expect(publication.data!.possiblePoints).toBe(7);
    const secondQuiz = await compose(page, "T01 reused " + randomUUID(), [prompts[0]!], preset);
    const secondVersion = await publish(page);
    const reused = await author.GET("/api/v1/quizzes/{quiz_id}/versions/{version_id}", {
      params: { path: { quiz_id: secondQuiz, version_id: secondVersion } },
    });
    expect(reused.response.status).toBe(200);
    expect(reused.data!.questions[0]!.question).toEqual(publication.data!.questions[0]!.question);
    await page.goto(publishedPath);
    await page.getByLabel("Active learner").selectOption(accounts.learner!.id);
    await page.getByRole("button", { name: "Assign learner", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Assignment confirmed");

    // Separate contexts retain real provider SSO without changing identity in-place.
    const context = await privateIdentity(browser, apps);
    const learner = context.page;
    try {
      await login(learner, "learner");
      const token = (await apps.session(learner)).access_token;
      const client = authenticatedClient(token);
      await learner.getByRole("link", { name: "My assignments", exact: true }).click();
      await learner.getByRole("region", { name: title, exact: true }).getByRole("button", { name: "Start attempt", exact: true }).click();
      await expect(learner).toHaveURL(/\/learner\/attempts\/[0-9a-f-]+$/);
      const attemptUrl = learner.url();
      const attemptId = new URL(attemptUrl).pathname.split("/").at(-1)!;
      const params = { path: { attempt_id: attemptId } };
      const snapshot = async () => {
        const response = await client.GET("/api/v1/attempts/{attempt_id}", { params });
        expect(response.response.status).toBe(200);
        expect([feedback, "correctOptionId", "defaultPoints"].some((value) => JSON.stringify(response.data).includes(value)),
          "Attempt projection omits private scoring data").toBe(false);
        return response.data!;
      };
      const initial = await snapshot();
      expect(initial.deadline).toBeNull();
      expect(initial.questions.map((question) => question.prompt)).toEqual(prompts);
      const first = learner.locator("[data-question-id]").first();
      const second = learner.locator("[data-question-id]").nth(1);
      const held = await apps.apiDb.connect();
      try {
        await held.query("BEGIN");
        await held.query("SELECT id FROM quezo.attempts WHERE id=$1 FOR UPDATE", [attemptId]);
        await first.getByLabel("T01 first", { exact: true }).check();
        await first.getByRole("button", { name: "Save answer", exact: true }).click();
        await expect(first.getByRole("status")).toHaveText("Saving");
        await expect(learner.getByText("Waiting for pending saves before submission.")).toBeVisible();
        await expect(learner.getByRole("button", { name: "Submit attempt", exact: true })).toBeDisabled();
        await held.query("COMMIT");
      } finally { await held.query("ROLLBACK"); held.release(); }
      await expect(first.getByRole("status")).toHaveText("Saved");
      await learner.getByRole("navigation", { name: "Questions" }).getByRole("link", { name: "Question 2" }).click();
      await second.getByLabel("False", { exact: true }).check();
      await second.getByRole("button", { name: "Save answer", exact: true }).click();
      await expect(second.getByRole("status")).toHaveText("Saved");
      const saved = await snapshot();
      expect(saved.questions.map((question) => question.response.revision)).toEqual([1, 1]);

      for (const original of originals) {
        await page.goto(`/author/questions/${original.questionId}`);
        await page.getByLabel("Prompt", { exact: true }).fill("Revised " + original.prompt);
        await page.getByLabel("Default points").fill("9");
        await page.getByLabel("Correct option 2", { exact: true }).check();
        await page.getByRole("button", { name: "Save new revision" }).click();
        await expect(page.getByRole("heading", { name: "Selected question revision 2" })).toBeVisible();
        const old = await author.GET("/api/v1/questions/{question_id}/versions/{version_id}", {
          params: { path: { question_id: original.questionId, version_id: original.versionId } },
        });
        expect(old.response.status).toBe(200);
        expect(old.data).toEqual(original);
      }
      await learner.reload();
      await expect(first.getByLabel("T01 first", { exact: true })).toBeChecked();
      await expect(second.getByLabel("False", { exact: true })).toBeChecked();
      expect(presentation(await snapshot())).toEqual(presentation(initial));
      await learner.getByRole("link", { name: "My assignments", exact: true }).click();
      await learner.getByRole("region", { name: title, exact: true }).getByRole("button", { name: "Resume attempt" }).click();
      await expect(learner).toHaveURL(attemptUrl);
      expect((await snapshot()).questions).toEqual(saved.questions);
      learner.once("dialog", (dialog) => dialog.accept());
      await learner.getByRole("button", { name: "Submit attempt", exact: true }).click();
      await expect(learner.getByRole("heading", { name: "Submission confirmed", exact: true })).toBeVisible();
      const completion = (await snapshot()).completion;
      for (let retry = 0; retry < 2; retry++) {
        const response = await client.POST("/api/v1/attempts/{attempt_id}/submission", { params, body: {} });
        expect(response.response.status).toBe(200);
        expect(response.data).toEqual(completion);
        expect(Object.keys(response.data!).sort()).toEqual(["attemptId", "completionReason", "finalizedAt", "state"]);
      }
      const grade = () => apps.apiDb.query(
        "SELECT id, earned_points, possible_points FROM quezo.grades WHERE attempt_id=$1", [attemptId],
      );
      const graded = (await grade()).rows;
      expect(graded).toHaveLength(1);
      expect(graded[0]).toMatchObject({ earned_points: 5, possible_points: 7 });
      await page.goto(`/author/questions/${originals[0]!.questionId}`);
      await page.getByLabel("Default points").fill("10");
      await page.getByRole("button", { name: "Save new revision" }).click();
      await expect(page.getByRole("heading", { name: "Selected question revision 3" })).toBeVisible();
      expect((await author.GET("/api/v1/quizzes/{quiz_id}/versions/{version_id}", {
        params: { path: { quiz_id: quizId, version_id: versionId } },
      })).data).toEqual(publication.data);
      expect((await author.GET("/api/v1/quizzes/{quiz_id}/versions/{version_id}", {
        params: { path: { quiz_id: secondQuiz, version_id: secondVersion } },
      })).data).toEqual(reused.data);
      expect((await grade()).rows).toEqual(graded);
      expect(presentation(await snapshot())).toEqual(presentation(initial));
      expect((await snapshot()).questions).toEqual(saved.questions);

      await learner.getByRole("link", { name: "View result", exact: true }).click();
      const resultUrl = attemptUrl + "/result";
      await expect(learner.getByRole("region", { name: "Score", exact: true })).toContainText(
        preset === "never" ? "Score withheld." : "5 / 7 points (71.4%)",
      );
      const result = await client.GET("/api/v1/attempts/{attempt_id}/result", { params });
      expect(result.response.status).toBe(200);
      expect(result.response.headers.get("cache-control")).toBe("private, no-store");
      expect(result.data!.score).toEqual(preset === "never" ? { status: "withheld" } :
        { status: "released", earnedPoints: 5, possiblePoints: 7 });
      expect(result.data!.answerKey).toEqual({ status: "withheld" });
      expect(result.data!.explanations).toEqual({ status: "withheld" });
      const hidden = [feedback, ...prompts, "correctOption", '"outcome"', "feedback",
        ...(preset === "never" ? ["earnedPoints", "possiblePoints"] : [])];
      for (const headers of [{}, { RSC: "1" }]) {
        const response = await learner.request.get(resultUrl, { headers });
        expect(response.ok()).toBe(true);
        expect(response.headers()["cache-control"]).toContain("private");
        expect(response.headers()["cache-control"]).toContain("no-store");
        const serialized = await response.text() + JSON.stringify(result.data) + await learner.content();
        expect(hidden.some((field) => serialized.includes(field)), "HTTP/HTML/RSC/DOM omit unreleased fields").toBe(false);
      }
      expect(await learner.evaluate(async () => (await caches.keys()).length)).toBe(0);
      await privatePage(learner, apps);
      try {
        await apps.apiDb.query("DELETE FROM quezo.account_roles WHERE account_id=$1 AND role='learner'", [accounts.learner!.id]);
        expect((await client.GET("/api/v1/attempts/{attempt_id}/result", { params })).response.status).toBe(403);
        expect((await client.POST("/api/v1/attempts/{attempt_id}/submission", { params, body: {} })).response.status).toBe(403);
        await learner.reload();
        await expect(learner.getByRole("heading", { name: "Result unavailable", exact: true })).toBeVisible();
        expect((await learner.content()).includes(title), "Revoked identity cannot read cached result").toBe(false);
      } finally {
        await apps.apiDb.query("INSERT INTO quezo.account_roles(account_id,role) VALUES ($1,'learner')", [accounts.learner!.id]);
      }
      await learner.reload();
      await expect(learner.getByRole("heading", { name: "Result: " + title, exact: true })).toBeVisible();

      const foreignContext = await privateIdentity(browser, apps);
      const foreign = foreignContext.page;
      try {
        await login(foreign, "combined");
        const outsider = authenticatedClient((await apps.session(foreign)).access_token);
        expect((await outsider.GET("/api/v1/quizzes/{quiz_id}/versions/{version_id}", {
          params: { path: { quiz_id: quizId, version_id: versionId } },
        })).response.status).toBe(404);
        expect((await outsider.GET("/api/v1/attempts/{attempt_id}", { params })).response.status).toBe(404);
        expect((await outsider.GET("/api/v1/attempts/{attempt_id}/result", { params })).response.status).toBe(404);
        expect((await outsider.POST("/api/v1/attempts/{attempt_id}/submission", { params, body: {} })).response.status).toBe(404);
        for (const url of [publishedPath, attemptUrl, resultUrl]) {
          await foreign.goto(url);
          await expect(foreign.getByRole("main").getByRole("alert")).toBeVisible();
          const html = await foreign.content();
          expect([title, feedback, ...prompts].some((value) => html.includes(value)), "Foreign HTML/RSC conceals content").toBe(false);
        }
        await privatePage(foreign, apps);
      } finally { await foreignContext.close(); }
      expect((await grade()).rows).toEqual(graded);
    } finally { await context.close(); }
  });
}
