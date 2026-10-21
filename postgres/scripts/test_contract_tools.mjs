import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";

const backend = fileURLToPath(new URL("../", import.meta.url));
const root = dirname(backend);

test("export and generation detect stale or missing output without modifying it", async () => {
  // Stay below the repo so the copied generator resolves the locked node_modules.
  const fixture = await mkdtemp(join(backend, ".contract-test-"));
  try {
    const scripts = join(fixture, "postgres", "scripts");
    const api = join(fixture, "frontend", "quezo", "src", "lib", "api");
    await mkdir(scripts, { recursive: true });
    await mkdir(api, { recursive: true });
    await cp(join(backend, "src"), join(fixture, "postgres", "src"), { recursive: true });
    for (const name of ["export_openapi.py", "generate-client.mjs"]) {
      await cp(join(backend, "scripts", name), join(scripts, name));
    }
    const exportArgs = [
      "run", "--directory", backend, "--locked", "python",
      join(scripts, "export_openapi.py"),
    ];
    const generationArgs = [join(scripts, "generate-client.mjs")];
    const fixtures = [
      ["uv", exportArgs, join(fixture, "postgres", "openapi.json")],
      [process.execPath, generationArgs, join(api, "schema.d.ts")],
    ];
    for (const [command, args, output] of fixtures) {
      const missing = spawnSync(command, [...args, "--check"], { encoding: "utf8" });
      assert.equal(missing.status, 1, missing.stderr);
      execFileSync(command, args);
      const original = await readFile(output, "utf8");
      execFileSync(command, [...args, "--check"]);
      await writeFile(output, `${original}\n`);
      const stale = spawnSync(command, [...args, "--check"], { encoding: "utf8" });
      assert.equal(stale.status, 1, stale.stderr);
      assert.match(stale.stderr, /stale/);
      assert.equal(await readFile(output, "utf8"), `${original}\n`);
      execFileSync(command, args);
      assert.equal(await readFile(output, "utf8"), original);
      execFileSync(command, [...args, "--check"]);
    }
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});

test("typed client accepts only implemented contracts and preserves error envelopes", async () => {
  const fixture = await mkdtemp(join(backend, ".contract-test-"));
  try {
    const source = join(root, "frontend", "quezo", "src", "lib", "api");
    for (const name of ["client.ts", "schema.d.ts"]) {
      await cp(join(source, name), join(fixture, name));
    }
    await writeFile(join(fixture, "consumer.ts"), `
import { createApiClient } from "./client.js";
import type { components } from "./schema.js";
const client = createApiClient("http://synthetic.invalid");
async function typesOnly() {
  const result = await client.GET("/health/live");
  if (result.data) {
    const status: "ok" = result.data.status;
  }
  if (result.error) {
    const error: components["schemas"]["ErrorEnvelope"] = result.error;
  }
  const me = await client.GET("/api/v1/me");
  if (me.data) {
    const actor: components["schemas"]["Actor"] = me.data;
  }
  // @ts-expect-error I01 must not invent assessment endpoints.
  await client.GET("/api/v1/quizzes");
  // @ts-expect-error Health has no POST operation.
  await client.POST("/health/live");
  // @ts-expect-error Health accepts no write payload.
  await client.GET("/health/live", { body: { token: "synthetic" } });
}
const actor: components["schemas"]["Actor"] = {
  userId: "b852a646-70ed-4ab9-aae4-d7fc2e0ca313",
  roles: ["author", "learner"], status: "active",
};
// @ts-expect-error Unknown roles are not permitted by the generated contract.
actor.roles = ["superuser"];
const defaults: components["schemas"]["PaginationParams"] = {};
`);
    const build = join(fixture, "build");
    execFileSync(process.execPath, [
      join(root, "node_modules", "typescript", "bin", "tsc"),
      "--strict", "--skipLibCheck", "--target", "ES2022", "--module", "NodeNext",
      "--outDir", build, join(fixture, "consumer.ts"),
    ]);
    const { createApiClient } = await import(pathToFileURL(join(build, "client.js")).href);
    const success = { status: "ok", scope: "process-only" };
    const failure = {
      code: "DEPENDENCY_UNAVAILABLE", message: "A required service is unavailable.",
      requestId: "b852a646-70ed-4ab9-aae4-d7fc2e0ca313",
    };
    for (const [status, body] of [[200, success], [503, failure]]) {
      const client = createApiClient("http://synthetic.invalid", async (request) => {
        assert.equal(request.url, "http://synthetic.invalid/health/live");
        assert.equal(request.headers.has("authorization"), false);
        return Response.json(body, {
          status, headers: { "X-Request-ID": failure.requestId },
        });
      });
      const result = await client.GET("/health/live");
      assert.equal(result.response.status, status);
      assert.equal(result.response.headers.get("X-Request-ID"), failure.requestId);
      assert.deepEqual(status === 200 ? result.data : result.error, body);
    }
    const failedNetwork = createApiClient("http://synthetic.invalid", async () => {
      throw new TypeError("synthetic network outage");
    });
    await assert.rejects(failedNetwork.GET("/health/live"), /synthetic network outage/);
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});
