import { randomUUID } from "node:crypto";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, accounts, apiOrigin, webOrigin } from "./fixtures";

type S = components["schemas"];

test("D01 AT-06 author assigns and learner lists starts reloads without private payloads", async ({ page, apps, browser }) => {
  test.setTimeout(150_000);
  await login(page, "author");
  await page.getByRole("link", { name: "Manage question banks" }).click();
  await page.getByLabel("Bank name").fill("D01 bank " + randomUUID());
  await page.getByRole("button", { name: "Create bank", exact: true }).click();
  await page.getByRole("link", { name: "Create question", exact: true }).click();
  const prompt = "D01 private until start " + randomUUID();
  const feedback = "D01 scoring-only sentinel " + randomUUID();
  apps.assessmentContent.add(prompt); apps.assessmentContent.add(feedback);
  await page.getByLabel("Question type").selectOption("mcq");
  await page.getByLabel("Prompt", { exact: true }).fill(prompt);
  await page.getByLabel("Default points").fill("7");
  await page.getByLabel("Explanatory feedback").fill(feedback);
  await page.getByLabel("Option 1", { exact: true }).fill("D01 first choice");
  await page.getByLabel("Option 2", { exact: true }).fill("D01 second choice");
  await page.getByLabel("Correct option 2", { exact: true }).check();
  await page.getByRole("button", { name: "Create question", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
  await page.goto("/author/quizzes");
  const title = "D01 quiz " + randomUUID();
  await page.getByLabel("Quiz title").fill(title);
  while (await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).count() === 0) {
    await page.getByRole("button", { name: "Next available questions" }).click();
  }
  await page.getByRole("button", { name: `Add revision 1 of ${prompt}`, exact: true }).click();
  await page.getByRole("button", { name: "Create quiz", exact: true }).click();
  await page.getByLabel("I confirm publication of this saved draft").check();
  await page.getByRole("button", { name: "Publish saved draft" }).click();
  await page.getByRole("link", { name: "View published version" }).click();
  const publicationPath = new URL(page.url()).pathname;
  const authorToken = (await apps.session(page)).access_token;
  const countBefore = await apps.apiDb.query("SELECT count(*)::int AS n FROM quezo.assignments");
  await page.reload();
  expect((await apps.apiDb.query("SELECT count(*)::int AS n FROM quezo.assignments")).rows).toEqual(countBefore.rows);
  await page.getByLabel("Active learner").selectOption(accounts.learner!.id);
  await page.getByRole("button", { name: "Assign learner", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Assignment confirmed");
  const confirmation = await page.getByRole("status").textContent();
  await page.getByRole("button", { name: "Assign learner", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(confirmation!);
  const context = await browser.newContext({ baseURL: webOrigin });
  const learner = await context.newPage();
  try {
    await login(learner, "learner");
    const token = (await apps.session(learner)).access_token;
    await learner.getByRole("link", { name: "My assignments", exact: true }).click();
    const prestart = await learner.content();
    expect([prompt, feedback, "correctOptionId", "defaultPoints"].some((value) => prestart.includes(value)),
      "Pre-start HTML/RSC omits questions and private scoring").toBe(false);
    const listing = await fetch(apiOrigin + "/api/v1/assignments", { headers: { Authorization: `Bearer ${token}` } });
    const assignments: S["Page_Assignment_"] = await listing.json();
    const assignment = assignments.items.find((item) => item.title === title)!;
    expect(assignment.state).toBe("available");
    const card = learner.getByRole("region", { name: title, exact: true });
    await card.getByRole("button", { name: "Start attempt", exact: true }).click();
    await expect(learner).toHaveURL(/\/learner\/attempts\/[0-9a-f-]+$/);
    await expect(learner.getByRole("heading", { name: title, exact: true })).toBeVisible();
    const attemptPath = new URL(learner.url()).pathname;
    const attemptId = attemptPath.split("/").at(-1)!;
    const projection = await fetch(`${apiOrigin}/api/v1/attempts/${attemptId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(projection.status).toBe(200);
    const raw = await projection.text();
    expect([feedback, "correctOptionId", "defaultPoints"].some((value) => raw.includes(value)),
      "Attempt JSON omits scoring definitions").toBe(false);
    const snapshot: S["Attempt"] = JSON.parse(raw);
    expect(snapshot.deadline).toBeNull();
    expect(snapshot.possiblePoints).toBe(7);
    expect(snapshot.questions[0]!.prompt === prompt, "Authorized content is delivered only after start").toBe(true);
    const ids = await learner.locator("[data-option-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-option-id")));
    await learner.reload();
    expect(await learner.locator("[data-option-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-option-id")))).toEqual(ids);
    expect([feedback, "correctOptionId"].some((value) => (raw + prestart).includes(value))).toBe(false);
    expect((await learner.content()).includes(feedback), "Reloaded HTML/RSC omits private feedback").toBe(false);
    await learner.getByRole("link", { name: "My assignments", exact: true }).click();
    await learner.getByRole("region", { name: title, exact: true }).getByRole("button", { name: "Resume attempt" }).click();
    await expect(learner).toHaveURL(webOrigin + attemptPath);
    await page.getByRole("button", { name: "Assign learner", exact: true }).click();
    await expect(page.getByRole("status")).toHaveText(confirmation!);
    const row = await apps.apiDb.query("SELECT count(*)::int AS n FROM quezo.attempts WHERE assignment_id = $1", [assignment.id]);
    expect(row.rows[0].n).toBe(1);
    const command = randomUUID();
    const send = () => fetch(`${apiOrigin}/api/v1/assignments/${assignment.id}/attempts`, {
      method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": command },
      body: "{}",
    });
    expect((await send()).status).toBe(200);
    expect((await (await send()).json()).id).toBe(attemptId);
    expect((await fetch(`${apiOrigin}/api/v1/attempts/${attemptId}`, {
      headers: { Authorization: `Bearer ${authorToken}` },
    })).status).toBe(403);
    const otherContext = await browser.newContext({ baseURL: webOrigin });
    const other = await otherContext.newPage();
    try {
      await login(other, "combined");
      const otherToken = (await apps.session(other)).access_token;
      for (const path of [`/api/v1/assignments/${assignment.id}`, `/api/v1/attempts/${attemptId}`]) {
        expect((await fetch(apiOrigin + path, { headers: { Authorization: `Bearer ${otherToken}` } })).status).toBe(404);
      }
      await other.goto(attemptPath);
      await expect(other.getByRole("alert")).toBeVisible();
      expect((await other.content()).includes(prompt), "Foreign attempt HTML/RSC conceals content").toBe(false);
      await other.goto(publicationPath);
      await expect(other.locator("main").getByRole("alert")).toBeVisible();
    } finally { await otherContext.close(); }
  } finally { await context.close(); }
});
