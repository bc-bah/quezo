"use client";

import { useState } from "react";
import type { components } from "../../../lib/api/schema";
import { assignLearner, eligibleLearners } from "./actions";
import { QuizError } from "./composition";

type S = components["schemas"];

export function AssignLearner({ quizId, versionId, initial }: {
  quizId: string; versionId: string; initial: S["Page_EligibleLearner_"];
}) {
  const [page, setPage] = useState(initial);
  const [learnerId, setLearnerId] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<S["ErrorEnvelope"] | string | null>(null);
  const [assignment, setAssignment] = useState<S["Assignment"] | null>(null);
  async function assign() {
    setPending(true); setError(null); setAssignment(null);
    try {
      const result = await assignLearner({ quizId, versionId, learnerId });
      if (result.ok) setAssignment(result.value);
      else setError(result.error);
    } catch { setError("Assignment could not be confirmed. Retry the same learner and version safely."); }
    finally { setPending(false); }
  }
  async function next() {
    setPending(true); setError(null);
    try {
      const result = await eligibleLearners(page.nextCursor);
      if (result.ok) { setPage(result.value); setLearnerId(""); }
      else setError(result.error);
    } catch { setError("Learners could not be loaded. Try again."); }
    finally { setPending(false); }
  }
  return <section>
    <h2>Assign this published version</h2>
    <p>Select a specific active learner by application ID. Duplicate assignment preserves their allowance.</p>
    <label>Active learner
      <select value={learnerId} disabled={pending} onChange={(event) => setLearnerId(event.target.value)}>
        <option value="">Select learner</option>
        {page.items.map((learner) => <option key={learner.userId} value={learner.userId}>{learner.userId}</option>)}
      </select>
    </label>
    {page.nextCursor && <button disabled={pending} onClick={next}>Next learners</button>}
    <button disabled={pending || !learnerId} onClick={assign}>Assign learner</button>
    <QuizError error={error} />
    <p role="status">{pending ? "Working..." : assignment ? `Assignment confirmed: ${assignment.id}` : ""}</p>
  </section>;
}
