import { readConfig } from "../src/lib/server/config";
import { actorFrom } from "../src/lib/server/contracts";

export function config() {
  return readConfig({
    QUEZO_WEB_ENV: "local",
    QUEZO_WEB_ORIGIN: "http://localhost:3000",
    QUEZO_BACKEND_ORIGIN: "http://127.0.0.1:4000",
    QUEZO_OIDC_ISSUER: "http://127.0.0.1:8080/realms/quezo-local",
    QUEZO_OIDC_CLIENT_ID: "quezo-web",
    QUEZO_OIDC_CLIENT_SECRET: "synthetic-client-secret",
    QUEZO_API_AUDIENCE: "quezo-api",
    QUEZO_WEB_DATABASE_URL: process.env.QUEZO_WEB_TEST_URL
      ?? "postgresql://quezo_web:synthetic@127.0.0.1:1/quezo_test",
  });
}

export const actor = actorFrom({
  userId: "b852a646-70ed-4ab9-aae4-d7fc2e0ca313",
  roles: ["author", "learner"],
  status: "active",
});
