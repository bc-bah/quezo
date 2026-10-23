import { randomUUID } from "node:crypto";
import { test, expect, login, accounts, apiOrigin } from "./fixtures";
import { createApiClient } from "../../frontend/quezo/src/lib/api/client";

test("D03 AT-09/11 controlled overdue backend fixture catches up on restart and renders expired without timed UX", async ({ page, apps }) => {
  await login(page, "author");
  const token = (await apps.session(page)).access_token;
  const client = createApiClient(apiOrigin, async (input, init) => {
    const request = new Request(input, init);
    request.headers.set("Authorization", `Bearer ${token}`);
    return fetch(request);
  });
  const bank = await client.POST("/api/v1/question-banks", { body: { name: "D03 expiry " + randomUUID() } });
  expect(bank.response.status).toBe(201);
  const options = [{ id: randomUUID(), text: "True" }, { id: randomUUID(), text: "False" }];
  const feedback = "D03 withheld feedback " + randomUUID();
  apps.assessmentContent.add(feedback);
  const question = await client.POST("/api/v1/questions", { body: {
    bankId: bank.data!.id, questionType: "true_false", prompt: "Controlled expiry fixture",
    options, correctOptionId: options[0]!.id, defaultPoints: 3, feedback,
  } });
  expect(question.response.status).toBe(201);
  const quiz = await client.POST("/api/v1/quizzes", { body: {
    title: "D03 expired fixture", questions: [{
      questionId: question.data!.questionId, versionId: question.data!.versionId,
    }], policy: { durationSeconds: 60 },
  } });
  expect(quiz.response.status).toBe(201);
  const publication = await client.POST("/api/v1/quizzes/{quiz_id}/publish", {
    params: { path: { quiz_id: quiz.data!.id }, header: { "idempotency-key": randomUUID() } },
    body: { expectedRevision: 1 },
  });
  expect(publication.response.status).toBe(201);
  const assignment = await client.POST("/api/v1/assignments", { body: {
    quizId: quiz.data!.id, versionId: publication.data!.versionId, learnerId: accounts.learner!.id,
  } });
  expect(assignment.response.status).toBe(201);
  await apps.stopApi();
  const id = randomUUID();
  const connection = await apps.apiDb.connect();
  try {
    await connection.query("BEGIN");
    // Fixture-only historical admission: never mutate a frozen runtime deadline.
    await connection.query(`
      INSERT INTO quezo.attempts (id, assignment_id, learner_id, version_id, attempt_number,
        title, instructions, policy, started_at, deadline, possible_points)
      SELECT $1, a.id, a.learner_id, v.id, 1, v.title, v.instructions, v.policy,
        statement_timestamp() - interval '120 seconds', statement_timestamp() - interval '60 seconds', v.possible_points
      FROM quezo.assignments a JOIN quezo.quiz_versions v ON v.id=a.version_id WHERE a.id=$2
    `, [id, assignment.data!.id]);
    await connection.query(`
      INSERT INTO quezo.attempt_questions (id, attempt_id, version_id, question_id, question_version_id,
        position, question, options, effective_points)
      SELECT gen_random_uuid(), $1, quiz_version_id, question_id, question_version_id,
        position, question, question->'options', effective_points FROM quezo.quiz_questions WHERE quiz_version_id=$2
    `, [id, publication.data!.versionId]);
    await connection.query(`
      INSERT INTO quezo.attempt_start_commands (actor_id, assignment_id, operation, request_id, fingerprint, attempt_id)
      VALUES ($1,$2,'start',$3,$4,$5)
    `, [accounts.learner!.id, assignment.data!.id, randomUUID(), "a".repeat(64), id]);
    await connection.query("COMMIT");
  } finally { await connection.query("ROLLBACK"); connection.release(); }
  await apps.startApi();
  expect((await apps.apiDb.query("SELECT earned_points, possible_points FROM quezo.grades WHERE attempt_id=$1", [id])).rows)
    .toEqual([{ earned_points: 0, possible_points: 3 }]);
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.context().clearCookies();
  await login(page, "learner");
  await page.goto("/learner/attempts/" + id);
  await expect(page.getByRole("heading", { name: "Attempt expired", exact: true })).toBeVisible();
  await expect(page.getByRole("radio").first()).toBeDisabled();
  expect(await page.getByRole("button", { name: "Submit attempt", exact: true }).count()).toBe(0);
  const html = await page.content();
  expect([feedback, "earnedPoints", "correctOptionId", '"outcome"'].some((field) => html.includes(field)),
    "Expired HTML/RSC does not disclose grade/key/feedback").toBe(false);
  expect(await page.getByRole("timer").count()).toBe(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Attempt expired", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "View result", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Attempt expired", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Score", exact: true })).toContainText("0 / 3 points (0.0%)");
  await expect(page.getByRole("region", { name: "Answer key", exact: true })).toContainText("withheld");
  const resultHtml = await page.content();
  expect([feedback, "correctOption", '"outcome"'].some((field) => resultHtml.includes(field)),
    "Expired result releases only its permitted aggregate").toBe(false);
});
