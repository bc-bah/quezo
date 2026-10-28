"use client";

import { useRef, useState, type FormEvent } from "react";
import { startAttempt } from "./actions";
import { QuizError } from "../author/quizzes/composition";
import type { components } from "../../lib/api/schema";
import { TimingControls, type TimingChoice } from "../../lib/timing-controls";

export function StartAttempt({ assignment }: { assignment: components["schemas"]["Assignment"] }) {
  const [key] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [choice, setChoice] = useState<TimingChoice>("standard");
  const [duration, setDuration] = useState((assignment.durationSeconds ?? 60) * 10);
  const command = useRef<components["schemas"]["StartCommand"] | null>(null);
  const [error, setError] = useState<components["schemas"]["ErrorEnvelope"] | string | null>(null);
  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true); setError(null);
    command.current ??= { timingChoice: choice,
      adjustedDurationSeconds: choice === "adjusted" ? duration : null };
    try {
      const result = await startAttempt(assignment.id, key, command.current);
      if (!result.ok) { setError(result.error); return; }
      // A document boundary lets native back/refresh navigation warn about unsaved answers.
      window.location.assign(`/learner/attempts/${result.value.id}`);
    } catch { setError("Start could not be confirmed. Retry here with the same command or reload your assignments."); }
    finally { setPending(false); }
  }
  return <>
    {["available", "in_progress", "completed_remaining"].includes(assignment.state) &&
      <form onSubmit={start}>
        {!assignment.activeAttemptId && <TimingControls authoredDuration={assignment.durationSeconds}
          choice={choice} onChoice={setChoice} duration={duration} onDuration={setDuration}
          disabled={pending || command.current !== null} />}
        {command.current !== null && !pending && <p>Your dispatched timing choice is retained for safe retry.
          Reload assignments to reconcile before choosing differently.</p>}
        <button disabled={pending}>{assignment.activeAttemptId ? "Resume attempt" : "Start attempt"}</button>
      </form>}
    <QuizError error={error} />
    <p role="status">{pending ? "Opening attempt..." : ""}</p>
  </>;
}
