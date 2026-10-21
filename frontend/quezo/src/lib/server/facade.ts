import "server-only";
import { createApiClient } from "../api/client";
import { actorFrom, errorValidator, type Actor } from "./contracts";
import { limits, type WebConfig } from "./config";
import { failure, unavailable, WebError } from "./errors";

export class BackendFacade {
  constructor(
    private readonly config: Pick<WebConfig, "backend">,
    private readonly transport: typeof fetch = fetch,
  ) {}

  // Reused by the generated client once I01 exports /me; never forward browser headers.
  authorizedFetch(accessToken: string): typeof fetch {
    return async (input, init) => {
      const request = new Request(input, init);
      const target = new URL(request.url);
      if (target.origin !== this.config.backend || target.username || target.password) {
        throw failure(500, "INTERNAL_ERROR", "Invalid backend destination.");
      }
      const headers = new Headers(request.headers);
      headers.delete("cookie");
      headers.set("Authorization", `Bearer ${accessToken}`);
      headers.set("Accept", "application/json");
      try {
        return await this.transport(new Request(request, {
          headers, redirect: "error", cache: "no-store",
          signal: AbortSignal.timeout(limits.networkMs),
        }));
      } catch { throw unavailable(); }
    };
  }

  client(accessToken: string) {
    return createApiClient(this.config.backend, this.authorizedFetch(accessToken));
  }

  async actor(accessToken: string): Promise<Actor> {
    // /me is an agreed I01 producer, not yet an OpenAPI operation. Do not fabricate paths.
    const response = await this.authorizedFetch(accessToken)(`${this.config.backend}/api/v1/me`);
    let value: unknown;
    try {
      // Bound untrusted dependency responses before parsing or presenting them.
      const reader = response.body?.getReader();
      if (!reader) throw unavailable();
      let size = 0;
      const chunks: Uint8Array[] = [];
      try {
        for (;;) {
          const { done, value: chunk } = await reader.read();
          if (done) break;
          size += chunk.length;
          if (size > 262144) throw unavailable();
          chunks.push(chunk);
        }
      } finally { await reader.cancel(); }
      value = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch { throw unavailable(); }
    if (!response.ok) {
      if (errorValidator(value)) throw new WebError(response.status, value);
      throw unavailable();
    }
    return actorFrom(value);
  }
}
