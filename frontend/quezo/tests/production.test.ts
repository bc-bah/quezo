import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { createServer, type AddressInfo } from "node:net";
import { fileURLToPath } from "node:url";
import { provider } from "./provider";

test("built Next HTTP boundary, real database and OIDC peer: fail-closed navigation and redaction", async (context) => {
  const database = process.env.QUEZO_WEB_TEST_URL;
  if (!database || !/^\/quezo_test_[0-9a-f]{32}$/.test(new URL(database).pathname)) {
    throw new Error("Use the isolated production-check launcher");
  }
  const peer = await provider();
  context.after(() => peer.close());
  const probe = createServer();
  await new Promise<void>((resolve) => probe.listen(0, "127.0.0.1", resolve));
  const port = (probe.address() as AddressInfo).port;
  await new Promise<void>((resolve) => probe.close(() => resolve()));
  const origin = `http://127.0.0.1:${port}`;
  const child = spawn(process.execPath, ["scripts/run-next.mjs", "start", "--port", String(port)], {
    cwd: fileURLToPath(new URL("../", import.meta.url)),
    env: {
      ...process.env, NEXT_TELEMETRY_DISABLED: "1", QUEZO_WEB_ENV: "local",
      QUEZO_WEB_ORIGIN: origin, QUEZO_BACKEND_ORIGIN: peer.origin,
      QUEZO_OIDC_ISSUER: peer.origin, QUEZO_OIDC_CLIENT_ID: "quezo-web",
      QUEZO_OIDC_CLIENT_SECRET: "synthetic-client-secret", QUEZO_API_AUDIENCE: "quezo-api",
      QUEZO_WEB_DATABASE_URL: database,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let logs = "";
  child.stdout.on("data", (chunk) => { logs += String(chunk); });
  child.stderr.on("data", (chunk) => { logs += String(chunk); });
  context.after(async () => {
    if (child.exitCode === null) {
      const exited = once(child, "exit");
      child.kill("SIGTERM");
      await exited;
    }
    assert.doesNotMatch(logs, /synthetic-access-token|synthetic-client-secret|synthetic-refresh-token|secret-query-sentinel/);
  });
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      const response = await fetch(origin, { signal: AbortSignal.timeout(1000) });
      if (response.ok) { ready = true; break; }
    } catch { /* Startup polling only, never an application fallback. */ }
    if (child.exitCode !== null) break;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  assert.ok(ready, `Built web server did not become ready: ${logs}`);
  const page = await fetch(`${origin}/?probe=secret-query-sentinel`);
  assert.match(await page.text(), /You are signed out/);
  assert.match(page.headers.get("cache-control")!, /no-store/);
  const csrf = await fetch(`${origin}/auth/login`, {
    method: "POST", redirect: "manual", headers: { accept: "text/html" },
  });
  assert.equal(csrf.status, 403);
  assert.match(await csrf.text(), /Return to Quezo/);

  const login = await fetch(`${origin}/auth/login`, {
    method: "POST", redirect: "manual", headers: { origin },
  });
  assert.equal(login.status, 303, login.status === 303 ? "" : await login.text());
  const loginCookie = login.headers.getSetCookie().find((value) => value.startsWith("quezo_login="))!.split(";")[0]!;
  const authorization = new URL(login.headers.get("location")!);
  const callback = peer.callback(authorization);
  const complete = await fetch(callback.url, {
    redirect: "manual", headers: { cookie: loginCookie },
  });
  assert.equal(complete.status, 303);
  const sessionCookie = complete.headers.getSetCookie().find((value) => value.startsWith("quezo_session="))!.split(";")[0]!;
  const signedIn = await fetch(origin, { headers: { cookie: sessionCookie } });
  const html = await signedIn.text();
  assert.match(html, /You are signed in/);
  assert.match(html, /href="#author"/);
  assert.doesNotMatch(html, /synthetic-access-token|synthetic-refresh-token|synthetic-client-secret|synthetic-subject/);
  const replay = await fetch(callback.url, { redirect: "manual", headers: { cookie: loginCookie } });
  assert.equal(replay.status, 401);
  peer.setActor("outage");
  const outage = await fetch(origin, { headers: { cookie: sessionCookie } });
  const outageHtml = await outage.text();
  assert.match(outageHtml, /required service is unavailable/);
  assert.doesNotMatch(outageHtml, /You are signed in|href="#author"/);
  const logout = await fetch(`${origin}/auth/logout`, {
    method: "POST", redirect: "manual", headers: { origin, cookie: sessionCookie },
  });
  assert.equal(logout.status, 303);
  const expired = await fetch(origin, { headers: { cookie: sessionCookie } });
  assert.match(await expired.text(), /Your session expired/);
});
