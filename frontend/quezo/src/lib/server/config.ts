import "server-only";

export interface WebConfig {
  origin: string;
  issuer: string;
  clientId: string;
  clientSecret: string;
  audience: string;
  backend: string;
  databaseUrl: string;
  local: boolean;
  redirectUri: string;
  sessionCookie: string;
  loginCookie: string;
}

export const limits = Object.freeze({
  loginSeconds: 300,
  idleSeconds: 1800,
  sessionSeconds: 28800,
  networkMs: 5000,
  poolMax: 5,
  poolWaitingMax: 10,
});

export function readConfig(env: Record<string, string | undefined> = process.env): WebConfig {
  function required(key: string): string {
    const value = env[key];
    if (!value?.trim()) throw new Error(`Missing web configuration: ${key}`);
    return value;
  }
  const environment = required("QUEZO_WEB_ENV");
  if (!["local", "shared"].includes(environment)) throw new Error("Invalid QUEZO_WEB_ENV");
  const local = environment === "local";
  function url(key: string, originOnly: boolean): URL {
    let value: URL;
    try { value = new URL(required(key)); } catch { throw new Error(`Invalid ${key}`); }
    const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(value.hostname);
    if (
      !(value.protocol === "https:" || (local && loopback && value.protocol === "http:"))
      || value.username || value.password || value.search || value.hash
      || (originOnly && value.pathname !== "/")
      || (local && !loopback)
    ) throw new Error(`Invalid ${key}`);
    return value;
  }
  const origin = url("QUEZO_WEB_ORIGIN", true).origin;
  const issuer = url("QUEZO_OIDC_ISSUER", false).href.replace(/\/$/, "");
  const backend = url("QUEZO_BACKEND_ORIGIN", true).origin;
  const databaseUrl = required("QUEZO_WEB_DATABASE_URL");
  let database: URL;
  try { database = new URL(databaseUrl); } catch { throw new Error("Invalid web database configuration"); }
  if (
    !["postgres:", "postgresql:"].includes(database.protocol)
    || database.username !== "quezo_web" || !database.password
    || !database.hostname || database.pathname.length < 2
    || database.search || database.hash
    || (local && !["localhost", "127.0.0.1", "[::1]"].includes(database.hostname))
    || (!local && database.protocol !== "postgresql:")
  ) throw new Error("Invalid web database configuration");
  const audience = required("QUEZO_API_AUDIENCE");
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(audience)) throw new Error("Invalid QUEZO_API_AUDIENCE");
  return {
    origin, issuer, backend, databaseUrl, local,
    clientId: required("QUEZO_OIDC_CLIENT_ID"),
    clientSecret: required("QUEZO_OIDC_CLIENT_SECRET"),
    audience,
    redirectUri: `${origin}/auth/callback`,
    sessionCookie: local ? "quezo_session" : "__Host-quezo_session",
    loginCookie: local ? "quezo_login" : "__Host-quezo_login",
  };
}
