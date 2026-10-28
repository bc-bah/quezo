import { apiData, assessmentClient } from "../../../../../lib/server/questions";
import { publicError } from "../../../../../lib/server/errors";
import { ReleasedResult } from "../../../../reporting";

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
      <a href="/learner/history">Attempt history</a>
      <p>Attempt {result.attemptNumber}; ID: {result.completion.attemptId}</p>
      <p>Publication version: {result.versionId}</p>
      <h2>{result.completion.completionReason === "expired" ? "Attempt expired" : "Submission confirmed"}</h2>
      <p>Finalized at <time dateTime={result.completion.finalizedAt}>{result.completion.finalizedAt}</time>.</p>
      <ReleasedResult result={result} />
      <a href={`/learner/attempts/${attemptId}`}>Back to attempt</a>
    </main>;
  } catch (error) {
    return <main id="main"><h1>Result unavailable</h1>
      <p role="alert">{publicError(error).envelope.message}</p>
      <a href="/learner">My assignments</a></main>;
  }
}
