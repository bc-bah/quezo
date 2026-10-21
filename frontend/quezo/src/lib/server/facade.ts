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

  // Never forward browser headers; bound success and error bodies before client parsing.
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
        const response = await this.transport(new Request(request, {
          headers, redirect: "error", cache: "no-store",
          signal: AbortSignal.timeout(limits.networkMs),
        }));
        if (!response.body) return response;
        const reader = response.body.getReader();
        let size = 0;
        const chunks: Uint8Array[] = [];
        try {
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            size += value.length;
            if (size > 262144) throw unavailable();
            chunks.push(value);
          }
        } finally { await reader.cancel(); }
        return new Response(Buffer.concat(chunks), {
          status: response.status, statusText: response.statusText, headers: response.headers,
        });
      } catch { throw unavailable(); }
    };
  }

  client(accessToken: string) {
    return createApiClient(this.config.backend, this.authorizedFetch(accessToken));
  }

  async actor(accessToken: string): Promise<Actor> {
    const { data, error, response } = await this.client(accessToken).GET("/api/v1/me")
      .catch(() => { throw unavailable(); });
    if (!response.ok) {
      if (errorValidator(error)) throw new WebError(response.status, error);
      throw unavailable();
    }
    return actorFrom(data);
  }
}
