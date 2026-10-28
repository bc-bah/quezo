import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { SessionShell } from "../src/app/session-shell";
import type { components } from "../src/lib/api/schema";

const actor: components["schemas"]["Actor"] = {
  userId: "b852a646-70ed-4ab9-aae4-d7fc2e0ca313", roles: [], status: "active",
};

test("navigation uses native keyboard-operable links/buttons and focusable destinations", () => {
  for (const role of ["administrator", "author", "learner"] as const) {
    const html = renderToStaticMarkup(<SessionShell view={{ state: "signed-in", actor: { ...actor, roles: [role] } }} />);
    assert.match(html, /aria-label="Main navigation"/);
    assert.ok(html.includes(`href="#${role}"`));
    assert.ok(html.includes(`id="${role}" tabindex="-1"`));
    if (role === "administrator") assert.match(html, /href="\/admin\/accounts">Manage accounts/);
    assert.match(html, /<button type="submit">Sign out<\/button>/);
    assert.doesNotMatch(html, /onclick|tabindex="[1-9]/);
    for (const other of ["administrator", "author", "learner"].filter((value) => value !== role)) {
      assert.ok(!html.includes(`href="#${other}"`));
    }
  }
  const css = readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8");
  assert.match(css, /:focus-visible/);
  assert.match(css, /flex-wrap: wrap/);
  const layout = readFileSync(new URL("../src/app/layout.tsx", import.meta.url), "utf8");
  assert.match(layout, /href="#main"/);
});

test("combined/empty roles and signed-out, expired, disabled and errors are explicit without identity leakage", () => {
  const empty = renderToStaticMarkup(<SessionShell view={{ state: "signed-in", actor }} />);
  assert.match(empty, /No application role is assigned/);
  const combined = renderToStaticMarkup(<SessionShell view={{
    state: "signed-in", actor: { ...actor, roles: ["author", "learner"] },
  }} />);
  assert.match(combined, /href="#author"/);
  assert.match(combined, /href="#learner"/);
  assert.doesNotMatch(combined, /b852a646|access_token|localStorage/);
  for (const state of ["signed-out", "expired", "disabled"] as const) {
    const html = renderToStaticMarkup(<SessionShell view={{ state }} />);
    assert.match(html, /role="status"/);
    assert.match(html, /method="post"/);
    assert.doesNotMatch(html, /href="#author"/);
  }
  const html = renderToStaticMarkup(<SessionShell view={{ state: "error", error: {
    code: "DEPENDENCY_UNAVAILABLE", message: "Service unavailable.", requestId: actor.userId,
  } }} />);
  assert.match(html, /role="alert"/);
  assert.match(html, /Try again/);
  assert.doesNotMatch(html, /You are signed in/);
});
