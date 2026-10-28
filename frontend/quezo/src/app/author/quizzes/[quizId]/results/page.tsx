import { apiData, questionClient } from "../../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../../shared";
import { AttemptRecord } from "../../../../reporting";

export const dynamic = "force-dynamic";

export default async function ReportPage({ params, searchParams }: {
  params: Promise<{ quizId: string }>;
  searchParams: Promise<{ learnerCursor?: string; attemptCursor?: string }>;
}) {
  const { quizId } = await params;
  const base = `/author/quizzes/${quizId}/results`;
  try {
    const client = await questionClient();
    const { learnerCursor, attemptCursor } = await searchParams;
    const path = { quiz_id: quizId };
    const [report, attempts] = await Promise.all([
      apiData(client.GET("/api/v1/quizzes/{quiz_id}/results", {
        params: { path, query: { cursor: learnerCursor ?? null } },
      })),
      apiData(client.GET("/api/v1/quizzes/{quiz_id}/results/attempts", {
        params: { path, query: { cursor: attemptCursor ?? null } },
      })),
    ]);
    const summary = report.summary;
    const next = (learners: string | null, attempts: string | null) => {
      const query = new URLSearchParams();
      if (learners) query.set("learnerCursor", learners);
      if (attempts) query.set("attemptCursor", attempts);
      return `${base}?${query}`;
    };
    return <AuthorPage><a href={`/author/quizzes/${quizId}`}>Back to quiz</a>
      <h1>Report: {report.title}</h1>
      <section aria-label="Summary"><h2>Participation and completion</h2>
        <p>Assigned learners: {summary.assignedLearners}</p>
        <p>Participation: {summary.participatingLearners} / {summary.assignedLearners} assigned learners have started at least one attempt.</p>
        <p>Completion: {summary.completedLearners} / {summary.assignedLearners} assigned learners have finalized at least one attempt.</p>
        <p>Started attempts: {summary.startedAttempts}; in progress: {summary.inProgressAttempts};
          {" "}finalized: {summary.finalizedAttempts}; submitted: {summary.submittedAttempts}; expired: {summary.expiredAttempts}.</p>
        <h2>Scores per finalized attempt</h2>
        <p>Released scores: {summary.releasedScoreAttempts}; withheld scores: {summary.withheldScoreAttempts}.
          In-progress attempts have no final score and are excluded. No best-attempt selection.</p>
        {summary.meanScorePercent === null ? <p>No released finalized scores.</p>
          : <p>Mean: {summary.meanScorePercent.toFixed(1)}%.
            Denominator: {summary.releasedScoreAttempts} released finalized attempts
            {" "}of {summary.finalizedAttempts} finalized attempts (each attempt equally weighted).</p>}
        <p>Release checked at {report.serverTime}. Reload to check again.</p>
      </section>
      <section aria-label="Assigned learners"><h2>Assigned learners</h2>
        {report.learners.items.length === 0 && <p>No assigned learners on this page.</p>}
        {report.learners.items.map((learner) => <article key={learner.learnerId}>
          <h3>Learner {learner.learnerId}</h3>
          <p>Assignments: {learner.assignmentCount}; started: {learner.startedAttempts};
            {" "}in progress: {learner.inProgressAttempts}; finalized: {learner.finalizedAttempts};
            {" "}submitted: {learner.submittedAttempts}; expired: {learner.expiredAttempts}.</p>
        </article>)}
        {report.learners.nextCursor && <a href={next(report.learners.nextCursor, attemptCursor ?? null)}>Next learners</a>}
      </section>
      <section aria-label="Attempts"><h2>Attempts across publications</h2>
        {attempts.items.length === 0 && <p>No attempts on this page.</p>}
        {attempts.items.map((attempt) => <AttemptRecord key={attempt.id} attempt={attempt}
          href={attempt.state === "finalized" ? `${base}/attempts/${attempt.id}` : null} />)}
        {attempts.nextCursor && <a href={next(learnerCursor ?? null, attempts.nextCursor)}>Next attempts</a>}
      </section>
      {(learnerCursor || attemptCursor) && <a href={base}>First report page</a>}
    </AuthorPage>;
  } catch (error) {
    return <><AuthorError error={error} /><p><a href={base}>Retry report</a></p></>;
  }
}
