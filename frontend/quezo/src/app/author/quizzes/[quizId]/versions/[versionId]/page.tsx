import { apiData, questionClient } from "../../../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../../../shared";
import { AssignLearner } from "../../../assign";

export const dynamic = "force-dynamic";

export default async function PublishedPage({ params }: { params: Promise<{ quizId: string; versionId: string }> }) {
  try {
    const { quizId, versionId } = await params;
    const client = await questionClient();
    const version = await apiData(client.GET("/api/v1/quizzes/{quiz_id}/versions/{version_id}", {
      params: { path: { quiz_id: quizId, version_id: versionId } },
    }));
    const learners = await apiData(client.GET("/api/v1/eligible-learners"));
    return <AuthorPage><h1>Published: {version.title}</h1>
      <p>Immutable publication from draft revision {version.draftRevision}.</p>
      <p>Published version: <code>{version.id}</code></p>
      <p className="plain-text">{version.instructions}</p>
      <p>Possible points: {version.possiblePoints}</p>
      <h2>Pinned policy</h2>
      <dl>{Object.entries(version.policy).map(([name, value]) => <div key={name}>
        <dt>{name}</dt><dd>{value === null ? "No limit / window" : String(value)}</dd>
      </div>)}</dl>
      <ol>{version.questions.map((item) => <li key={item.position}>
        <p className="plain-text">{item.question.prompt}</p><p>{item.effectivePoints} points</p>
        <p>Question revision {item.question.revision}; version <code>{item.question.versionId}</code></p>
      </li>)}</ol>
      <AssignLearner quizId={quizId} versionId={versionId} initial={learners} />
      <a href={`/author/quizzes/${quizId}`}>Back to quiz</a>
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
