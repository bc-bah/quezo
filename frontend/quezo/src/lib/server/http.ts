import "server-only";
import { NextResponse, type NextRequest } from "next/server";
import { limits, type WebConfig } from "./config";
import { failure, publicError } from "./errors";
import { runtime } from "./runtime";

const privateHeaders = { "Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer" };

export function canonicalRequest(request: NextRequest, config: WebConfig): Request {
  // Next may use its internal bind origin in request.url. Trust only configured
  // public origin after checking Host; never derive redirects from forwarding headers.
  if (request.headers.get("host") !== new URL(config.origin).host) {
    throw failure(400, "UNAUTHENTICATED", "The request host does not match the configured web origin.");
  }
  return new Request(`${config.origin}${request.nextUrl.pathname}${request.nextUrl.search}`, {
    method: request.method, headers: request.headers,
  });
}

export function setCookie(
  response: NextResponse, config: WebConfig, kind: "session" | "login", value: string,
) {
  response.cookies.set(kind === "session" ? config.sessionCookie : config.loginCookie, value, {
    httpOnly: true, secure: !config.local, sameSite: "lax", path: "/",
    maxAge: value ? (kind === "session" ? limits.sessionSeconds : limits.loginSeconds) : 0,
  });
}

export async function authRoute(kind: "login" | "callback" | "logout", request: NextRequest) {
  try {
    const web = await runtime();
    const canonical = canonicalRequest(request, web.config);
    const session = request.cookies.get(web.config.sessionCookie)?.value;
    const login = request.cookies.get(web.config.loginCookie)?.value;
    const home = new URL("/", web.config.origin);
    if (kind === "login") {
      const result = await web.login(canonical, login, session);
      const response = NextResponse.redirect(result.url, { status: 303, headers: privateHeaders });
      setCookie(response, web.config, "login", result.id);
      setCookie(response, web.config, "session", "");
      return response;
    }
    if (kind === "callback") {
      const id = await web.callback(canonical, login);
      const response = NextResponse.redirect(home, { status: 303, headers: privateHeaders });
      setCookie(response, web.config, "session", id);
      setCookie(response, web.config, "login", "");
      return response;
    }
    await web.logout(canonical, session, login);
    const response = NextResponse.redirect(home, { status: 303, headers: privateHeaders });
    setCookie(response, web.config, "session", "");
    setCookie(response, web.config, "login", "");
    return response;
  } catch (error) {
    const safe = publicError(error);
    if (request.headers.get("accept")?.includes("text/html")) {
      const escape = (value: string) => value.replace(/[&<>"']/g, (char) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]!,
      );
      return new NextResponse(
        `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Quezo - Sign-in error</title></head>`
        + `<body><main><h1>Request not completed</h1><p role="alert">${escape(safe.envelope.message)}</p>`
        + `<p>Reference: ${escape(safe.envelope.requestId)}</p><a href="/">Return to Quezo</a></main></body></html>`,
        { status: safe.status, headers: {
          ...privateHeaders, "Content-Type": "text/html; charset=utf-8",
          "X-Request-ID": safe.envelope.requestId,
          "Content-Security-Policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        } },
      );
    }
    // Safe envelope, never raw provider errors or callback query values.
    return NextResponse.json(safe.envelope, {
      status: safe.status, headers: { ...privateHeaders, "X-Request-ID": safe.envelope.requestId },
    });
  }
}
