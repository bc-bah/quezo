import { apiData, questionClient } from "../../../../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../../../../shared";
import { ReleasedResult } from "../../../../../../reporting";

export const dynamic = "force-dynamic";

export default async function SubmissionPage({ params }: {
  params: Promise<{ quizId: string; attemptId: string }>;
}) {
  const { quizId, attemptId } = await params;
  const back = `/author/quizzes/${quizId}/results`;
  try {
    const client = await questionClient();
    const submission = await apiData(client.GET("/api/v1/quizzes/{quiz_id}/results/attempts/{attempt_id}", {
      params: { path: { quiz_id: quizId, attempt_id: attemptId } },
    }));
    const { attempt, result } = submission;
    return <AuthorPage><a href={back}>Back to report</a><h1>Submission: {attempt.title}</h1>
      <p>Attempt {attempt.attemptNumber}; ID: {attempt.id}; assignment: {attempt.assignmentId}</p>
      <p>Publication version: {attempt.versionId}; learner: {attempt.learnerId}</p>
      <p>Status: {attempt.completion?.completionReason}; started: {attempt.startedAt};
        {" "}finalized: {attempt.completion?.finalizedAt}</p>
      <p>Timing: {attempt.timingChoice}; deadline: {attempt.deadline ?? "none"};
        {" "}adjusted duration: {attempt.adjustedDurationSeconds ?? "not applicable"} seconds</p>
      <section aria-label="Saved responses"><h2>Saved responses at finalization</h2>
        {submission.responses.map((item) => <article key={item.attemptQuestionId}>
          <h3>Question {item.position}</h3><p className="plain-text">{item.prompt}</p>
          <p>Question ID: {item.attemptQuestionId}</p>
          <p className="plain-text">{item.response.selectedOptionId === null ? "Unanswered."
            : `Selected answer: ${item.options.find((option) => option.id === item.response.selectedOptionId)!.text}`}</p>
          <p>Saved revision: {item.response.revision}; saved at: {item.response.savedAt ?? "never"}</p>
        </article>)}
      </section>
      <ReleasedResult result={result} />
    </AuthorPage>;
  } catch (error) {
    return <><AuthorError error={error} /><p><a href={back}>Back to report</a></p></>;
  }
}
