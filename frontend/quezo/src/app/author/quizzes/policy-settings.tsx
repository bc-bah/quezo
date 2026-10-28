"use client";

import type { components } from "../../../lib/api/schema";
import { useEffect, useState } from "react";

type Policy = components["schemas"]["QuizPolicy"];
type Release = NonNullable<Policy["scoreRelease"]>;

export const demoPolicy: Policy = {
  durationSeconds: null, attemptLimit: 1, availabilityStart: null, availabilityEnd: null,
  timeZone: "UTC", randomizeQuestions: false, randomizeOptions: false,
  scoreRelease: "after_finalization", answerKeyRelease: "never", explanationRelease: "never",
};

function zoned(instant: string | null | undefined, zone: string | undefined) {
  if (!instant) return "No bound";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: zone, dateStyle: "full", timeStyle: "long",
    }).format(new Date(instant));
  } catch (error) {
    if (error instanceof RangeError) return "Enter a valid IANA time zone.";
    throw error;
  }
}

export function PolicySettings({ policy, onChange }: { policy: Policy; onChange: (value: Policy) => void }) {
  const [interactive, setInteractive] = useState(false);
  useEffect(() => setInteractive(true), []);
  return <fieldset disabled={!interactive}>
    <legend>Delivery settings</legend>
    <p>Changes apply only to a newly published version and explicitly new assignments.
      Existing assignments and attempts keep their pinned settings.</p>
    <label><input type="checkbox" checked={policy.durationSeconds == null}
      onChange={(event) => onChange({ ...policy, durationSeconds: event.target.checked ? null : 60 })} />
      Unlimited authored duration</label>
    {policy.durationSeconds != null && <label>Duration (seconds)<input type="number" required
      min={60} max={604800} step={1} value={policy.durationSeconds}
      onChange={(event) => onChange({ ...policy, durationSeconds: Number(event.target.value) })} /></label>}
    <label><input type="checkbox" checked={policy.attemptLimit == null}
      onChange={(event) => onChange({ ...policy, attemptLimit: event.target.checked ? null : 1 })} />
      Unlimited attempts</label>
    {policy.attemptLimit != null && <label>Attempt limit<input type="number" required min={1} max={100}
      step={1} value={policy.attemptLimit}
      onChange={(event) => onChange({ ...policy, attemptLimit: Number(event.target.value) })} /></label>}
    <label>IANA scheduling time zone<input required maxLength={100} value={policy.timeZone}
      onChange={(event) => onChange({ ...policy, timeZone: event.target.value })} /></label>
    <p>Enter availability as explicit UTC instants below; the selected IANA zone is shown for
      confirmation. UTC input avoids ambiguous repeated or nonexistent daylight-saving local times.
      To choose either occurrence of a repeated hour, enter its distinct UTC instant.
      Leave a bound blank for no bound. End must be after start.</p>
    {(["availabilityStart", "availabilityEnd"] as const).map((field) => <div key={field}>
      <label>{field === "availabilityStart" ? "Availability start (UTC)" : "Availability end (UTC)"}
        <input type="datetime-local" step={1} value={policy[field]?.slice(0, 19) ?? ""}
          onChange={(event) => onChange({ ...policy,
            [field]: event.target.value ? new Date(event.target.value + "Z").toISOString() : null })} />
      </label>
      <p>{zoned(policy[field], policy.timeZone)}</p>
    </div>)}
    <p>New starts are blocked at the end in every timing mode. Standard attempts use the earlier
      deadline; learners may choose adjusted duration or timing off before starting.</p>
    <label><input type="checkbox" checked={policy.randomizeQuestions}
      onChange={(event) => onChange({ ...policy, randomizeQuestions: event.target.checked })} />
      Randomize question order</label>
    <label><input type="checkbox" checked={policy.randomizeOptions}
      onChange={(event) => onChange({ ...policy, randomizeOptions: event.target.checked })} />
      Randomize option order</label>
    <label>Release preset<select value={
      policy.answerKeyRelease === "never" && policy.explanationRelease === "never" &&
      policy.scoreRelease !== "after_availability_end" ? policy.scoreRelease : "custom"}
      onChange={(event) => {
        if (event.target.value !== "custom") onChange({ ...policy,
          scoreRelease: event.target.value as Release, answerKeyRelease: "never", explanationRelease: "never" });
      }}>
      <option value="after_finalization">Score only after finalization</option>
      <option value="never">Fully withheld</option>
      <option value="custom" disabled>Independent release settings</option>
    </select></label>
    {([
      ["scoreRelease", "Score release"], ["answerKeyRelease", "Correct answer release"],
      ["explanationRelease", "Explanation release"],
    ] as const).map(([field, label]) => <label key={field}>{label}
      <select value={policy[field]} onChange={(event) =>
        onChange({ ...policy, [field]: event.target.value as Release })}>
        <option value="after_finalization">After finalization</option>
        <option value="after_availability_end">After availability end (requires an end)</option>
        <option value="never">Never</option>
      </select>
    </label>)}
    <p>Every release requires finalization. After-availability-end uses the original published end,
      even for adjusted/off timing. Closing does not release answers. A released score can reveal
      correctness in a one-question quiz. Released explanations can reveal answers even when
      correct-answer release is Never.</p>
  </fieldset>;
}
