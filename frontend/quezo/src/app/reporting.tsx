import type { components } from "../lib/api/schema";

type S = components["schemas"];

export function AttemptRecord({ attempt, href }: { attempt: S["AttemptHistoryItem"]; href: string | null }) {
  return <article aria-label={`Attempt ${attempt.attemptNumber}: ${attempt.id}`}>
    <h3>{attempt.title} - attempt {attempt.attemptNumber}</h3>
    <p>Attempt ID: {attempt.id}; assignment: {attempt.assignmentId}</p>
    <p>Publication version: {attempt.versionId}</p>
    <p>Learner: {attempt.learnerId}</p>
    <p>Started: <time dateTime={attempt.startedAt}>{attempt.startedAt}</time></p>
    <p>Timing: {attempt.timingChoice}; deadline: {attempt.deadline ?? "none"}
      {attempt.adjustedDurationSeconds !== null && `; adjusted duration: ${attempt.adjustedDurationSeconds} seconds`}</p>
    <p>Status: {attempt.completion?.completionReason ?? "in progress"}</p>
    {attempt.completion && <p>Finalized: <time dateTime={attempt.completion.finalizedAt}>{attempt.completion.finalizedAt}</time></p>}
    <Score score={attempt.score} />
    {href ? <a href={href}>{attempt.state === "finalized" ? "Inspect finalized attempt" : "Resume attempt"}</a>
      : <p>Submission inspection is available only after finalization.</p>}
  </article>;
}

export function Score({ score }: { score: S["AttemptHistoryItem"]["score"] }) {
  return score.status === "released"
    ? <p>Score: {score.earnedPoints} / {score.possiblePoints} points
      {" ("}{(100 * score.earnedPoints / score.possiblePoints).toFixed(1)}%)</p>
    : <p>{score.status === "withheld" ? "Score withheld." : "No final score: attempt in progress."}</p>;
}

export function ReleasedResult({ result }: { result: S["LearnerResult"] }) {
  return <>
    <section aria-label="Score">
      <h2>Score</h2>
      <Score score={result.score} />
    </section>
    <section aria-label="Answer key">
      <h2>Answer key</h2>
      {result.answerKey.status === "released" ? result.answerKey.items.map((item) =>
        <article key={item.attemptQuestionId}>
          <h3>Question {item.position}</h3><p className="plain-text">{item.prompt}</p>
          <p className="plain-text">Correct answer: {item.correctOption.text}</p>
          <p>Outcome: {item.outcome}. Awarded {item.earnedPoints} / {item.possiblePoints} points.</p>
        </article>) : <p>Answer key and item outcomes withheld.</p>}
    </section>
    <section aria-label="Explanations">
      <h2>Explanations</h2>
      {result.explanations.status === "released" ? result.explanations.items.map((item) =>
        <article key={item.attemptQuestionId}>
          <h3>Question {item.position}</h3><p className="plain-text">{item.prompt}</p>
          <p className="plain-text">{item.feedback || "No explanation provided."}</p>
        </article>) : <p>Explanations withheld.</p>}
    </section>
    <p>Release checked at <time dateTime={result.serverTime}>{result.serverTime}</time>.
      {" "}Reload this page to check again.</p>
  </>;
}
