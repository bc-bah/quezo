import { randomUUID } from "node:crypto";
import { createApiClient } from "../../frontend/quezo/src/lib/api/client";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, accounts, apiOrigin, privateIdentity } from "./fixtures";

type S = components["schemas"];

function client(token: string) {
  return createApiClient(apiOrigin, async (input, init) => {
    const request = new Request(input, init);
    request.headers.set("Authorization", `Bearer ${token}`);
    return fetch(request);
  });
}

async function data<T>(operation: Promise<{ data?: T; response: Response }>): Promise<T> {
  const result = await operation;
  expect(result.response.ok, "Authorized reporting fixture operation").toBe(true);
  if (result.data === undefined) throw new Error("Reporting fixture data missing");
  return result.data;
}

for (const release of ["after_finalization", "never"] as const) {
  test(`R02 AT-12/13 ${release} history and reporting agree with immutable Grades and deny guessed IDs`, async ({ page, apps, browser }) => {
    test.setTimeout(180_000);
    await login(page, "combined");
    const api = client((await apps.session(page)).access_token);
    const title = "R02 " + randomUUID();
    const feedback = "R02 protected explanation " + randomUUID();
    apps.assessmentContent.add(feedback);
    const bank = await data(api.POST("/api/v1/question-banks", { body: { name: title } }));
    const selections: { questionId: string; versionId: string }[] = [];
    for (const kind of ["mcq", "true_false"] as const) {
      const options = kind === "mcq"
        ? Array.from({ length: 10 }, (_, index) => ({ id: randomUUID(), text: `R02 option ${index + 1}` }))
        : [{ id: randomUUID(), text: "True" }, { id: randomUUID(), text: "False" }];
      const question = await data(api.POST("/api/v1/questions", { body: {
        bankId: bank.id, questionType: kind, prompt: title + " " + kind,
        options, correctOptionId: options[0]!.id, defaultPoints: kind === "mcq" ? 7 : 3, feedback,
      } }));
      selections.push({ questionId: question.questionId, versionId: question.versionId });
    }
    const quiz = await data(api.POST("/api/v1/quizzes", { body: {
      title, instructions: "R02 instructions", questions: selections,
      policy: { attemptLimit: null, scoreRelease: release, answerKeyRelease: release, explanationRelease: release },
    } }));
    const publication = await data(api.POST("/api/v1/quizzes/{quiz_id}/publish", {
      params: { path: { quiz_id: quiz.id }, header: { "idempotency-key": randomUUID() } },
      body: { expectedRevision: 1 },
    }));
    const assignment = await data(api.POST("/api/v1/assignments", { body: {
      quizId: quiz.id, versionId: publication.versionId, learnerId: accounts.combined!.id,
    } }));
    await data(api.POST("/api/v1/assignments", { body: {
      quizId: quiz.id, versionId: publication.versionId, learnerId: accounts.learner!.id,
    } }));
    const started: S["Attempt"][] = [];
    for (let index = 0; index < 3; index++) {
      const attempt = await data(api.POST("/api/v1/assignments/{assignment_id}/attempts", {
        params: { path: { assignment_id: assignment.id }, header: { "idempotency-key": randomUUID() } },
        body: { timingChoice: "off" },
      }));
      started.push(attempt);
      if (index === 2) continue;
      const question = attempt.questions[0]!;
      await data(api.PUT("/api/v1/attempts/{attempt_id}/responses/{question_id}", {
        params: { path: { attempt_id: attempt.id, question_id: question.attemptQuestionId } },
        body: { requestId: randomUUID(), expectedRevision: 0, selectedOptionId: question.options[index === 0 ? 1 : 0]!.id },
      }));
      await data(api.POST("/api/v1/attempts/{attempt_id}/submission", {
        params: { path: { attempt_id: attempt.id } }, body: {},
      }));
    }
    await data(api.POST("/api/v1/quizzes/{quiz_id}/drafts", {
      params: { path: { quiz_id: quiz.id } }, body: { expectedRevision: 1 },
    }));
    await data(api.PATCH("/api/v1/quizzes/{quiz_id}", {
      params: { path: { quiz_id: quiz.id } }, body: {
        expectedRevision: 2, title: title + " second", instructions: "", questions: selections,
        policy: { scoreRelease: "never", answerKeyRelease: "never", explanationRelease: "never" },
      },
    }));
    const secondPublication = await data(api.POST("/api/v1/quizzes/{quiz_id}/publish", {
      params: { path: { quiz_id: quiz.id }, header: { "idempotency-key": randomUUID() } },
      body: { expectedRevision: 3 },
    }));
    const secondAssignment = await data(api.POST("/api/v1/assignments", { body: {
      quizId: quiz.id, versionId: secondPublication.versionId, learnerId: accounts.combined!.id,
    } }));
    const fourth = await data(api.POST("/api/v1/assignments/{assignment_id}/attempts", {
      params: { path: { assignment_id: secondAssignment.id }, header: { "idempotency-key": randomUUID() } },
      body: {},
    }));
    await data(api.POST("/api/v1/attempts/{attempt_id}/submission", {
      params: { path: { attempt_id: fourth.id } }, body: {},
    }));
    const reportPath = `/author/quizzes/${quiz.id}/results`;
    await page.goto(`/author/quizzes/${quiz.id}`);
    await page.getByRole("link", { name: "Participation and results", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Report: " + title + " second", exact: true })).toBeVisible();
    const summary = page.getByRole("region", { name: "Summary", exact: true });
    await expect(summary).toContainText("Participation: 1 / 2");
    await expect(summary).toContainText("Completion: 1 / 2");
    await expect(summary).toContainText("finalized: 3; submitted: 3; expired: 0");
    await expect(summary).toContainText(release === "never" ? "No released finalized scores." : "Mean: 35.0%");
    const historyApi = await data(api.GET("/api/v1/me/attempts"));
    const reportApi = await data(api.GET("/api/v1/quizzes/{quiz_id}/results", {
      params: { path: { quiz_id: quiz.id } },
    }));
    expect(reportApi.summary.releasedScoreAttempts).toBe(release === "never" ? 0 : 2);
    expect(reportApi.summary.withheldScoreAttempts).toBe(release === "never" ? 3 : 1);
    const persisted = await apps.apiDb.query(
      "SELECT count(*)::int AS grades, sum(g.earned_points)::int AS earned FROM quezo.grades g "
      + "JOIN quezo.attempts t ON t.id=g.attempt_id JOIN quezo.assignments a ON a.id=t.assignment_id WHERE a.quiz_id=$1",
      [quiz.id],
    );
    expect(persisted.rows).toEqual([{ grades: 3, earned: 7 }]);
    const first = started[0]!;
    await page.getByRole("article", { name: `Attempt 1: ${first.id}`, exact: true })
      .getByRole("link", { name: "Inspect finalized attempt", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Submission: " + title, exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Saved responses", exact: true })).toContainText("Unanswered.");
    await expect(page.getByRole("region", { name: "Saved responses", exact: true })).toContainText("R02 option 2");
    if (release === "after_finalization") {
      await expect(page.getByRole("region", { name: "Answer key", exact: true })).toContainText("Outcome: incorrect");
      await expect(page.getByRole("region", { name: "Answer key", exact: true })).toContainText("Outcome: unanswered");
    } else {
      await expect(page.getByRole("region", { name: "Answer key", exact: true })).toContainText("withheld");
      expect((await page.content()).includes(feedback), "Withheld feedback absent from submission DOM").toBe(false);
    }
    const detail = await data(api.GET("/api/v1/quizzes/{quiz_id}/results/attempts/{attempt_id}", {
      params: { path: { quiz_id: quiz.id, attempt_id: first.id } },
    }));
    expect(detail.attempt).toEqual(historyApi.items.find((attempt) => attempt.id === first.id));
    const rsc = await page.request.get(page.url(), { headers: { RSC: "1" } });
    expect(rsc.headers()["cache-control"]).toContain("no-store");
    if (release === "never") {
      expect(["earnedPoints", "correctOption", '"outcome"', feedback].some((value) =>
        JSON.stringify(detail).includes(value)), "No protected API fields").toBe(false);
      expect((await rsc.text()).includes(feedback), "No withheld explanation in RSC").toBe(false);
    }
    await page.goto("/learner");
    await page.getByRole("link", { name: "Attempt history", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Attempt history", exact: true })).toBeVisible();
    await expect(page.getByRole("article", { name: `Attempt 1: ${fourth.id}`, exact: true })).toContainText(secondPublication.versionId);
    await expect(page.getByRole("article", { name: `Attempt 3: ${started[2]!.id}`, exact: true })).toContainText("No final score");
    const firstRow = page.getByRole("article", { name: `Attempt 1: ${first.id}`, exact: true });
    await expect(firstRow).toContainText(publication.versionId);
    await firstRow.getByRole("link", { name: "Inspect finalized attempt", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Result: " + title, exact: true })).toBeVisible();
    const result = await data(api.GET("/api/v1/attempts/{attempt_id}/result", {
      params: { path: { attempt_id: first.id } },
    }));
    expect(result.score).toEqual(detail.attempt.score);
    expect(result.answerKey).toEqual(detail.result.answerKey);

    const foreign = await privateIdentity(browser, apps);
    try {
      await login(foreign.page, "author");
      const other = client((await apps.session(foreign.page)).access_token);
      expect((await other.GET("/api/v1/quizzes/{quiz_id}/results", {
        params: { path: { quiz_id: quiz.id } },
      })).response.status).toBe(404);
      expect((await other.GET("/api/v1/quizzes/{quiz_id}/results/attempts/{attempt_id}", {
        params: { path: { quiz_id: quiz.id, attempt_id: first.id } },
      })).response.status).toBe(404);
      await foreign.page.goto(reportPath);
      await expect(foreign.page.getByRole("main").getByRole("alert")).toBeVisible();
      expect((await foreign.page.content()).includes(title), "Foreign report conceals content").toBe(false);
      await foreign.page.goto(reportPath + "/attempts/" + first.id);
      await expect(foreign.page.getByRole("main").getByRole("alert")).toBeVisible();
    } finally { await foreign.close(); }
  });
}

test("R02 AT-13 history pagination and empty/error recovery use real persisted attempts", async ({ page, apps }) => {
  test.setTimeout(180_000);
  await login(page, "learner");
  const api = client((await apps.session(page)).access_token);
  let existing = await data(api.GET("/api/v1/me/attempts", { params: { query: { pageSize: 100 } } }));
  while (existing.nextCursor) {
    existing = await data(api.GET("/api/v1/me/attempts", {
      params: { query: { pageSize: 100, cursor: existing.nextCursor } },
    }));
  }
  const lastExisting = existing.items.at(-1)?.id;
  await page.goto("/learner/history" + (lastExisting ? `?cursor=${lastExisting}` : ""));
  await expect(page.getByText("No attempts on this page.", { exact: true })).toBeVisible();
  await apps.backendTransport.close();
  try {
    await page.reload();
    await expect(page.getByRole("heading", { name: "Attempt history unavailable" })).toBeVisible();
    await expect(page.getByRole("main").getByRole("alert")).toBeVisible();
  } finally { await apps.backendTransport.open(); }
  await page.getByRole("link", { name: "Retry history", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Attempt history", exact: true })).toBeVisible();
  // Use native author login, then the same protected API contracts for repeated attempts.
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.context().clearCookies();
  await login(page, "combined");
  const author = client((await apps.session(page)).access_token);
  const bank = await data(author.POST("/api/v1/question-banks", { body: { name: "R02 pagination" } }));
  const options = [{ id: randomUUID(), text: "True" }, { id: randomUUID(), text: "False" }];
  const question = await data(author.POST("/api/v1/questions", { body: {
    bankId: bank.id, questionType: "true_false", prompt: "R02 pagination question", options,
    correctOptionId: options[0]!.id, defaultPoints: 1, feedback: "",
  } }));
  const quiz = await data(author.POST("/api/v1/quizzes", { body: {
    title: "R02 pagination quiz", instructions: "", questions: [{ questionId: question.questionId, versionId: question.versionId }],
    policy: { attemptLimit: null },
  } }));
  await page.goto(`/author/quizzes/${quiz.id}/results`);
  await expect(page.getByText("No assigned learners on this page.", { exact: true })).toBeVisible();
  await expect(page.getByText("No attempts on this page.", { exact: true })).toBeVisible();
  await apps.backendTransport.close();
  try {
    await page.reload();
    await expect(page.getByRole("main").getByRole("alert")).toBeVisible();
  } finally { await apps.backendTransport.open(); }
  await page.getByRole("link", { name: "Retry report", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Report: R02 pagination quiz", exact: true })).toBeVisible();
  const publication = await data(author.POST("/api/v1/quizzes/{quiz_id}/publish", {
    params: { path: { quiz_id: quiz.id }, header: { "idempotency-key": randomUUID() } }, body: { expectedRevision: 1 },
  }));
  const assignment = await data(author.POST("/api/v1/assignments", { body: {
    quizId: quiz.id, versionId: publication.versionId, learnerId: accounts.learner!.id,
  } }));
  const ids = [];
  for (let index = 0; index < 26; index++) {
    const attempt = await data(api.POST("/api/v1/assignments/{assignment_id}/attempts", {
      params: { path: { assignment_id: assignment.id }, header: { "idempotency-key": randomUUID() } }, body: {},
    }));
    ids.push(attempt.id);
    await data(api.POST("/api/v1/attempts/{attempt_id}/submission", {
      params: { path: { attempt_id: attempt.id } }, body: {},
    }));
  }
  await page.reload();
  await expect(page.getByRole("region", { name: "Attempts", exact: true }).getByRole("article")).toHaveCount(25);
  await page.getByRole("link", { name: "Next attempts", exact: true }).click();
  await expect(page.getByRole("region", { name: "Attempts", exact: true }).getByRole("article")).toHaveCount(1);
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.context().clearCookies();
  await login(page, "learner");
  await page.goto("/learner/history");
  await expect(page.getByRole("article")).toHaveCount(25);
  const rows = await page.getByRole("article").allTextContents();
  while (await page.getByRole("link", { name: "Next attempts", exact: true }).count()) {
    const next = page.getByRole("link", { name: "Next attempts", exact: true });
    const href = await next.getAttribute("href");
    if (!href) throw new Error("History pagination link missing");
    const cursor = new URL(href, page.url()).searchParams.get("cursor");
    const expected = await data(api.GET("/api/v1/me/attempts", { params: { query: { cursor } } }));
    await next.click();
    await expect(page.getByRole("article")).toHaveCount(expected.items.length);
    for (const attempt of expected.items) {
      await expect(page.getByRole("article", { name: `Attempt ${attempt.attemptNumber}: ${attempt.id}`, exact: true })).toBeVisible();
    }
    rows.push(...await page.getByRole("article").allTextContents());
  }
  expect(ids.every((id) => rows.filter((text) => text.includes(id)).length === 1)).toBe(true);
  await expect(page.getByRole("link", { name: "Next attempts", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "First history page", exact: true }).click();
  await expect(page.getByRole("article")).toHaveCount(25);
});
