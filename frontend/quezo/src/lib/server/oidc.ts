import "server-only";
import * as oidc from "openid-client";
import { limits, type WebConfig } from "./config";
import { failure, unavailable } from "./errors";
import type { LoginTransaction } from "./store";

export class IdentityProvider {
  private configuration: Promise<oidc.Configuration> | undefined;
  constructor(private readonly settings: WebConfig) {}

  private async discover(): Promise<oidc.Configuration> {
    if (!this.configuration) {
      this.configuration = oidc.discovery(
        new URL(this.settings.issuer),
        this.settings.clientId,
        { client_secret: this.settings.clientSecret, id_token_signed_response_alg: "RS256" },
        oidc.ClientSecretPost(this.settings.clientSecret),
        {
          timeout: limits.networkMs / 1000,
          execute: this.settings.local
            ? [oidc.allowInsecureRequests, oidc.enableNonRepudiationChecks]
            : [oidc.enableNonRepudiationChecks],
        },
      ).catch(() => {
        this.configuration = undefined;
        throw unavailable();
      });
    }
    return this.configuration;
  }

  async authorization(): Promise<{ url: URL; transaction: LoginTransaction }> {
    const configuration = await this.discover();
    const verifier = oidc.randomPKCECodeVerifier();
    const transaction = {
      state: oidc.randomState(), nonce: oidc.randomNonce(), verifier,
    };
    const url = oidc.buildAuthorizationUrl(configuration, {
      redirect_uri: this.settings.redirectUri,
      scope: `openid ${this.settings.audience}`,
      response_type: "code",
      code_challenge_method: "S256",
      code_challenge: await oidc.calculatePKCECodeChallenge(verifier),
      state: transaction.state,
      nonce: transaction.nonce,
    });
    return { url, transaction };
  }

  async exchange(url: URL, transaction: LoginTransaction) {
    const configuration = await this.discover();
    let tokens: oidc.TokenEndpointResponse & oidc.TokenEndpointResponseHelpers;
    try {
      tokens = await oidc.authorizationCodeGrant(configuration, url, {
        pkceCodeVerifier: transaction.verifier,
        expectedState: transaction.state,
        expectedNonce: transaction.nonce,
        idTokenExpected: true,
      });
    } catch (error) {
      // Protocol denials are distinct from transport/dependency failures; no raw provider text.
      if ((error instanceof oidc.ResponseBodyError
        && (error.status >= 500 || error.status === 429 || error.error !== "invalid_grant"))
        || (error instanceof oidc.AuthorizationResponseError
          && ["server_error", "temporarily_unavailable"].includes(error.error))
        || (error instanceof oidc.ClientError && [
          "OAUTH_RESPONSE_IS_NOT_CONFORM", "OAUTH_RESPONSE_IS_NOT_JSON",
          "OAUTH_PARSE_ERROR", "OAUTH_TIMEOUT", "OAUTH_ABORT",
          "OAUTH_HTTP_REQUEST_FORBIDDEN", "OAUTH_REQUEST_PROTOCOL_FORBIDDEN",
        ].includes(error.code ?? ""))) {
        throw unavailable();
      }
      if (error instanceof oidc.AuthorizationResponseError
        || error instanceof oidc.ResponseBodyError
        || (error instanceof oidc.ClientError && error.code?.startsWith("OAUTH_"))) {
        throw failure(401, "UNAUTHENTICATED", "Sign-in could not be verified. Start again.");
      }
      throw unavailable();
    }
    if (!Number.isFinite(tokens.expires_in) || !tokens.expires_in
      || tokens.expires_in <= 0 || tokens.token_type.toLowerCase() !== "bearer"
      || !tokens.access_token || tokens.access_token.length > 32768) {
      throw failure(401, "UNAUTHENTICATED", "Sign-in returned an unusable token. Start again.");
    }
    return {
      accessToken: tokens.access_token,
      expiresAt: new Date(Date.now() + tokens.expires_in * 1000),
    };
  }
}
