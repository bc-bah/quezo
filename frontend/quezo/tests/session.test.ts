import assert from "node:assert/strict";
import test from "node:test";
import { NextRequest, NextResponse } from "next/server";
import { config, actor } from "./fixtures";
import { readConfig } from "../src/lib/server/config";
import { actorFrom } from "../src/lib/server/contracts";
import { BackendFacade } from "../src/lib/server/facade";
import { publicError, WebError } from "../src/lib/server/errors";
import { requireOrigin } from "../src/lib/server/session";
import { canonicalRequest, setCookie } from "../src/lib/server/http";

test("configuration fails closed; HTTP is limited to explicitly local loopback", () => {
  assert.throws(() => readConfig({}));
  const base = {
    QUEZO_WEB_ENV: "shared", QUEZO_WEB_ORIGIN: "https://quezo.example",
    QUEZO_OIDC_ISSUER: "https://identity.example/realms/quezo",
    QUEZO_BACKEND_ORIGIN: "https://api.example",
    QUEZO_WEB_DATABASE_URL: "postgresql://quezo_web:synthetic@db.example/quezo",
    QUEZO_OIDC_CLIENT_ID: "web", QUEZO_OIDC_CLIENT_SECRET: "synthetic",
    QUEZO_API_AUDIENCE: "quezo-api",
  };
  assert.equal(readConfig(base).sessionCookie, "__Host-quezo_session");
  for (const changes of [
    { QUEZO_WEB_ORIGIN: "http://quezo.example" },
    { QUEZO_WEB_ORIGIN: "https://quezo.example/path" },
    { QUEZO_WEB_ENV: "local", QUEZO_WEB_ORIGIN: "http://not-local.example" },
    { QUEZO_WEB_ENV: "local", QUEZO_WEB_ORIGIN: "https://not-local.example" },
    { QUEZO_WEB_DATABASE_URL: "postgresql://quezo_runtime:synthetic@db.example/quezo" },
    { QUEZO_WEB_DATABASE_URL: "postgresql://quezo_web:synthetic@db.example/quezo?options=x" },
    { QUEZO_OIDC_ISSUER: "https://user:secret@identity.example" },
    { QUEZO_API_AUDIENCE: "openid admin" },
  ]) assert.throws(() => readConfig({ ...base, ...changes }));
});

test("origin protection denies absent, null, sibling, forged forwarding and cross-site origins", () => {
  const settings = config();
  for (const origin of [undefined, "null", "https://attacker.invalid", "http://localhost:3001"]) {
    assert.throws(() => requireOrigin(new Request(`${settings.origin}/auth/logout`, {
      method: "POST", headers: { ...(origin ? { origin } : {}), "x-forwarded-host": "localhost:3000" },
    }), settings), (error: unknown) => error instanceof WebError && error.status === 403);
  }
  assert.throws(() => requireOrigin(new Request(`${settings.origin}/auth/logout`, {
    method: "POST", headers: { origin: settings.origin, "sec-fetch-site": "cross-site" },
  }), settings));
  requireOrigin(new Request(`${settings.origin}/auth/logout`, {
    method: "POST", headers: { origin: settings.origin, "sec-fetch-site": "same-origin" },
  }), settings);
});

test("cookies contain only opaque ids, with host scope, HttpOnly and shared Secure", () => {
  for (const local of [true, false]) {
    const settings = { ...config(), local };
    const response = new NextResponse();
    setCookie(response, settings, "session", "a".repeat(43));
    const cookie = response.headers.get("set-cookie")!;
    assert.match(cookie, /HttpOnly/);
    assert.match(cookie, /SameSite=lax/i);
    assert.match(cookie, /Path=\//);
    assert.equal(cookie.includes("Secure"), !local);
    assert.doesNotMatch(cookie, /Domain=|access_token|synthetic-client-secret/);
    setCookie(response, settings, "session", "");
    assert.match(response.headers.get("set-cookie")!, /Max-Age=0/);
  }
});

test("Next bind origins are canonicalized only after exact Host validation; forwarding headers are ignored", () => {
  const settings = config();
  const request = new NextRequest("http://internal.invalid/auth/callback?code=synthetic", {
    headers: { host: "localhost:3000", "x-forwarded-host": "attacker.invalid", "x-forwarded-proto": "https" },
  });
  assert.equal(canonicalRequest(request, settings).url, `${settings.origin}/auth/callback?code=synthetic`);
  for (const host of ["attacker.invalid", "localhost:3001", "localhost:3000.attacker.invalid"]) {
    assert.throws(() => canonicalRequest(new NextRequest(request.url, {
      headers: { host, "x-forwarded-host": "localhost:3000" },
    }), settings));
  }
});

test("actor validation uses the producer schema, including empty/combined roles and extra-field rejection", () => {
  assert.deepEqual(actorFrom(actor), actor);
  assert.equal(actorFrom({ ...actor, roles: [] }).roles.length, 0);
  for (const changes of [
    { userId: "not-a-uuid" }, { roles: ["superuser"] }, { status: "enabled" },
    { accessToken: "synthetic-secret" }, { email: "synthetic@example.invalid" },
  ]) assert.throws(() => actorFrom({ ...actor, ...changes }));
});

test("facade consults /me afresh, uses no-store, forbids redirects and browser cookies", async () => {
  let calls = 0;
  const backend = new BackendFacade(config(), async (input) => {
    const request = new Request(input);
    calls++;
    assert.equal(request.headers.get("authorization"), "Bearer synthetic-access-token");
    assert.equal(request.headers.has("cookie"), false);
    assert.equal(request.cache, "no-store");
    assert.equal(request.redirect, "error");
    return Response.json(calls === 1 ? actor : { ...actor, roles: [] });
  });
  assert.deepEqual(await backend.actor("synthetic-access-token"), actor);
  assert.deepEqual((await backend.actor("synthetic-access-token")).roles, []);
  await assert.rejects(backend.authorizedFetch("synthetic-access-token")("https://attacker.invalid"));
  const client = backend.client("synthetic-access-token");
  assert.ok(client.GET);
});

test("safe backend errors preserve code/message/requestId/details; outages never return an actor", async () => {
  const envelope = {
    code: "VALIDATION_FAILED", message: "The request contains invalid fields.",
    requestId: actor.userId,
    details: { fields: [{ path: ["body", "name"], reason: "required" }] },
  };
  const backend = new BackendFacade(config(), async () => Response.json(envelope, { status: 422 }));
  await assert.rejects(backend.actor("synthetic-access-token"), (error: unknown) =>
    error instanceof WebError && error.status === 422
      && JSON.stringify(error.envelope) === JSON.stringify(envelope));
  for (const transport of [
    async () => { throw new Error("synthetic-access-token database://secret"); },
    async () => new Response("private-provider-error", { status: 503 }),
    async () => Response.json({ accessToken: "synthetic-access-token" }),
  ]) {
    await assert.rejects(new BackendFacade(config(), transport).actor("synthetic-access-token"));
  }
});

test("unexpected exception and token content never reach safe envelope or logs", (context) => {
  const logs: string[] = [];
  context.mock.method(console, "error", (line: string) => logs.push(line));
  const result = publicError(new Error("synthetic-access-token password cookie"));
  assert.equal(result.status, 500);
  assert.doesNotMatch(JSON.stringify([result.envelope, logs]), /synthetic-access-token|password|cookie/);
  assert.match(logs[0]!, /web_request_failed/);
});
