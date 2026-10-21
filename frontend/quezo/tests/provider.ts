import { createServer } from "node:http";
import { createHash, generateKeyPairSync, randomUUID, sign } from "node:crypto";
import type { AddressInfo } from "node:net";
import { actor } from "./fixtures";

// Controlled local protocol peer, never imported by runtime code. I02 uses real Keycloak.
export async function provider() {
  const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwk = { ...publicKey.export({ format: "jwk" }), kid: "synthetic", alg: "RS256", use: "sig" };
  let origin = "";
  let actorMode: "active" | "disabled" | "empty" | "outage" | "missing" | "unauthenticated" = "active";
  let identityDown = false;
  const grants = new Map<string, { authorization: URL; defect?: string }>();
  const server = createServer(async (request, response) => {
    const url = new URL(request.url!, origin);
    const json = (value: unknown, status = 200) => {
      response.writeHead(status, { "Content-Type": "application/json" });
      response.end(JSON.stringify(value));
    };
    if (url.pathname === "/api/v1/me") {
      if (request.headers.authorization !== "Bearer synthetic-access-token") {
        json({ code: "UNAUTHENTICATED", message: "Sign in again.", requestId: actor.userId }, 401);
      } else if (actorMode === "outage") {
        json({ code: "DEPENDENCY_UNAVAILABLE", message: "A required service is unavailable.", requestId: actor.userId }, 503);
      } else if (actorMode === "missing") {
        json({ code: "NOT_FOUND", message: "The requested resource was not found.", requestId: actor.userId }, 404);
      } else if (actorMode === "unauthenticated") {
        json({ code: "UNAUTHENTICATED", message: "Sign in again.", requestId: actor.userId }, 401);
      } else {
        json({ ...actor, status: actorMode === "disabled" ? "disabled" : "active", roles: actorMode === "empty" ? [] : actor.roles });
      }
      return;
    }
    if (identityDown) { json({ error: "temporarily_unavailable" }, 503); return; }
    if (url.pathname === "/.well-known/openid-configuration") {
      json({
        issuer: origin, authorization_endpoint: `${origin}/authorize`,
        token_endpoint: `${origin}/token`, jwks_uri: `${origin}/jwks`,
        response_types_supported: ["code"], subject_types_supported: ["public"],
        id_token_signing_alg_values_supported: ["RS256"],
        token_endpoint_auth_methods_supported: ["client_secret_post"],
        code_challenge_methods_supported: ["S256"],
      });
    } else if (url.pathname === "/jwks") {
      json({ keys: [jwk] });
    } else if (url.pathname === "/token") {
      let body = "";
      for await (const chunk of request) body += String(chunk);
      const params = new URLSearchParams(body);
      const code = params.get("code") ?? "";
      const grant = grants.get(code);
      grants.delete(code);
      if (!grant
        || params.get("client_secret") !== "synthetic-client-secret"
        || params.get("client_id") !== "quezo-web"
        || params.get("grant_type") !== "authorization_code"
        || params.get("redirect_uri") !== grant.authorization.searchParams.get("redirect_uri")
        || createHash("sha256").update(params.get("code_verifier") ?? "").digest("base64url")
          !== grant.authorization.searchParams.get("code_challenge")) {
        json({ error: "invalid_grant" }, 400);
        return;
      }
      const now = Math.floor(Date.now() / 1000);
      const claims = {
        iss: grant.defect === "issuer" ? "https://wrong.invalid" : origin,
        sub: "synthetic-subject",
        aud: grant.defect === "audience" ? "wrong-client" : "quezo-web",
        iat: now, exp: now + (grant.defect === "expiry" ? -300 : 3600),
        nonce: grant.defect === "nonce" ? "wrong-nonce" : grant.authorization.searchParams.get("nonce"),
      };
      const header = Buffer.from(JSON.stringify({ alg: "RS256", kid: "synthetic" })).toString("base64url");
      const payload = Buffer.from(JSON.stringify(claims)).toString("base64url");
      const signature = sign("RSA-SHA256", Buffer.from(`${header}.${payload}`), privateKey).toString("base64url");
      json({
        access_token: "synthetic-access-token", token_type: "Bearer", expires_in: 3600,
        refresh_token: "synthetic-refresh-token",
        id_token: `${header}.${payload}.${grant.defect === "signature" ? signature.split("").reverse().join("") : signature}`,
      });
    } else { json({ error: "not_found" }, 404); }
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  origin = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  return {
    origin,
    setActor(mode: typeof actorMode) { actorMode = mode; },
    setIdentityDown(down: boolean) { identityDown = down; },
    callback(authorization: URL, defect?: string) {
      const code = randomUUID();
      grants.set(code, { authorization, ...(defect ? { defect } : {}) });
      const url = new URL(authorization.searchParams.get("redirect_uri")!);
      url.searchParams.set("code", code);
      url.searchParams.set("state", authorization.searchParams.get("state")!);
      url.searchParams.set("iss", origin);
      return new Request(url);
    },
    async close() {
      server.closeAllConnections();
      await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    },
  };
}
