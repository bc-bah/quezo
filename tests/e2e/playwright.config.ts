import { defineConfig } from "@playwright/test";

if (!/^quezo-i02-[a-f0-9]{12}$/.test(process.env.I02_OWNED_PROJECT ?? "")) {
  throw new Error("Use npm run test:e2e; standalone browser tests require the guarded launcher.");
}

export default defineConfig({
  testDir: ".",
  testMatch: ["access.spec.ts", "questions.spec.ts", "quizzes.spec.ts", "attempts.spec.ts", "responses.spec.ts", "finalization.spec.ts", "results.spec.ts", "lifecycle.spec.ts"],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["./safe-reporter.ts"]],
  outputDir: process.env.I02_RESULTS!,
  preserveOutput: "never",
  use: {
    browserName: "chromium",
    baseURL: process.env.I02_WEB_ORIGIN!,
    trace: "off",
    screenshot: "off",
    video: "off",
    serviceWorkers: "block",
  },
});
