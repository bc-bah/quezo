import { randomUUID } from "node:crypto";
import { test, expect, login, accounts, apiOrigin, privatePage } from "./fixtures";
import { createApiClient } from "../../frontend/quezo/src/lib/api/client";

for (const scenario of [
  { name: "score-only", preset: "after_finalization", save: true, score: "1 / 3 points (33.3%)" },
  { name: "released zero", preset: "after_finalization", save: false, score: "0 / 3 points (0.0%)" },
  { name: "fully withheld", preset: "never", save: true, score: "Score withheld." },
]) {
  test(`R01 AT-12 ${scenario.name} result omits unreleased data in real HTTP and HTML`, async ({ page, apps }) => {
    test.setTimeout(120_000);
    await login(page, "author");
    await page.getByRole("link", { name: "Manage question banks" }).click();
    await page.getByLabel("Bank name").fill("R01 bank " + randomUUID());
    await page.getByRole("button", { name: "Create bank", exact: true }).click();
    await expect(page.getByRole("link", { name: "Create question", exact: true })).toBeVisible();
    const bank = page.url();
    const feedback = "R01 hidden feedback " + randomUUID();
    const prompts: string[] = [];
    apps.assessmentContent.add(feedback);
    for (const [index, kind] of (["mcq", "true_false"] as const).entries()) {
      await page.goto(bank);
      await page.getByRole("link", { name: "Create question", exact: true }).click();
      const prompt = "R01 " + kind + " " + randomUUID();
      prompts.push(prompt); apps.assessmentContent.add(prompt);
      await page.getByLabel("Question type").selectOption(kind);
      await page.getByLabel("Prompt", { exact: true }).fill(prompt);
      await page.getByLabel("Default points").fill(String(index + 1));
      await page.getByLabel("Explanatory feedback").fill(feedback);
      if (kind === "mcq") {
        await page.getByLabel("Option 1", { exact: true }).fill("R01 first");
        await page.getByLabel("Option 2", { exact: true }).fill("R01 second");
      }
      await page.getByLabel("Correct option 1", { exact: true }).check();
      await page.getByRole("button", { name: "Create question", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Selected question revision 1" })).toBeVisible();
    }
    const title = "R01 quiz " + randomUUID();
    await page.goto("/author/quizzes");
    await page.getByLabel("Quiz title").fill(title);
    await page.getByLabel("Release preset").selectOption(scenario.preset);
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
    await page.context().clearCookies();
    await login(page, "learner");
    await page.getByRole("link", { name: "My assignments", exact: true }).click();
    await page.getByRole("region", { name: title, exact: true }).getByRole("button", { name: "Start attempt", exact: true }).click();
    await expect(page).toHaveURL(/\/learner\/attempts\/[0-9a-f-]+$/);
    const attemptUrl = page.url();
    const attemptId = new URL(attemptUrl).pathname.split("/").at(-1)!;
    const resultUrl = attemptUrl + "/result";
    const token = (await apps.session(page)).access_token;
    const client = createApiClient(apiOrigin, async (input, init) => {
      const request = new Request(input, init);
      request.headers.set("Authorization", `Bearer ${token}`);
      return fetch(request);
    });
    const params = { path: { attempt_id: attemptId } };
    expect((await client.GET("/api/v1/attempts/{attempt_id}/result", { params })).response.status).toBe(409);
    await page.goto(resultUrl);
    await expect(page.getByRole("heading", { name: "Result unavailable", exact: true })).toBeVisible();
    expect((await page.content()).includes(title), "No pre-finalization result content").toBe(false);
    await page.goto(attemptUrl);
    if (scenario.save) {
      const question = page.locator("[data-question-id]").first();
      await question.getByLabel("R01 first", { exact: true }).check();
      await question.getByRole("button", { name: "Save answer", exact: true }).click();
      await expect(question.getByRole("status")).toHaveText("Saved");
    }
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Submit attempt", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Submission confirmed", exact: true })).toBeVisible();
    const acknowledgement = await client.POST("/api/v1/attempts/{attempt_id}/submission", { params, body: {} });
    expect(Object.keys(acknowledgement.data!).sort()).toEqual(["attemptId", "completionReason", "finalizedAt", "state"]);
    const attemptHtml = await page.content();
    expect(["earnedPoints", "correctOption", feedback, '"outcome"'].some((value) => attemptHtml.includes(value)),
      "Completion is metadata only").toBe(false);
    const navigation = page.waitForResponse((response) => response.url() === resultUrl);
    await page.getByRole("link", { name: "View result", exact: true }).click();
    const htmlResponse = await navigation;
    expect(htmlResponse.headers()["cache-control"]).toContain("private");
    expect(htmlResponse.headers()["cache-control"]).toContain("no-store");
    await expect(page.getByRole("heading", { name: "Result: " + title, exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Submission confirmed", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Score", exact: true })).toContainText(scenario.score);
    await expect(page.getByRole("region", { name: "Answer key", exact: true })).toContainText("withheld");
    await expect(page.getByRole("region", { name: "Explanations", exact: true })).toContainText("withheld");
    const response = await fetch(`${apiOrigin}/api/v1/attempts/${attemptId}/result`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    const raw = await response.text();
    const result = await client.GET("/api/v1/attempts/{attempt_id}/result", { params });
    expect(result.data!.answerKey).toEqual({ status: "withheld" });
    expect(result.data!.explanations).toEqual({ status: "withheld" });
    if (scenario.preset === "never") {
      expect(result.data!.score).toEqual({ status: "withheld" });
      expect(["earnedPoints", "possiblePoints"].some((value) => raw.includes(value)), "Withheld is omission, not null or zero").toBe(false);
      expect((await page.getByRole("main").innerText()).includes("0.0%"), "No fabricated zero").toBe(false);
    } else {
      expect(result.data!.score).toEqual({ status: "released", earnedPoints: scenario.save ? 1 : 0, possiblePoints: 3 });
    }
    const protectedValues = ["correctOption", '"outcome"', "feedback", feedback, ...prompts];
    const serialized = raw + await htmlResponse.text() + await page.content();
    expect(protectedValues.some((value) => serialized.includes(value)), "API/HTML/RSC/DOM omit unreleased item data").toBe(false);
    const rsc = await page.request.get(resultUrl, { headers: { RSC: "1" } });
    expect(rsc.headers()["cache-control"]).toContain("no-store");
    const rscText = await rsc.text();
    expect(protectedValues.some((value) => rscText.includes(value)), "RSC has the same omissions").toBe(false);
    await privatePage(page, apps);
    await page.reload();
    await expect(page.getByRole("region", { name: "Score", exact: true })).toContainText(scenario.score);
    expect((await apps.apiDb.query("SELECT earned_points, possible_points FROM quezo.grades WHERE attempt_id=$1", [attemptId])).rows)
      .toEqual([{ earned_points: scenario.save ? 1 : 0, possible_points: 3 }]);

    await apps.stopApi();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Result unavailable", exact: true })).toBeVisible();
    expect((await page.content()).includes(title), "Outage cannot serve a cached result").toBe(false);
    await apps.startApi();
    await page.reload();
    await expect(page.getByRole("region", { name: "Score", exact: true })).toContainText(scenario.score);
    await page.goto("/");
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await page.context().clearCookies();
    await login(page, "combined");
    await page.goto(resultUrl);
    await expect(page.getByRole("heading", { name: "Result unavailable", exact: true })).toBeVisible();
    const foreign = await page.content();
    expect([title, feedback, ...prompts].some((value) => foreign.includes(value)), "Foreign result concealed").toBe(false);
  });
}
