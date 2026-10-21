import { test as base, expect, type Page } from "@playwright/test";
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { createHash } from "node:crypto";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { createServer, connect, type Socket, type AddressInfo } from "node:net";
import pg from "pg";

export const webOrigin = process.env.I02_WEB_ORIGIN!;
export const apiOrigin = process.env.I02_API_ORIGIN!;
export const issuer = process.env.I02_ISSUER!;
type Account = { username: string; password: string; id: string; roles: string[] };
export const accounts: Record<string, Account> = JSON.parse(process.env.I02_ACCOUNTS!);

// Forward bytes unchanged to real PostgreSQL; closing sockets induces an actual
// transport outage without stopping/reinitializing its tmpfs database.
class DatabaseTransport {
  private readonly sockets = new Set<Socket>();
  private readonly server;
  private port = 0;
  constructor(private readonly target: string) {
    this.server = createServer((incoming) => {
      const upstream = connect({ host: new URL(target).hostname, port: Number(new URL(target).port) });
      for (const socket of [incoming, upstream]) {
        this.sockets.add(socket);
        socket.on("close", () => this.sockets.delete(socket));
        socket.on("error", () => { incoming.destroy(); upstream.destroy(); });
      }
      incoming.pipe(upstream).pipe(incoming);
    });
  }
  async open() {
    this.server.listen(this.port, "127.0.0.1");
    await once(this.server, "listening");
    this.port = (this.server.address() as AddressInfo).port;
  }
  get url() {
    const value = new URL(this.target);
    value.hostname = "127.0.0.1";
    value.port = String(this.port);
    return value.href;
  }
  async close() {
    for (const socket of this.sockets) socket.destroy();
    if (!this.server.listening) return;
    await new Promise<void>((resolve, reject) => this.server.close((error) => error ? reject(error) : resolve()));
  }
}

function appEnvironment(): NodeJS.ProcessEnv {
  return Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    /^(PATH|PATHEXT|SYSTEMROOT|WINDIR|COMSPEC|TEMP|TMP|HOME|USERPROFILE|APPDATA|LOCALAPPDATA|LANG)$/i.test(key)));
}

export class Applications {
  private api?: ChildProcess;
  private web?: ChildProcess;
  private logs = "";
  readonly secrets = new Set<string>([
    process.env.I02_CLIENT_SECRET!, "i02-query-sentinel", ...Object.values(accounts).map((account) => account.password),
  ]);
  readonly webDb = new pg.Pool({ connectionString: process.env.I02_WEB_DATABASE, max: 1, connectionTimeoutMillis: 5000 });
  readonly apiDb = new pg.Pool({ connectionString: process.env.I02_API_DATABASE, max: 1, connectionTimeoutMillis: 5000 });
  readonly webTransport = new DatabaseTransport(process.env.I02_WEB_DATABASE!);
  readonly apiTransport = new DatabaseTransport(process.env.I02_API_DATABASE!);
  private readonly paused = new Set<"postgres-test" | "keycloak-test">();

  private start(command: string, args: string[], cwd: string, env: NodeJS.ProcessEnv) {
    const child = spawn(command, args, { cwd, env, stdio: ["ignore", "pipe", "pipe"] });
    child.stdout!.on("data", (chunk: Buffer) => { this.logs += chunk.toString(); });
    child.stderr!.on("data", (chunk: Buffer) => { this.logs += chunk.toString(); });
    child.on("error", () => { this.logs += "I02 child launch failed"; });
    return child;
  }

  async ready(url: string, child?: ChildProcess) {
    for (let attempt = 0; attempt < 100; attempt++) {
      if (child && child.exitCode !== null) throw new Error("I02 application exited before readiness");
      try {
        const response = await fetch(url, { signal: AbortSignal.timeout(1000) });
        if (response.ok) return;
      } catch { /* Bounded readiness only, never authentication fallback. */ }
      await delay(100);
    }
    throw new Error("I02 readiness deadline exceeded");
  }

  async startApi(settings: { issuer?: string; audience?: string } = {}) {
    this.api = this.start(process.env.I02_PYTHON!, [
      "-m", "uvicorn", "--app-dir", "src", "quezo_api.app:create_app", "--factory",
      "--loop", "quezo_api.database:database_loop_factory", "--host", "127.0.0.1",
      "--port", new URL(apiOrigin).port, "--no-server-header", "--no-access-log",
    ], path.resolve("postgres"), {
      ...appEnvironment(), QUEZO_DATABASE_URL: this.apiTransport.url,
      QUEZO_OIDC_ISSUER: settings.issuer ?? issuer, QUEZO_API_AUDIENCE: settings.audience ?? "quezo-api",
      QUEZO_IDENTITY_CACHE_SECONDS: "10", QUEZO_IDENTITY_REFRESH_SECONDS: "1",
      QUEZO_IDENTITY_TIMEOUT: "1", QUEZO_DB_POOL_TIMEOUT: "1",
    });
    await this.ready(apiOrigin + "/health/live", this.api);
  }

  async startWeb() {
    this.web = this.start(process.execPath, ["scripts/run-next.mjs", "start", "--port", new URL(webOrigin).port],
      path.resolve("frontend/quezo"), {
        ...appEnvironment(), NEXT_TELEMETRY_DISABLED: "1", QUEZO_WEB_ENV: "local",
        QUEZO_WEB_ORIGIN: webOrigin, QUEZO_BACKEND_ORIGIN: apiOrigin,
        QUEZO_OIDC_ISSUER: issuer, QUEZO_OIDC_CLIENT_ID: "quezo-web",
        QUEZO_OIDC_CLIENT_SECRET: process.env.I02_CLIENT_SECRET, QUEZO_API_AUDIENCE: "quezo-api",
        QUEZO_WEB_DATABASE_URL: this.webTransport.url,
      });
    await this.ready(webOrigin, this.web);
    const response = await fetch(webOrigin);
    expect((await response.text()).includes("You are signed out."), "Built web/session store readiness").toBe(true);
  }

  private async stop(child?: ChildProcess) {
    if (!child || child.exitCode !== null) return;
    const exited = once(child, "exit");
    child.kill("SIGTERM");
    const timeout = setTimeout(() => child.kill("SIGKILL"), 10_000);
    try { await exited; } finally { clearTimeout(timeout); }
  }
  async stopApi() { await this.stop(this.api); }
  async restartWeb() { await this.stop(this.web); await this.startWeb(); }
  container(service: "postgres-test" | "keycloak-test", pause: boolean) {
    const project = process.env.I02_OWNED_PROJECT!;
    const id = execFileSync("docker", ["ps", "-q", "--filter", `label=com.docker.compose.project=${project}`,
      "--filter", `label=com.docker.compose.service=${service}`], { encoding: "utf8" }).trim();
    if (!/^[a-f0-9]{12,64}$/.test(id)) throw new Error("Expected exactly one owned test container");
    execFileSync("docker", [pause ? "pause" : "unpause", id], { stdio: "pipe" });
    if (pause) this.paused.add(service); else this.paused.delete(service);
  }
  async session(page: Page) {
    const cookie = (await page.context().cookies(webOrigin)).find((item) => item.name === "quezo_session");
    expect(Boolean(cookie), "Opaque session cookie issued").toBe(true);
    this.secrets.add(cookie!.value);
    const hash = createHash("sha256").update(cookie!.value).digest("hex");
    const result = await this.webDb.query<{ access_token: string; token_expires_at: Date; expires_at: Date }>(
      "SELECT access_token, token_expires_at, expires_at FROM quezo_session.sessions WHERE id_hash = $1", [hash]);
    expect(result.rowCount).toBe(1);
    const row = result.rows[0]!;
    this.secrets.add(row.access_token);
    return { ...row, hash, cookie: cookie! };
  }
  async close() {
    for (const service of this.paused) this.container(service, false);
    try {
      await this.stop(this.web);
      await this.stop(this.api);
    } finally {
      await this.webDb.end();
      await this.apiDb.end();
      await this.webTransport.close();
      await this.apiTransport.close();
    }
    expect([...this.secrets].some((secret) => this.logs.includes(secret)), "Application logs contain no usable secrets").toBe(false);
    expect(/code=|[?&]state=|Authorization:|Cookie:/i.test(this.logs), "No callback/header logging").toBe(false);
  }
}

export async function beginLogin(page: Page) {
  await page.goto("/?probe=i02-query-sentinel");
  const request = page.waitForRequest((item) => item.url() === webOrigin + "/auth/login" && item.method() === "POST");
  const response = page.waitForResponse((item) => item.url() === webOrigin + "/auth/login");
  await page.getByRole("button", { name: "Sign in with Keycloak" }).click();
  const posted = await request;
  const result = await response;
  console.log(`Native login: Origin=${await posted.headerValue("origin")}; status=${result.status()}`);
  expect(await posted.headerValue("origin"), "Native login Origin").toBe(webOrigin);
  expect(await posted.headerValue("referer"), "Only origin, never path/query").toBe(webOrigin + "/");
  expect(result.status()).toBe(303);
  expect(result.headers()["referrer-policy"]).toBe("no-referrer");
  await expect(page.locator("#username")).toBeVisible();
}

export async function login(page: Page, name: string) {
  await beginLogin(page);
  const account = accounts[name]!;
  await page.locator("#username").fill(account.username);
  await page.locator("#password").fill(account.password);
  await page.locator("#kc-login").click();
  await expect(page.getByText("You are signed in.", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(webOrigin + "/");
}

export async function apiMe(token?: string) {
  return fetch(apiOrigin + "/api/v1/me", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: AbortSignal.timeout(10_000),
  });
}

export async function privatePage(page: Page, apps: Applications) {
  const visible = await page.evaluate(() => JSON.stringify({
    html: document.documentElement.outerHTML,
    local: { ...localStorage }, session: { ...sessionStorage }, cookies: document.cookie,
  }));
  expect([...apps.secrets].some((secret) => visible.includes(secret)), "No usable secrets in DOM or web storage").toBe(false);
  expect(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/.test(visible), "No JWT in DOM or storage").toBe(false);
  expect(await page.evaluate(() => /quezo_(session|login)=/.test(document.cookie))).toBe(false);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
}

export const test = base.extend<{ privacy: void }, { apps: Applications }>({
  apps: [async ({}, use) => {
    const apps = new Applications();
    try {
      await apps.ready(issuer + "/.well-known/openid-configuration");
      await apps.webTransport.open();
      await apps.apiTransport.open();
      await apps.startApi();
      await apps.startWeb();
      await use(apps);
    } finally { await apps.close(); }
  }, { scope: "worker" }],
  privacy: [async ({ page, apps }, use) => {
    const checks: Promise<void>[] = [];
    const violations: string[] = [];
    page.on("response", (response) => {
      if (!response.url().startsWith(webOrigin + "/auth/")) return;
      checks.push((async () => {
        for (const header of await response.headersArray()) {
          if (header.name.toLowerCase() === "set-cookie") {
            const value = header.value.match(/^(?:__Host-)?quezo_(?:session|login)=([^;]+)/)?.[1];
            if (value) apps.secrets.add(value);
          }
        }
        if (response.headers()["referrer-policy"] !== "no-referrer") violations.push("Auth route referrer policy");
      })());
    });
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === webOrigin && url.pathname === "/auth/callback") {
        for (const key of ["code", "state"]) {
          const value = url.searchParams.get(key);
          if (value) apps.secrets.add(value);
        }
      }
      checks.push((async () => {
        if (url.origin === apiOrigin) violations.push("Browser called backend directly");
        if (url.origin === webOrigin && await request.headerValue("authorization")) violations.push("Browser exposed authorization");
        const referrer = await request.headerValue("referer");
        if (referrer?.includes("/auth/callback") || referrer?.includes("code=")) violations.push("Callback referrer leaked");
      })());
    });
    await use();
    await Promise.all(checks);
    expect(violations).toEqual([]);
    if (page.url().startsWith(webOrigin) && !page.isClosed()) await privatePage(page, apps);
  }, { auto: true }],
});
export { expect };
