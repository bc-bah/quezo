import { apiData, assessmentClient } from "../../../lib/server/questions";
import { publicError } from "../../../lib/server/errors";
import { AttemptRecord } from "../../reporting";

export const dynamic = "force-dynamic";

export default async function HistoryPage({ searchParams }: {
  searchParams: Promise<{ cursor?: string }>;
}) {
  try {
    const client = await assessmentClient("learner");
    const { cursor } = await searchParams;
    const page = await apiData(client.GET("/api/v1/me/attempts", {
      params: { query: { cursor: cursor ?? null } },
    }));
    return <main id="main"><a href="/learner">My assignments</a><h1>Attempt history</h1>
      <p>All your started attempts, including retained publications. Scores are checked against each attempt&apos;s release policy on every read.</p>
      {page.items.length === 0 && <p>No attempts on this page.</p>}
      {page.items.map((attempt) => <AttemptRecord key={attempt.id} attempt={attempt}
        href={`/learner/attempts/${attempt.id}${attempt.state === "finalized" ? "/result" : ""}`} />)}
      {page.nextCursor && <a href={`/learner/history?cursor=${encodeURIComponent(page.nextCursor)}`}>Next attempts</a>}
      {cursor && <p><a href="/learner/history">First history page</a></p>}
    </main>;
  } catch (error) {
    return <main id="main"><h1>Attempt history unavailable</h1>
      <p role="alert">{publicError(error).envelope.message}</p>
      <a href="/learner/history">Retry history</a>{" "}<a href="/learner">My assignments</a></main>;
  }
}
