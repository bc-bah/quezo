"use client";

import { useState } from "react";

export function AuthForm({ action }: { action: "login" | "logout" }) {
  const [pending, setPending] = useState(false);
  const signingIn = action === "login";
  return (
    <form action={`/auth/${action}`} method="post" onSubmit={() => setPending(true)}>
      <button type="submit" disabled={pending}>
        {pending
          ? signingIn ? "Signing in..." : "Signing out..."
          : signingIn ? "Sign in with Keycloak" : "Sign out"}
      </button>
      {pending && <p role="status">{signingIn ? "Opening secure sign-in..." : "Invalidating your session..."}</p>}
    </form>
  );
}
