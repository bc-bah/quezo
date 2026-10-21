import { test, expect, login, beginLogin, webOrigin, accounts, apiMe, issuer, privatePage } from "./fixtures";
import { setTimeout as delay } from "node:timers/promises";
import { createServer } from "node:http";
import { once } from "node:events";
import type { AddressInfo } from "node:net";

test("EX-I02-01 no-referrer negative control rejects native null origins", async ({ page, apps, browser }) => {
  console.log(`Browser: Chromium ${browser.version()}`);
  await page.goto("/");
  await page.evaluate(() => {
    const meta = document.createElement("meta");
    meta.name = "referrer";
    meta.content = "no-referrer";
    document.head.append(meta);
  });
  const loginResponse = page.waitForResponse((item) => item.url() === webOrigin + "/auth/login");
  await page.getByRole("button", { name: "Sign in with Keycloak" }).click();
  const started = await loginResponse;
  console.log(`Negative-control login no-referrer: Origin=${await started.request().headerValue("origin")}; status=${started.status()}`);
  expect(await started.request().headerValue("origin")).toBe("null");
  expect(started.status()).toBe(403);
  await login(page, "author");
  await page.evaluate(() => {
    const meta = document.createElement("meta");
    meta.name = "referrer";
    meta.content = "no-referrer";
    document.head.append(meta);
  });
  const logoutResponse = page.waitForResponse((item) => item.url() === webOrigin + "/auth/logout");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  const ended = await logoutResponse;
  console.log(`Negative-control logout no-referrer: Origin=${await ended.request().headerValue("origin")}; status=${ended.status()}`);
  expect(await ended.request().headerValue("origin")).toBe("null");
  expect(ended.status()).toBe(403);
});

test("AT-01 native login and logout forms", async ({ page, apps, browser }) => {
  console.log(`Browser: Chromium ${browser.version()}`);
  await login(page, "author");
  const original = await apps.session(page);
  await expect(page.getByRole("link", { name: "Author workspace", exact: true })).toBeVisible();
  const posted = page.waitForRequest((request) => request.url() === webOrigin + "/auth/logout" && request.method() === "POST");
  const response = page.waitForResponse((item) => item.url() === webOrigin + "/auth/logout");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  const request = await posted;
  const result = await response;
  console.log(`Native logout: Origin=${await request.headerValue("origin")}; status=${result.status()}`);
  expect(await request.headerValue("origin")).toBe(webOrigin);
  expect(result.status()).toBe(303);
  expect(result.headers()["referrer-policy"]).toBe("no-referrer");
  await expect(page.getByText("You are signed out.", { exact: true })).toBeVisible();
  expect((await apps.webDb.query("SELECT 1 FROM quezo_session.sessions WHERE id_hash = $1", [original.hash])).rowCount).toBe(0);
  expect((await apiMe(original.access_token)).status).toBe(200); // Local logout is not provider revocation.
  await page.getByRole("button", { name: "Sign in with Keycloak" }).click();
  await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
  const renewed = await apps.session(page);
  expect(renewed.cookie.value === original.cookie.value, "New local session, same provider SSO").toBe(false);
});

const navigation: Record<string, string> = {
  administrator: "Account administration", author: "Author workspace", learner: "Learner workspace",
};
for (const name of ["administrator", "author", "learner", "combined", "empty"]) {
  test(`AT-01 ${name} navigation, current actor and private browser state`, async ({ page, apps }) => {
    await login(page, name);
    const session = await apps.session(page);
    const account = accounts[name]!;
    const response = await apiMe(session.access_token);
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toContain("no-store");
    expect(await response.json()).toEqual({ userId: account.id, roles: account.roles, status: "active" });
    for (const [role, label] of Object.entries(navigation)) {
      await expect(page.getByRole("link", { name: label, exact: true })).toHaveCount(account.roles.includes(role) ? 1 : 0);
    }
    if (!account.roles.length) await expect(page.getByText("No application role is assigned.", { exact: false })).toBeVisible();
    expect(session.cookie.httpOnly).toBe(true);
    expect(session.cookie.secure).toBe(false); // Explicit loopback-local mode; shared flags are unit-tested.
    expect(session.cookie.sameSite).toBe("Lax");
    expect(session.cookie.path).toBe("/");
    expect(session.cookie.domain).toBe("127.0.0.1");
    await privatePage(page, apps);
    const loaded = await page.reload();
    expect(loaded!.headers()["cache-control"]).toContain("no-store");
    await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
    expect((await apps.session(page)).cookie.value === session.cookie.value).toBe(true);
  });
}

test("AT-01 persisted session survives built-web restart and keyboard navigation", async ({ page, apps }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
  await page.getByRole("button", { name: "Sign in with Keycloak" }).focus();
  await page.keyboard.press("Enter");
  await page.locator("#username").fill(accounts.learner!.username);
  await page.keyboard.press("Tab");
  await expect(page.locator("#password")).toBeFocused();
  await page.keyboard.type(accounts.learner!.password);
  await page.keyboard.press("Enter");
  await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
  const session = await apps.session(page);
  await apps.restartWeb();
  await page.reload();
  await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
  expect((await apps.session(page)).cookie.value === session.cookie.value).toBe(true);
  await page.getByRole("link", { name: "Learner workspace", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#learner")).toBeFocused();
  await page.getByRole("button", { name: "Sign out", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("You are signed out.", { exact: true })).toBeVisible();
});

test("AT-01 old token cannot restore removed roles or disabled account", async ({ page, apps }) => {
  await login(page, "combined");
  const session = await apps.session(page);
  const id = accounts.combined!.id;
  try {
    await apps.apiDb.query("DELETE FROM quezo.account_roles WHERE account_id = $1 AND role = 'author'", [id]);
    await page.reload();
    await expect(page.getByRole("link", { name: "Author workspace", exact: true })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Learner workspace", exact: true })).toBeVisible();
    expect((await (await apiMe(session.access_token)).json()).roles).toEqual(["learner"]);
    await apps.apiDb.query("UPDATE quezo.accounts SET status = 'disabled' WHERE id = $1", [id]);
    await page.reload();
    await expect(page.getByText("Your application access is disabled.", { exact: false })).toBeVisible();
    const denied = await apiMe(session.access_token);
    expect(denied.status).toBe(403);
    expect((await denied.json()).code).toBe("ACCOUNT_DISABLED");
    expect((await apps.webDb.query("SELECT 1 FROM quezo_session.sessions WHERE id_hash = $1", [session.hash])).rowCount).toBe(0);
    // Existing provider SSO must not bootstrap/reactivate the disabled application account.
    const callback = page.waitForResponse((response) => response.url().startsWith(webOrigin + "/auth/callback"));
    await page.getByRole("button", { name: "Sign in with Keycloak" }).click();
    expect((await callback).status()).toBe(403);
    await expect(page.locator("main").getByRole("alert")).toContainText("disabled");
  } finally {
    // Fixture-only restoration, never runtime provisioning.
    await apps.apiDb.query("UPDATE quezo.accounts SET status = 'active' WHERE id = $1", [id]);
    await apps.apiDb.query("INSERT INTO quezo.account_roles(account_id, role) VALUES ($1, 'author') ON CONFLICT DO NOTHING", [id]);
  }
});

test("AT-01 inactive mapping denies the existing browser session and direct token", async ({ page, apps }) => {
  await login(page, "learner");
  const session = await apps.session(page);
  const id = accounts.learner!.id;
  try {
    await apps.apiDb.query("UPDATE quezo.identity_mappings SET active = false WHERE account_id = $1", [id]);
    await page.reload();
    await expect(page.getByText("Your session expired. Sign in again.")).toBeVisible();
    expect((await apiMe(session.access_token)).status).toBe(401);
  } finally {
    await apps.apiDb.query("UPDATE quezo.identity_mappings SET active = true WHERE account_id = $1", [id]);
  }
});

test("AT-01 direct API denies missing, malformed, tampered, wrong-audience and wrong-issuer credentials", async ({ page, apps }) => {
  await login(page, "author");
  const session = await apps.session(page);
  for (const token of [undefined, "not-a-jwt", session.access_token.slice(0, -12) + "invalidbytes"]) {
    const response = await apiMe(token);
    expect(response.status).toBe(401);
    expect((await response.json()).code).toBe("UNAUTHENTICATED");
  }
  try {
    await apps.stopApi();
    await apps.startApi({ audience: "not-quezo-api" });
    expect((await apiMe(session.access_token)).status).toBe(401);
    await apps.stopApi();
    // The same real provider keys at its loopback alias, but a mismatching exact issuer.
    await apps.startApi({ issuer: issuer.replace("localhost", "127.0.0.1") });
    expect((await apiMe(session.access_token)).status).toBe(401);
  } finally {
    await apps.stopApi();
    await apps.startApi();
  }
  expect((await apiMe(session.access_token)).status).toBe(200);
});

test("AT-01 callback state, browser binding and replay fail closed", async ({ page, apps, browser }) => {
  await beginLogin(page);
  const binding = (await page.context().cookies(webOrigin)).find((cookie) => cookie.name === "quezo_login")!;
  apps.secrets.add(binding.value);
  expect(binding.httpOnly).toBe(true);
  const failed = await page.goto(webOrigin + "/auth/callback?code=invalid-synthetic-code&state=wrong-state&iss=" + encodeURIComponent(issuer));
  expect(failed!.status()).toBe(401);
  await expect(page.locator("main").getByRole("alert")).toBeVisible();
  await expect(page.getByRole("link", { name: "Return to Quezo" })).toBeVisible();
  let callback = "";
  page.on("request", (request) => {
    if (request.url().startsWith(webOrigin + "/auth/callback?")) callback = request.url();
  });
  await login(page, "author");
  await apps.session(page);
  expect(Boolean(callback)).toBe(true);
  const fresh = await browser.newContext();
  try {
    const other = await fresh.newPage();
    expect((await other.goto(callback))!.status()).toBe(401);
  } finally { await fresh.close(); }
  expect((await page.goto(callback))!.status()).toBe(401);
});

test("AT-01 real foreign-origin form and missing/null hostile requests are denied", async ({ page, apps }) => {
  await login(page, "author");
  const session = await apps.session(page);
  const attacker = createServer((_request, response) => {
    response.setHeader("content-type", "text/html");
    response.end(`<form action="${webOrigin}/auth/logout" method="post"><button>Foreign logout</button></form>`);
  });
  attacker.listen(0, "127.0.0.1");
  await once(attacker, "listening");
  const origin = `http://127.0.0.1:${(attacker.address() as AddressInfo).port}`;
  try {
    await page.goto(origin);
    const denied = page.waitForResponse((response) => response.url() === webOrigin + "/auth/logout");
    await page.getByRole("button", { name: "Foreign logout" }).click();
    const response = await denied;
    expect(await response.request().headerValue("origin")).toBe(origin);
    expect(response.status()).toBe(403);
    await page.goto(webOrigin);
    await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
    expect((await apps.session(page)).cookie.value === session.cookie.value).toBe(true);
    // Supplemental hostile HTTP probes do not substitute for the native form tests.
    for (const action of ["login", "logout"]) {
      for (const originHeader of [undefined, "null", origin]) {
        const result = await fetch(`${webOrigin}/auth/${action}`, {
          method: "POST", headers: originHeader ? { Origin: originHeader } : {}, redirect: "manual",
        });
        expect(result.status).toBe(403);
        expect((await result.json()).code).toBe("CSRF_REJECTED");
      }
    }
  } finally {
    attacker.closeAllConnections();
    await new Promise<void>((resolve) => attacker.close(() => resolve()));
  }
});

test("AT-01 backend and both database transports fail explicitly without cached actors", async ({ page, apps }) => {
  await login(page, "author");
  const session = await apps.session(page);
  try {
    await apps.stopApi();
    await page.reload();
    await expect(page.locator("main").getByRole("alert")).toContainText("unavailable");
    await expect(page.getByRole("link", { name: "Author workspace", exact: true })).toHaveCount(0);
  } finally { await apps.startApi(); }
  for (const transport of [apps.apiTransport, apps.webTransport]) {
    try {
      await transport.close();
      await page.reload();
      await expect(page.locator("main").getByRole("alert")).toContainText("unavailable");
      await expect(page.getByText("You are signed in.", { exact: true })).toHaveCount(0);
      if (transport === apps.apiTransport) {
        const response = await apiMe(session.access_token);
        expect(response.status).toBe(503);
        expect((await response.json()).code).toBe("DEPENDENCY_UNAVAILABLE");
      }
    } finally { await transport.open(); }
    await expect.poll(async () => (await apiMe(session.access_token)).status, { timeout: 15_000 }).toBe(200);
    await page.reload();
    await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
  }
});

test("AT-01 real identity outage respects warm, expired and cold JWKS caches", async ({ page, apps, browser }) => {
  await login(page, "author");
  const session = await apps.session(page);
  // Fresh process establishes a known cache-age baseline using the real key endpoint.
  await apps.stopApi();
  await apps.startApi();
  expect((await apiMe(session.access_token)).status).toBe(200);
  apps.container("keycloak-test", true);
  try {
    expect((await apiMe(session.access_token)).status).toBe(200);
    await page.reload();
    await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
    await delay(10_100);
    let denied = await apiMe(session.access_token);
    expect(denied.status).toBe(503);
    expect((await denied.json()).code).toBe("DEPENDENCY_UNAVAILABLE");
    await page.reload();
    await expect(page.locator("main").getByRole("alert")).toContainText("unavailable");
    await apps.stopApi();
    await apps.startApi();
    denied = await apiMe(session.access_token);
    expect(denied.status).toBe(503);
    await apps.restartWeb(); // Also exercise cold OIDC discovery with no authenticated browser.
    const fresh = await browser.newContext();
    try {
      const other = await fresh.newPage();
      await other.goto(webOrigin);
      const failed = other.waitForResponse((response) => response.url() === webOrigin + "/auth/login");
      await other.getByRole("button", { name: "Sign in with Keycloak" }).click();
      expect((await failed).status()).toBe(503);
      await expect(other.locator("main").getByRole("alert")).toContainText("unavailable");
    } finally { await fresh.close(); }
  } finally {
    apps.container("keycloak-test", false);
    await apps.ready(issuer + "/.well-known/openid-configuration");
  }
  await delay(1100);
  await page.goto(webOrigin);
  await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
});

test("AT-01 actual access-token expiry caps the durable session without refresh", async ({ page, apps }) => {
  test.setTimeout(330_000);
  await login(page, "learner");
  const session = await apps.session(page);
  expect(session.expires_at.getTime()).toBeLessThanOrEqual(session.token_expires_at.getTime());
  const wait = session.token_expires_at.getTime() - Date.now() + 1100;
  expect(wait > 0 && wait <= 302_000).toBe(true);
  console.log("Expiry: waiting for the unchanged 300-second provider lifetime; no clock/row/token injection.");
  await delay(wait);
  await page.reload();
  await expect(page.getByText("Your session expired. Sign in again.")).toBeVisible();
  expect((await apiMe(session.access_token)).status).toBe(401);
  expect((await page.context().cookies(webOrigin)).some((cookie) => cookie.name === "quezo_session")).toBe(true);
});
