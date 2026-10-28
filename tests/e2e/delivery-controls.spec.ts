import { randomUUID } from "node:crypto";
import { createApiClient } from "../../frontend/quezo/src/lib/api/client";
import type { components } from "../../frontend/quezo/src/lib/api/schema";
import { test, expect, login, apiOrigin, accounts, webOrigin } from "./fixtures";

test("D04 AT-05/06/09/12 settings preview and keyboard timing choices preserve frozen controls", async ({ page, apps, browser }) => {
  test.setTimeout(180_000);
  await login(page, "author");
  page.setDefaultTimeout(15_000);
  const token = (await apps.session(page)).access_token;
  const client = createApiClient(apiOrigin, async (input, init) => {
    const request = new Request(input, init);
    request.headers.set("Authorization", `Bearer ${token}`);
    return fetch(request);
  });
  const bank = await client.POST("/api/v1/question-banks", { body: { name: "D04 bank " + randomUUID() } });
  expect(bank.response.status).toBe(201);
  const options = [{ id: randomUUID(), text: "D04 first" }, { id: randomUUID(), text: "D04 second" }];
  const prompt = "D04 timing prompt " + randomUUID();
  const feedback = "D04 protected feedback " + randomUUID();
  apps.assessmentContent.add(prompt); apps.assessmentContent.add(feedback);
  const question = await client.POST("/api/v1/questions", { body: {
    bankId: bank.data!.id, questionType: "mcq", prompt, options,
    correctOptionId: options[0]!.id, defaultPoints: 3, feedback,
  } });
  expect(question.response.status).toBe(201);
  const end = new Date(Date.now() + 3600000).toISOString().slice(0, 19);
  const titles: string[] = [];
  for (const mode of ["standard", "adjusted", "off"] as const) {
    const title = "D04 " + mode + " " + randomUUID();
    titles.push(title);
    const draft = await client.POST("/api/v1/quizzes", { body: {
      title, questions: [{ questionId: question.data!.questionId, versionId: question.data!.versionId }],
    } });
    expect(draft.response.status).toBe(201);
    const path = `/author/quizzes/${draft.data!.id}`;
    await page.goto(path);
    await expect(page.getByLabel("Unlimited authored duration", { exact: true })).toBeEnabled();
    await page.getByLabel("Unlimited authored duration", { exact: true }).focus();
    await page.keyboard.press("Space");
    await page.getByLabel("Duration (seconds)", { exact: true }).fill("604800");
    await page.getByLabel("Unlimited attempts", { exact: true }).check();
    await page.getByLabel("IANA scheduling time zone").fill("America/New_York");
    // Both occurrences of the repeated local 01:30 are explicit distinct UTC inputs.
    await page.getByLabel("Availability start (UTC)").fill("2026-11-01T05:30");
    await page.getByLabel("Availability end (UTC)").fill("2026-11-01T06:30");
    await expect(page.getByText(/01:30:00 GMT-4/)).toBeVisible();
    await expect(page.getByText(/01:30:00 GMT-5/)).toBeVisible();
    await page.getByLabel("Availability start (UTC)").fill("");
    await page.getByLabel("Availability end (UTC)").fill(end.replace(/:00$/, ""));
    await page.getByLabel("Randomize question order").check();
    await page.getByLabel("Randomize option order").uncheck();
    await page.getByLabel("Score release").selectOption("after_availability_end");
    await page.getByLabel("Correct answer release").selectOption("never");
    await page.getByLabel("Explanation release").selectOption("after_finalization");
    await page.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Edit draft revision 2" })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Duration (seconds)", { exact: true })).toHaveValue("604800");
    await expect(page.getByLabel("Unlimited attempts", { exact: true })).toBeChecked();
    const before = await apps.apiDb.query(`SELECT
      (SELECT count(*)::int FROM quezo.assignments) AS assignments,
      (SELECT count(*)::int FROM quezo.attempts) AS attempts,
      (SELECT count(*)::int FROM quezo.grades) AS grades`);
    await page.getByRole("link", { name: "Preview saved draft" }).click();
    const preview = page.getByRole("region", { name: "Timing preview" });
    await expect(preview.getByRole("combobox", { name: "Attempt timing" })).toBeEnabled();
    await preview.getByRole("combobox", { name: "Attempt timing" }).focus();
    await page.keyboard.press("ArrowDown");
    await expect(preview.getByRole("combobox", { name: "Attempt timing" })).toHaveValue("adjusted");
    await expect(preview.getByRole("spinbutton", { name: "Adjusted duration (seconds)" })).toHaveValue("6048000");
    await page.keyboard.press("ArrowDown");
    await expect(preview.getByRole("combobox", { name: "Attempt timing" })).toHaveValue("off");
    expect((await page.content()).includes(feedback), "Preview excludes private feedback").toBe(false);
    expect((await apps.apiDb.query(`SELECT
      (SELECT count(*)::int FROM quezo.assignments) AS assignments,
      (SELECT count(*)::int FROM quezo.attempts) AS attempts,
      (SELECT count(*)::int FROM quezo.grades) AS grades`)).rows).toEqual(before.rows);
    await page.getByRole("link", { name: "Back to quiz", exact: true }).click();
    await page.getByLabel("I confirm publication of this saved draft").check();
    await page.getByRole("button", { name: "Publish saved draft" }).click();
    await page.getByRole("link", { name: "View published version" }).click();
    await page.getByLabel("Active learner").selectOption(accounts.learner!.id);
    await page.getByRole("button", { name: "Assign learner", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Assignment confirmed");
  }
  const context = await browser.newContext({ baseURL: webOrigin });
  const learner = await context.newPage();
  try {
    await login(learner, "learner");
    learner.setDefaultTimeout(15_000);
    const learnerToken = (await apps.session(learner)).access_token;
    for (const [index, mode] of (["standard", "adjusted", "off"] as const).entries()) {
      await learner.goto("/learner");
      const card = learner.getByRole("region", { name: titles[index]!, exact: true });
      await expect(card).toContainText("remaining: unlimited");
      const timing = card.getByRole("combobox", { name: "Attempt timing" });
      await expect(timing).toBeEnabled();
      await timing.focus();
      if (mode !== "standard") await learner.keyboard.press("ArrowDown");
      if (mode === "off") await learner.keyboard.press("ArrowDown");
      await expect(timing).toHaveValue(mode);
      if (mode === "adjusted") {
        await learner.keyboard.press("Tab");
        await expect(card.getByRole("spinbutton", { name: "Adjusted duration (seconds)" })).toBeFocused();
        await expect(card.getByRole("spinbutton", { name: "Adjusted duration (seconds)" })).toHaveValue("6048000");
        await learner.keyboard.press("Tab");
      } else {
        await learner.keyboard.press("Tab");
      }
      await expect(card.getByRole("button", { name: "Start attempt", exact: true })).toBeFocused();
      await learner.keyboard.press("Enter");
      await expect(learner).toHaveURL(/\/learner\/attempts\/[0-9a-f-]+$/);
      await expect(learner.getByText(`Frozen timing: ${mode}`, { exact: false })).toBeVisible();
      await expect(learner.getByRole("combobox", { name: "Attempt timing" })).toHaveCount(0);
      const attemptId = new URL(learner.url()).pathname.split("/").at(-1)!;
      const read = async () => {
        const response = await fetch(`${apiOrigin}/api/v1/attempts/${attemptId}`, {
          headers: { Authorization: `Bearer ${learnerToken}` },
        });
        expect(response.status).toBe(200);
        const text = await response.text();
        expect(["correctOption", feedback].some((value) => text.includes(value)), "Ordinary read is filtered").toBe(false);
        const attempt: components["schemas"]["Attempt"] = JSON.parse(text);
        return attempt;
      };
      const frozen = await read();
      expect(frozen.timingChoice).toBe(mode);
      if (mode === "off") expect(frozen.deadline).toBeNull();
      if (mode === "adjusted") expect(Date.parse(frozen.deadline!) - Date.parse(frozen.startedAt)).toBe(6048000000);
      if (mode === "standard") expect(frozen.deadline).toBe(end + "Z");
      await learner.reload();
      expect(await read()).toEqual(frozen);
      await learner.getByRole("link", { name: "My assignments", exact: true }).click();
      await learner.getByRole("region", { name: titles[index]!, exact: true })
        .getByRole("button", { name: "Resume attempt" }).click();
      expect(await read()).toEqual(frozen);
    }
  } finally { await context.close(); }
});
