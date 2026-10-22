import { apiData, assessmentClient } from "../../../../lib/server/questions";
import { publicError } from "../../../../lib/server/errors";

export const dynamic = "force-dynamic";

export default async function AttemptPage({ params }: { params: Promise<{ attemptId: string }> }) {
  try {
    const client = await assessmentClient("learner");
    const { attemptId } = await params;
    const attempt = await apiData(client.GET("/api/v1/attempts/{attempt_id}", {
      params: { path: { attempt_id: attemptId } },
    }));
    return <main id="main"><a href="/learner">My assignments</a>
      <h1>{attempt.title}</h1><p>Attempt {attempt.attemptNumber}: {attempt.state.replaceAll("_", " ")}</p>
      <p className="plain-text">{attempt.instructions}</p>
      <p>Possible points: {attempt.possiblePoints}</p>
      <p>Answer saving and submission are not available yet.</p>
      <ol>{attempt.questions.map((question) => <li key={question.attemptQuestionId} data-question-id={question.attemptQuestionId}>
        <p className="plain-text">{question.prompt}</p><p>{question.effectivePoints} points</p>
        <ol>{question.options.map((option) => <li key={option.id} data-option-id={option.id} className="plain-text">{option.text}</li>)}</ol>
      </li>)}</ol>
    </main>;
  } catch (error) {
    return <main id="main"><h1>Attempt unavailable</h1><p role="alert">{publicError(error).envelope.message}</p>
      <a href="/learner">My assignments</a></main>;
  }
}
