import type { FullConfig, FullResult, Reporter, Suite, TestCase, TestResult } from "@playwright/test/reporter";
import { existsSync, unlinkSync } from "node:fs";
import path from "node:path";

// Playwright's normal error/step output can contain callback URLs or filled credentials.
export default class SafeReporter implements Reporter {
  private readonly counts: Record<TestResult["status"], number> = {
    passed: 0, failed: 0, timedOut: 0, skipped: 0, interrupted: 0,
  };
  onBegin(_config: FullConfig, suite: Suite) {
    console.log(`Browser cases discovered: ${suite.allTests().length}`);
  }
  onTestEnd(test: TestCase, result: TestResult) {
    this.counts[result.status]++;
    console.log(`${result.status.toUpperCase()}: ${test.title} (${result.duration}ms)`);
    for (const error of result.errors) {
      const line = error.stack?.match(/(?:access|questions|quizzes|author-workspace|attempts|delivery-controls|responses|finalization|results|reporting|lifecycle)\.spec\.ts:\d+:\d+/)?.[0];
      console.log(`Failure location: ${line ?? "fixture/setup"}; raw error/call log withheld.`);
      if (error.message?.includes("strict mode violation")) console.log("Failure kind: ambiguous locator");
      else if (error.message?.includes("Timeout")) console.log("Failure kind: timeout");
      else console.log("Failure kind: assertion or setup");
    }
    for (const attachment of result.attachments) {
      if (attachment.path && path.basename(attachment.path) === "error-context.md"
        && path.resolve(attachment.path).startsWith(path.resolve(process.env.I02_RESULTS!) + path.sep)
        && existsSync(attachment.path)) {
        unlinkSync(attachment.path);
      }
    }
  }
  onStdOut(chunk: string | Buffer) { process.stdout.write(chunk); }
  onEnd(result: FullResult) {
    console.log(`Browser case counts: ${JSON.stringify(this.counts)}`);
    console.log(`I02 browser result: ${result.status}`);
  }
}
