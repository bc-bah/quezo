import { apiData, questionClient } from "../../../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../../../shared";

export const dynamic = "force-dynamic";

export default async function VersionPage({ params }: {
  params: Promise<{ questionId: string; versionId: string }>;
}) {
  try {
    const { questionId, versionId } = await params;
    const client = await questionClient();
    const version = await apiData(client.GET("/api/v1/questions/{question_id}/versions/{version_id}", {
      params: { path: { question_id: questionId, version_id: versionId } },
    }));
    return <AuthorPage><h1>Selected question revision {version.revision}</h1>
      <p role="status">This exact revision is saved. Use its question and version IDs to select it explicitly in a quiz.</p>
      <p>{version.questionType === "mcq" ? "Single-answer MCQ" : "True/false"}</p>
      <p className="plain-text" data-testid="question-prompt">{version.prompt}</p>
      <p>Default points: {version.defaultPoints}</p>
      <ol>{version.options.map((option) => <li key={option.id}>
        <span className="plain-text">{option.text}</span>
        {option.id === version.correctOptionId && <strong> (Correct)</strong>}
        <div>Option ID: <code>{option.id}</code></div>
      </li>)}</ol>
      <h2>Explanatory feedback</h2><p className="plain-text">{version.feedback || "No feedback supplied."}</p>
      <label>Selected version ID<input readOnly value={version.versionId} /></label>
      <p>Question ID: <code>{version.questionId}</code></p>
      <a href="/author/quizzes">Compose a quiz</a>{" | "}
      <a href={`/author/questions/${version.questionId}`}>Edit current revision or select another</a>{" | "}
      <a href={`/author/banks/${version.bankId}`}>Back to bank</a>
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
