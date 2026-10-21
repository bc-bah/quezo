import type { SessionView } from "../lib/server/session";
import { AuthForm } from "./auth-form";

const workspaces = {
  administrator: "Account administration",
  author: "Author workspace",
  learner: "Learner workspace",
} as const;

export function SessionShell({ view }: { view: SessionView }) {
  return (
    <>
      <nav aria-label="Main navigation">
        <a href="/">Home</a>
        {view.state === "signed-in" && view.actor.roles.map((role, index) => (
          view.actor.roles.indexOf(role) === index
            ? <a key={role} href={`#${role}`}>{workspaces[role]}</a> : null
        ))}
      </nav>
      <main id="main" tabIndex={-1}>
        <h1>Quezo</h1>
        <div role={view.state === "error" ? "alert" : "status"}>
          {view.state === "signed-out" && <p>You are signed out.</p>}
          {view.state === "expired" && <p>Your session expired. Sign in again.</p>}
          {view.state === "disabled" && <p>Your application access is disabled. Contact your administrator.</p>}
          {view.state === "error" && (
            <>
              <p>{view.error.message}</p>
              <p>Reference: {view.error.requestId}</p>
              <a href="/">Try again</a>
            </>
          )}
          {view.state === "signed-in" && <p>You are signed in.</p>}
        </div>
        {view.state !== "signed-in" && view.state !== "error" && (
          <AuthForm action="login" />
        )}
        {(view.state === "signed-in" || view.state === "error") && (
          <AuthForm action="logout" />
        )}
        {view.state === "signed-in" && (
          <>
            {view.actor.roles.length === 0 && <p>No application role is assigned. Contact your administrator.</p>}
            {Object.entries(workspaces).map(([role, label]) =>
              view.actor.roles.some((assigned) => assigned === role) && (
                <section key={role} id={role} tabIndex={-1} aria-label={label}>
                  <h2>{label}</h2>
                  {role === "author"
                    ? <p><a href="/author">Manage question banks</a></p>
                    : <p>This workspace is not implemented yet.</p>}
                </section>
              ),
            )}
          </>
        )}
        <p>Authors can manage versioned objective questions. Quiz delivery is not available yet.</p>
      </main>
    </>
  );
}
