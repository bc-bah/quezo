"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../../lib/api/schema";
import { createRevision, publishQuiz, transitionQuiz } from "./actions";
import { QuizError } from "./composition";

type S = components["schemas"];

export function Publication({ quiz }: { quiz: S["Quiz"] }) {
  const router = useRouter();
  const [key] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [lifecycleConfirmed, setLifecycleConfirmed] = useState(false);
  const [error, setError] = useState<S["ErrorEnvelope"] | string | null>(null);
  const [ack, setAck] = useState<S["PublishAcknowledgement"] | null>(null);
  async function publish() {
    setPending(true); setError(null);
    try {
      const result = await publishQuiz(quiz.id, quiz.draftRevision, key);
      if (!result.ok) { setError(result.error); return; }
      setAck(result.value); router.refresh();
    } catch { setError("Publication could not be confirmed. Retry here with the same command, or reload to inspect saved state."); }
    finally { setPending(false); }
  }
  async function revise() {
    setPending(true); setError(null);
    try {
      const result = await createRevision(quiz.id, quiz.draftRevision);
      if (!result.ok) { setError(result.error); return; }
      router.refresh();
    } catch { setError("New draft creation could not be confirmed. Reload to inspect saved state before retrying."); }
    finally { setPending(false); }
  }
  async function transition(target: "close" | "archive") {
    setPending(true); setError(null);
    try {
      const result = await transitionQuiz(quiz.id, quiz.draftRevision, target);
      if (!result.ok) { setError(result.error); return; }
      setLifecycleConfirmed(false); router.refresh();
    } catch { setError("The lifecycle change could not be confirmed. Reload to inspect saved state before retrying."); }
    finally { setPending(false); }
  }
  return <section>
    <h2>Publication</h2>
    <p>State: {quiz.state}. {quiz.hasDraft ? "An editable draft exists." : "No revision draft."}</p>
    {quiz.publishedVersionId && <a href={`/author/quizzes/${quiz.id}/versions/${quiz.publishedVersionId}`}>View published version</a>}
    {quiz.hasDraft && (quiz.state === "draft" || quiz.state === "published") ? <>
      <p>Only the saved draft revision {quiz.draftRevision} will be published. Unsaved form edits are not included.</p>
      <a href={`/author/quizzes/${quiz.id}/preview`}>Preview saved draft</a>
      <label><input type="checkbox" checked={confirmed} disabled={pending}
        onChange={(event) => setConfirmed(event.target.checked)} /> I confirm publication of this saved draft</label>
      <button type="button" disabled={pending || !confirmed || ack !== null} onClick={publish}>Publish saved draft</button>
    </> : quiz.state === "published" &&
      <button type="button" disabled={pending} onClick={revise}>Create new revision draft</button>}
    {quiz.state === "closed" && <p>This quiz is closed. New starts are blocked; active attempts keep their fixed deadlines.
      A pending revision is frozen and cannot be edited or published. Reopening is not supported.</p>}
    {quiz.state === "archived" ? <p>This quiz is archived and read-only. Publications, assignments, attempts and grades are retained.</p> : <>
      <p>Closing blocks new starts across every publication, but does not end active attempts.
        Archive is allowed for an unpublished draft, or a closed quiz with no in-progress attempts; all history is retained.</p>
      <label><input type="checkbox" checked={lifecycleConfirmed} disabled={pending}
        onChange={(event) => setLifecycleConfirmed(event.target.checked)} /> I confirm this lifecycle change and retained history</label>
      {quiz.state === "published"
        ? <button type="button" disabled={pending || !lifecycleConfirmed} onClick={() => transition("close")}>Close quiz</button>
        : <button type="button" disabled={pending || !lifecycleConfirmed} onClick={() => transition("archive")}>Archive quiz</button>}
    </>}
    <QuizError error={error} />
    <p role="status">{pending ? "Working..." : ack ? "Publication confirmed." : ""}</p>
  </section>;
}
