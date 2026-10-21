import type { components } from "../../../lib/api/schema";

type Policy = components["schemas"]["QuizPolicy"];

export const demoPolicy: Policy = {
  durationSeconds: null, attemptLimit: 1, availabilityStart: null, availabilityEnd: null,
  timeZone: "UTC", randomizeQuestions: false, randomizeOptions: false,
  scoreRelease: "after_finalization", answerKeyRelease: "never", explanationRelease: "never",
};

export function supportsDemoPolicy(policy: Policy) {
  return policy.durationSeconds === null && policy.attemptLimit === 1 &&
    policy.availabilityStart === null && policy.availabilityEnd === null &&
    policy.timeZone === "UTC" && policy.randomizeQuestions === false && policy.randomizeOptions === false &&
    policy.answerKeyRelease === "never" && policy.explanationRelease === "never" &&
    (policy.scoreRelease === "never" || policy.scoreRelease === "after_finalization");
}

export function PolicySettings({ policy, onChange }: { policy: Policy; onChange: (value: Policy) => void }) {
  return <fieldset>
    <legend>Result policy</legend>
    <p>Untimed, no availability window, one attempt, authored question and option order.
      Advanced settings are not available in this editor.</p>
    <label>Release preset<select value={policy.scoreRelease}
      onChange={(event) => onChange({ ...policy,
        scoreRelease: event.target.value === "never" ? "never" : "after_finalization" })}>
      <option value="after_finalization">Score only after finalization</option>
      <option value="never">Fully withheld</option>
    </select></label>
    <p>Answer keys and explanations are withheld in both presets. A released total can reveal
      correctness for a one-question quiz.</p>
  </fieldset>;
}
