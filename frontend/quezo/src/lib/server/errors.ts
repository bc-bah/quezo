import "server-only";
import { randomUUID } from "node:crypto";
import type { components } from "../api/schema";

export type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];
const webError = Symbol.for("quezo.web-error");

export class WebError extends Error {
  readonly [webError] = true;
  constructor(
    readonly status: number,
    readonly envelope: ErrorEnvelope,
  ) {
    super(envelope.code);
  }
}

export function isWebError(error: unknown): error is WebError {
  // Next instrumentation and routes can load distinct module copies in one process.
  return typeof error === "object" && error !== null
    && webError in error && error[webError] === true;
}

export function failure(
  status: number,
  code: ErrorEnvelope["code"],
  message: string,
): WebError {
  return new WebError(status, { code, message, requestId: randomUUID() });
}

export function publicError(error: unknown): WebError {
  const safe = isWebError(error)
    ? error
    : failure(500, "INTERNAL_ERROR", "The request could not be completed.");
  // Never log exception text, URLs, cookies, headers or upstream bodies.
  console.error(JSON.stringify({
    event: "web_request_failed", code: safe.envelope.code,
    requestId: safe.envelope.requestId,
  }));
  return safe;
}

export function unavailable(): WebError {
  return failure(503, "DEPENDENCY_UNAVAILABLE", "A required service is unavailable. Try again.");
}

export function unauthenticated(): WebError {
  return failure(401, "UNAUTHENTICATED", "Your session expired. Sign in again.");
}
