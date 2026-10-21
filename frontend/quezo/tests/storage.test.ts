import assert from "node:assert/strict";
import { before, after, test } from "node:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createServer, connect, type AddressInfo, type Socket } from "node:net";
import { Pool } from "pg";
import { config } from "./fixtures";
import { provider } from "./provider";
import { SessionStore } from "../src/lib/server/store";
import { WebSession } from "../src/lib/server/session";
import { WebError } from "../src/lib/server/errors";
import { NextRequest } from "next/server";
import { authRoute } from "../src/lib/server/http";

const settings = config();
for (const value of [process.env.QUEZO_WEB_TEST_URL, process.env.QUEZO_WEB_TEST_MIGRATION_URL]) {
  if (!value) throw new Error("Run via isolated PostgreSQL pytest fixture");
  const url = new URL(value);
  if (!["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
    || !/^\/quezo_test_[0-9a-f]{32}$/.test(url.pathname)) {
    throw new Error("Refusing non-isolated database");
  }
}
const migration = new Pool({ connectionString: process.env.QUEZO_WEB_TEST_MIGRATION_URL, max: 1 });
let store: SessionStore;
before(async () => { store = await SessionStore.open(settings); });
after(async () => { await store?.close(); await migration.end(); });
const digest = (id: string) => createHash("sha256").update(id).digest("hex");
const loginRequest = () => new Request(`${settings.origin}/auth/login`, {
  method: "POST", headers: { origin: settings.origin },
});
const logoutRequest = () => new Request(`${settings.origin}/auth/logout`, {
  method: "POST", headers: { origin: settings.origin },
});

async function seededSession() {
  const login = await store.beginLogin({ state: "s", nonce: "n", verifier: "v" });
  await store.consumeLogin(login);
  return store.createSession("synthetic-access-token", new Date(Date.now() + 3600000), login);
}

test("real store hashes opaque identifiers, caps absolute/idle expiry and excludes refresh/id tokens", async () => {
  const id = await seededSession();
  assert.match(id, /^[A-Za-z0-9_-]{43}$/);
  const result = await migration.query(
    "SELECT * FROM quezo_session.sessions WHERE id_hash = $1", [digest(id)],
  );
  const row = result.rows[0];
  assert.notEqual(row.id_hash, id);
  assert.equal(row.access_token, "synthetic-access-token");
  assert.ok(row.expires_at <= row.token_expires_at);
  assert.ok(row.expires_at.getTime() - row.created_at.getTime() <= 28800000);
  assert.ok(row.idle_expires_at.getTime() - row.created_at.getTime() <= 1800001);
  assert.doesNotMatch(JSON.stringify(row), /refresh_token|id_token|roles|status|email/);
});

test("login transaction consume is atomic, rejects concurrent replay and expires", async () => {
  const id = await store.beginLogin({ state: "s", nonce: "n", verifier: "v" });
  const attempts = await Promise.all([store.consumeLogin(id), store.consumeLogin(id)]);
  assert.equal(attempts.filter(Boolean).length, 1);
  const expired = await store.beginLogin({ state: "s", nonce: "n", verifier: "v" });
  await migration.query(`
    UPDATE quezo_session.login_transactions SET created_at = clock_timestamp() - interval '10 minutes',
    expires_at = clock_timestamp() - interval '1 minute' WHERE id_hash = $1
  `, [digest(expired)]);
  assert.equal(await store.consumeLogin(expired), undefined);
});

test("idle/absolute expiry and logout invalidate durable sessions", async () => {
  for (const kind of ["idle", "absolute"]) {
    const id = await seededSession();
    await migration.query(kind === "idle"
      ? "UPDATE quezo_session.sessions SET idle_expires_at = clock_timestamp() - interval '1 second' WHERE id_hash = $1"
      : `UPDATE quezo_session.sessions SET created_at = statement_timestamp() - interval '10 minutes',
          expires_at = statement_timestamp() - interval '1 minute',
          idle_expires_at = statement_timestamp() - interval '1 minute' WHERE id_hash = $1`, [digest(id)]);
    assert.equal(await store.session(id), undefined);
  }
  const id = await seededSession();
  await store.logout(id);
  assert.equal(await store.session(id), undefined);
});

test("new login rotates prior session and pending login; logout cancels an in-flight callback", async () => {
  const id = await seededSession();
  const prior = await store.beginLogin({ state: "s", nonce: "n", verifier: "v" });
  const login = await store.beginLogin({ state: "s2", nonce: "n2", verifier: "v2" }, prior, id);
  assert.equal(await store.session(id), undefined);
  assert.equal(await store.consumeLogin(prior), undefined);
  assert.ok(await store.consumeLogin(login));
  await store.logout(undefined, login);
  await assert.rejects(store.createSession("synthetic", new Date(Date.now() + 60000), login));
});

test("concurrent callback completion cannot resurrect a logged-out login", async () => {
  for (let attempt = 0; attempt < 5; attempt++) {
    const login = await store.beginLogin({ state: "s", nonce: "n", verifier: "v" });
    await store.consumeLogin(login);
    const completion = store.createSession("synthetic", new Date(Date.now() + 60000), login);
    const logout = store.logout(undefined, login);
    const results = await Promise.allSettled([completion, logout]);
    assert.equal(results[1]?.status, "fulfilled");
    const session = results[0];
    if (session?.status === "fulfilled") assert.equal(await store.session(session.value), undefined);
    const rows = await migration.query("SELECT count(*) FROM quezo_session.sessions WHERE login_hash = $1", [digest(login)]);
    assert.equal(rows.rows[0].count, "0");
  }
});

test("pool bounds reject excess borrowers and close without leaking locked queries", async () => {
  const id = await seededSession();
  const client = await migration.connect();
  try {
    await client.query("BEGIN");
    await client.query("SELECT id_hash FROM quezo_session.sessions WHERE id_hash = $1 FOR UPDATE", [digest(id)]);
    const pending = Promise.allSettled(Array.from({ length: 30 }, () => store.session(id)));
    await new Promise((resolve) => setTimeout(resolve, 100));
    const connections = await client.query("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND application_name = 'quezo-web'");
    assert.ok(Number(connections.rows[0].count) <= 5);
    await client.query("COMMIT");
    const outcomes = await pending;
    assert.ok(outcomes.some((outcome) => outcome.status === "rejected"));
    assert.ok(outcomes.some((outcome) => outcome.status === "fulfilled"));
  } finally {
    await client.query("ROLLBACK");
    client.release();
  }
});

test("sessions persist across separate process exit/restart and logout remains invalidated", () => {
  const child = (action: string, id?: string) => {
    const result = spawnSync(process.execPath, [
      "--conditions=react-server", "--import", "tsx", "frontend/quezo/tests/session-worker.ts",
    ], { input: JSON.stringify({ action, id }), encoding: "utf8", timeout: 20000 });
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  const id = child("create");
  assert.match(id, /^[A-Za-z0-9_-]{43}$/);
  assert.equal(child("read", id), "true");
  assert.equal(child("logout", id), "invalidated");
  assert.equal(child("read", id), "false");
  const loginId = child("create-login");
  assert.equal(child("consume-login", loginId), "true");
  assert.equal(child("consume-login", loginId), "false");
});

test("real openid-client code+PKCE exchange validates signed nonce and rejects replay", async (context) => {
  const peer = await provider();
  context.after(() => peer.close());
  const web = new WebSession({ ...settings, issuer: peer.origin, backend: peer.origin }, store);
  const login = await web.login(loginRequest());
  assert.equal(login.url.searchParams.get("code_challenge_method"), "S256");
  assert.equal(login.url.searchParams.get("response_type"), "code");
  assert.equal(login.url.searchParams.get("redirect_uri"), settings.redirectUri);
  assert.equal(login.url.searchParams.get("scope"), "openid quezo-api");
  assert.ok(login.url.searchParams.get("nonce"));
  const callback = peer.callback(login.url);
  const id = await web.callback(callback, login.id);
  assert.equal((await web.view(id)).state, "signed-in");
  await assert.rejects(web.callback(callback, login.id));
  const view = await web.view(id);
  assert.doesNotMatch(JSON.stringify(view), /synthetic-access-token|refresh-token|id_token|synthetic-subject/);
  await web.logout(logoutRequest(), id);
  assert.equal((await web.view(id)).state, "expired");
});

test("callback rejects wrong state, cookie, redirect, nonce, issuer, audience, signature and expiry", async (context) => {
  const peer = await provider();
  context.after(() => peer.close());
  const web = new WebSession({ ...settings, issuer: peer.origin, backend: peer.origin }, store);
  for (const defect of ["state", "cookie", "redirect", "nonce", "issuer", "audience", "signature", "expiry"]) {
    const login = await web.login(loginRequest());
    const callback = peer.callback(login.url, defect);
    let url = new URL(callback.url);
    if (defect === "state") url.searchParams.set("state", "incorrect");
    if (defect === "redirect") url = new URL(callback.url.replace("/auth/callback", "/wrong"));
    await assert.rejects(
      web.callback(new Request(url), defect === "cookie" ? "a".repeat(43) : login.id),
      defect,
    );
  }
});

test("backend roles/status are live; disabled/401 invalidates and outages/missing I01 never authenticate", async (context) => {
  const peer = await provider();
  context.after(() => peer.close());
  const web = new WebSession({ ...settings, issuer: peer.origin, backend: peer.origin }, store);
  const id = await seededSession();
  assert.equal((await web.view(id)).state, "signed-in");
  peer.setActor("empty");
  const changed = await web.view(id);
  assert.equal(changed.state, "signed-in");
  if (changed.state === "signed-in") assert.deepEqual(changed.actor.roles, []);
  for (const mode of ["outage", "missing"] as const) {
    peer.setActor(mode);
    assert.equal((await web.view(id)).state, "error");
    const login = await web.login(loginRequest());
    await assert.rejects(web.callback(peer.callback(login.url), login.id));
  }
  peer.setActor("disabled");
  assert.equal((await web.view(id)).state, "disabled");
  assert.equal(await store.session(id), undefined);
  const login = await web.login(loginRequest());
  await assert.rejects(web.callback(peer.callback(login.url), login.id));
  peer.setActor("unauthenticated");
  assert.equal((await web.view(await seededSession())).state, "expired");
});

test("origin denials precede storage mutation and identity outages fail explicitly", async (context) => {
  const peer = await provider();
  context.after(() => peer.close());
  const web = new WebSession({ ...settings, issuer: peer.origin, backend: peer.origin }, store);
  const id = await seededSession();
  const bad = new Request(`${settings.origin}/auth/logout`, { method: "POST" });
  await assert.rejects(web.logout(bad, id), (error: unknown) =>
    error instanceof WebError && error.envelope.code === "CSRF_REJECTED");
  assert.ok(await store.session(id));
  await assert.rejects(web.login(bad));
  peer.setIdentityDown(true);
  await assert.rejects(web.login(loginRequest()));
  peer.setIdentityDown(false);
  const login = await web.login(loginRequest());
  peer.setIdentityDown(true);
  await assert.rejects(web.callback(peer.callback(login.url), login.id), (error: unknown) =>
    error instanceof WebError && error.status === 503
      && error.envelope.code === "DEPENDENCY_UNAVAILABLE");
  assert.equal((await web.view(undefined)).state, "signed-out");
});

test("HTTP routes return opaque cookies, private responses, actionable HTML and no token disclosure", async (context) => {
  const peer = await provider();
  context.after(() => { globalThis.quezoWeb = undefined; return peer.close(); });
  const web = new WebSession({ ...settings, issuer: peer.origin, backend: peer.origin }, store);
  globalThis.quezoWeb = Promise.resolve(web);
  const host = new URL(settings.origin).host;
  const login = await authRoute("login", new NextRequest(loginRequest(), {
    headers: { origin: settings.origin, host },
  }));
  assert.equal(login.status, 303);
  assert.match(login.headers.get("cache-control")!, /private, no-store/);
  const loginId = login.cookies.get(settings.loginCookie)!.value;
  const callback = peer.callback(new URL(login.headers.get("location")!));
  const response = await authRoute("callback", new NextRequest(callback.url, {
    headers: { cookie: `${settings.loginCookie}=${loginId}`, host },
  }));
  assert.equal(response.status, 303);
  assert.equal(response.headers.get("location"), `${settings.origin}/`);
  const id = response.cookies.get(settings.sessionCookie)!.value;
  assert.match(id, /^[A-Za-z0-9_-]{43}$/);
  assert.doesNotMatch(JSON.stringify([...response.headers]), /synthetic-access-token|refresh-token|synthetic-client-secret/);
  const denial = await authRoute("logout", new NextRequest(logoutRequest().url, {
    method: "POST", headers: { cookie: `${settings.sessionCookie}=${id}`, accept: "text/html", host },
  }));
  assert.equal(denial.status, 403);
  assert.match(await denial.text(), /Return to Quezo/);
  assert.ok(await store.session(id));
  const logout = await authRoute("logout", new NextRequest(logoutRequest().url, {
    method: "POST", headers: { origin: settings.origin, cookie: `${settings.sessionCookie}=${id}`, host },
  }));
  assert.equal(logout.status, 303);
  assert.match(logout.headers.get("set-cookie")!, /Max-Age=0/);
  assert.equal(await store.session(id), undefined);
});

test("startup failure closes connections; database network outage never uses cached sessions", async (context) => {
  const baseline = await migration.query("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = 'quezo_web'");
  await migration.query("ALTER TABLE quezo_session.sessions RENAME TO startup_probe");
  try { await assert.rejects(SessionStore.open(settings)); }
  finally { await migration.query("ALTER TABLE quezo_session.startup_probe RENAME TO sessions"); }
  const afterFailure = await migration.query("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = 'quezo_web'");
  assert.deepEqual(afterFailure.rows, baseline.rows);

  const target = new URL(settings.databaseUrl);
  const upstreamPort = Number(target.port);
  const sockets = new Set<Socket>();
  const proxy = createServer((socket) => {
    const upstream = connect(upstreamPort, target.hostname);
    for (const member of [socket, upstream]) {
      sockets.add(member);
      member.on("error", () => {});
      member.on("close", () => sockets.delete(member));
    }
    socket.pipe(upstream).pipe(socket);
  });
  context.after(() => {
    for (const socket of sockets) socket.destroy();
    proxy.close();
  });
  await new Promise<void>((resolve) => proxy.listen(0, "127.0.0.1", resolve));
  target.port = String((proxy.address() as AddressInfo).port);
  const isolated = await SessionStore.open({ ...settings, databaseUrl: target.href });
  try {
    const id = await seededSession();
    assert.ok(await isolated.session(id));
    for (const socket of sockets) socket.destroy();
    await new Promise<void>((resolve) => proxy.close(() => resolve()));
    const web = new WebSession(settings, isolated);
    assert.equal((await web.view(id)).state, "error");
    await assert.rejects(SessionStore.open({ ...settings, databaseUrl: target.href }));
  } finally {
    for (const socket of sockets) socket.destroy();
    proxy.close();
    await isolated.close();
  }
});
