"use client";

import { useState } from "react";
import { startAttempt } from "./actions";
import { QuizError } from "../author/quizzes/composition";
import type { components } from "../../lib/api/schema";

export function StartAttempt({ assignment }: { assignment: components["schemas"]["Assignment"] }) {
  const [key] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<components["schemas"]["ErrorEnvelope"] | string | null>(null);
  async function start() {
    setPending(true); setError(null);
    try {
      const result = await startAttempt(assignment.id, key);
      if (!result.ok) { setError(result.error); return; }
      // A document boundary lets native back/refresh navigation warn about unsaved answers.
      window.location.assign(`/learner/attempts/${result.value.id}`);
    } catch { setError("Start could not be confirmed. Retry here with the same command or reload your assignments."); }
    finally { setPending(false); }
  }
  return <>
    {["available", "in_progress", "completed_remaining"].includes(assignment.state) &&
      <button disabled={pending} onClick={start}>{assignment.activeAttemptId ? "Resume attempt" : "Start attempt"}</button>}
    <QuizError error={error} />
    <p role="status">{pending ? "Opening attempt..." : ""}</p>
  </>;
}
