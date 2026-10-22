import "server-only";
import { cookies, headers } from "next/headers";
import { BackendFacade } from "./facade";
import { errorValidator } from "./contracts";
import { failure, unauthenticated, unavailable, WebError } from "./errors";
import { runtime } from "./runtime";
import { requireOrigin } from "./session";

export async function questionClient(write = false) {
  return assessmentClient("author", write);
}

export async function assessmentClient(role: "author" | "learner", write = false) {
  const web = await runtime();
  if (write) {
    const incoming = await headers();
    if (incoming.get("host") !== new URL(web.config.origin).host) {
      throw failure(403, "CSRF_REJECTED", "The request host could not be verified.");
    }
    requireOrigin(new Request(web.config.origin + "/author", {
      method: "POST", headers: incoming,
    }), web.config);
  }
  const id = (await cookies()).get(web.config.sessionCookie)?.value;
  const session = await web.store.session(id);
  if (!session) throw unauthenticated();
  const backend = new BackendFacade(web.config);
  const actor = await backend.actor(session.access_token);
  if (!actor.roles.includes(role)) {
    throw failure(403, "FORBIDDEN", `A ${role} role is required.`);
  }
  return backend.client(session.access_token);
}

export async function apiData<T>(
  operation: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await operation;
  if (!response.ok) {
    if (errorValidator(error)) throw new WebError(response.status, error);
    throw unavailable();
  }
  if (data === undefined) throw unavailable();
  return data;
}
