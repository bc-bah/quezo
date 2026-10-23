import { apiData, assessmentClient } from "../../../../../lib/server/questions";
import { publicError } from "../../../../../lib/server/errors";

export const dynamic = "force-dynamic";

export default async function ResultPage({ params }: { params: Promise<{ attemptId: string }> }) {
  try {
    const client = await assessmentClient("learner");
    const { attemptId } = await params;
    const result = await apiData(client.GET("/api/v1/attempts/{attempt_id}/result", {
      params: { path: { attempt_id: attemptId } },
    }));
    return <main id="main">
      <a href="/learner">My assignments</a>
      <h1>Result: {result.title}</h1>
      <p>Attempt {result.attemptNumber}</p>
      <h2>{result.completion.completionReason === "expired" ? "Attempt expired" : "Submission confirmed"}</h2>
      <p>Finalized at <time dateTime={result.completion.finalizedAt}>{result.completion.finalizedAt}</time>.</p>
      <section aria-label="Score">
        <h2>Score</h2>
        {result.score.status === "released"
          ? <p>{result.score.earnedPoints} / {result.score.possiblePoints} points
            {" ("}{(100 * result.score.earnedPoints / result.score.possiblePoints).toFixed(1)}%)</p>
          : <p>Score withheld.</p>}
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
      <a href={`/learner/attempts/${attemptId}`}>Back to attempt</a>
    </main>;
  } catch (error) {
    return <main id="main"><h1>Result unavailable</h1>
      <p role="alert">{publicError(error).envelope.message}</p>
      <a href="/learner">My assignments</a></main>;
  }
}
