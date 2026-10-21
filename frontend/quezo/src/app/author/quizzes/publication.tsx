"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../../lib/api/schema";
import { createRevision, publishQuiz } from "./actions";
import { QuizError } from "./composition";

type S = components["schemas"];

export function Publication({ quiz }: { quiz: S["Quiz"] }) {
  const router = useRouter();
  const [key] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
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
  return <section>
    <h2>Publication</h2>
    <p>State: {quiz.state}. {quiz.hasDraft ? "An editable draft exists." : "No revision draft."}</p>
    {quiz.publishedVersionId && <a href={`/author/quizzes/${quiz.id}/versions/${quiz.publishedVersionId}`}>View published version</a>}
    {quiz.hasDraft ? <>
      <p>Only the saved draft revision {quiz.draftRevision} will be published. Unsaved form edits are not included.</p>
      <a href={`/author/quizzes/${quiz.id}/preview`}>Preview saved draft</a>
      <label><input type="checkbox" checked={confirmed} disabled={pending}
        onChange={(event) => setConfirmed(event.target.checked)} /> I confirm publication of this saved draft</label>
      <button type="button" disabled={pending || !confirmed || ack !== null} onClick={publish}>Publish saved draft</button>
    </> : quiz.state === "published" &&
      <button type="button" disabled={pending} onClick={revise}>Create new revision draft</button>}
    <QuizError error={error} />
    <p role="status">{pending ? "Working..." : ack ? "Publication confirmed." : ""}</p>
  </section>;
}
