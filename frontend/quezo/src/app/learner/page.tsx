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
        <p>Started: {assignment.attemptsStarted}; completed: {assignment.attemptsCompleted};
          remaining: {assignment.attemptsRemaining ?? "unlimited"}</p>
        <StartAttempt assignment={assignment} />
      </section>)}
      {page.nextCursor && <a href={`/learner?cursor=${encodeURIComponent(page.nextCursor)}`}>Next assignments</a>}
    </main>;
  } catch (error) {
    return <main id="main"><h1>My assignments</h1><p role="alert">{publicError(error).envelope.message}</p><a href="/">Home</a></main>;
  }
}
