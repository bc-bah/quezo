import "server-only";
import type { Actor } from "./contracts";
import type { WebConfig } from "./config";
import { failure, publicError, unauthenticated, type ErrorEnvelope } from "./errors";
import { BackendFacade } from "./facade";
import { IdentityProvider } from "./oidc";
import { SessionStore, validOpaque } from "./store";

export type SessionView =
  | { state: "signed-out" | "expired" }
  | { state: "signed-in"; actor: Actor }
  | { state: "disabled" }
  | { state: "error"; error: ErrorEnvelope };

export function requireOrigin(request: Request, config: Pick<WebConfig, "origin">): void {
  if (request.headers.get("origin") !== config.origin
    || !["same-origin", null].includes(request.headers.get("sec-fetch-site"))) {
    throw failure(403, "CSRF_REJECTED", "This request must originate from the Quezo page.");
  }
  if (new URL(request.url).origin !== config.origin) {
    throw failure(403, "CSRF_REJECTED", "The web server origin does not match its configured origin.");
  }
}

export class WebSession {
  constructor(
    readonly config: WebConfig,
    readonly store: SessionStore,
    private readonly identity = new IdentityProvider(config),
    private readonly backend = new BackendFacade(config),
  ) {}

  async login(request: Request, oldLogin?: string, oldSession?: string) {
    requireOrigin(request, this.config);
    await this.store.prune();
    const { url, transaction } = await this.identity.authorization();
    const id = await this.store.beginLogin(transaction, oldLogin, oldSession);
    return { url, id };
  }

  async callback(request: Request, loginId: string | undefined): Promise<string> {
    const url = new URL(request.url);
    if (`${url.origin}${url.pathname}` !== this.config.redirectUri
      || url.hash || url.username || url.password) {
      throw failure(400, "UNAUTHENTICATED", "Invalid sign-in callback.");
    }
    const transaction = await this.store.consumeLogin(loginId);
    if (!transaction || !validOpaque(loginId)) throw unauthenticated();
    const tokens = await this.identity.exchange(url, transaction);
    // No session is issued until the real backend accepts the new identity.
    const actor = await this.backend.actor(tokens.accessToken);
    if (actor.status !== "active") {
      throw failure(403, "ACCOUNT_DISABLED", "Your application access is disabled.");
    }
    return this.store.createSession(tokens.accessToken, tokens.expiresAt, loginId);
  }

  async view(id: string | undefined): Promise<SessionView> {
    if (!id) return { state: "signed-out" };
    try {
      const session = await this.store.session(id);
      if (!session) return { state: "expired" };
      const actor = await this.backend.actor(session.access_token);
      if (actor.status === "disabled") {
        await this.store.logout(id);
        return { state: "disabled" };
      }
      return { state: "signed-in", actor };
    } catch (error) {
      const safe = publicError(error);
      if (safe.envelope.code === "UNAUTHENTICATED"
        || safe.envelope.code === "ACCOUNT_DISABLED") {
        // Invalidation failures must remain outages, not success-shaped status.
        try { await this.store.logout(id); }
        catch (invalidationError) {
          return { state: "error", error: publicError(invalidationError).envelope };
        }
        return { state: safe.envelope.code === "ACCOUNT_DISABLED" ? "disabled" : "expired" };
      }
      return { state: "error", error: safe.envelope };
    }
  }

  async logout(request: Request, id: string | undefined, loginId?: string): Promise<void> {
    requireOrigin(request, this.config);
    await this.store.logout(id, loginId);
  }
}
