import "server-only";
import { cookies, headers } from "next/headers";
import { BackendFacade } from "./facade";
import { failure, unauthenticated } from "./errors";
import { runtime } from "./runtime";
import { requireOrigin } from "./session";

export async function accountClient(write = false) {
  const web = await runtime();
  if (write) {
    const incoming = await headers();
    if (incoming.get("host") !== new URL(web.config.origin).host) {
      throw failure(403, "CSRF_REJECTED", "The request host could not be verified.");
    }
    requireOrigin(new Request(`${web.config.origin}/admin/accounts`, {
      method: "POST", headers: incoming,
    }), web.config);
  }
  const id = (await cookies()).get(web.config.sessionCookie)?.value;
  const session = await web.store.session(id);
  if (!session) throw unauthenticated();
  const backend = new BackendFacade(web.config);
  const actor = await backend.actor(session.access_token);
  if (!actor.roles.includes("administrator")) {
    throw failure(403, "FORBIDDEN", "An administrator role is required.");
  }
  return backend.client(session.access_token);
}
