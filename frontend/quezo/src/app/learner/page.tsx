import { apiData, assessmentClient } from "../../lib/server/questions";
import { publicError } from "../../lib/server/errors";
import { StartAttempt } from "./start";

export const dynamic = "force-dynamic";

export default async function LearnerPage({ searchParams }: { searchParams: Promise<{ cursor?: string }> }) {
  try {
    const client = await assessmentClient("learner");
    const { cursor } = await searchParams;
    const page = await apiData(client.GET("/api/v1/assignments", { params: { query: { cursor: cursor ?? null } } }));
    return <main id="main"><a href="/">Home</a><h1>My assignments</h1>
      {page.items.length === 0 && <p>No assignments.</p>}
      {page.items.map((assignment) => <section key={assignment.id} aria-label={assignment.title}>
        <h2>{assignment.title}</h2>
        <p>State: {assignment.state.replaceAll("_", " ")}</p>
        <p>{({
          not_yet_available: "The scheduled start has not arrived.",
          available: "You may start an attempt.",
          in_progress: "Resume your existing attempt with its original timing.",
          completed_remaining: "You have completed an attempt and may start another.",
          exhausted: "All allowed starts have been used; expired attempts also count.",
          closed: "New starts are closed by the quiz state or scheduled end.",
        })[assignment.state]}</p>
        <p>Availability ({assignment.timeZone}): {assignment.availabilityStart ?? "no start bound"}
          {" to "}{assignment.availabilityEnd ?? "no end bound"} (UTC instants).
          The server decides eligibility at start.</p>
        <p>Started: {assignment.attemptsStarted}; completed: {assignment.attemptsCompleted};
          remaining: {assignment.attemptsRemaining ?? "unlimited"}</p>
        <StartAttempt assignment={assignment} />
        {assignment.latestCompletedAttemptId && <div>
          <p>Most recent completed attempt:</p>
          <a href={`/learner/attempts/${assignment.latestCompletedAttemptId}`}>View completed attempt</a>
          {" "}
          <a href={`/learner/attempts/${assignment.latestCompletedAttemptId}/result`}>View result</a>
        </div>}
      </section>)}
      {page.nextCursor && <a href={`/learner?cursor=${encodeURIComponent(page.nextCursor)}`}>Next assignments</a>}
    </main>;
  } catch (error) {
    return <main id="main"><h1>My assignments</h1><p role="alert">{publicError(error).envelope.message}</p><a href="/">Home</a></main>;
  }
}
