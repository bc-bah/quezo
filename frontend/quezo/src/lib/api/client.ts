import createClient from "openapi-fetch";
import type { paths } from "./schema";

export function createApiClient(
  baseUrl: string,
  fetch: typeof globalThis.fetch = globalThis.fetch,
) {
  return createClient<paths>({ baseUrl, fetch });
}
