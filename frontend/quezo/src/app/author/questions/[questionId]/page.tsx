import { apiData, questionClient } from "../../../../lib/server/questions";
import { QuestionForm } from "../../forms";
import { AuthorError, AuthorPage, QuestionList } from "../../shared";

export const dynamic = "force-dynamic";

export default async function QuestionPage({ params, searchParams }: {
  params: Promise<{ questionId: string }>; searchParams: Promise<{ cursor?: string }>;
}) {
  try {
    const { questionId } = await params;
    const { cursor } = await searchParams;
    const client = await questionClient();
    const [current, versions] = await Promise.all([
      apiData(client.GET("/api/v1/questions/{question_id}", { params: { path: { question_id: questionId } } })),
      apiData(client.GET("/api/v1/questions/{question_id}/versions", {
        params: { path: { question_id: questionId }, query: { cursor: cursor ?? null } },
      })),
    ]);
    const { questionType, prompt, options, correctOptionId, defaultPoints, feedback } = current;
    return <AuthorPage><h1>Question revisions</h1>
      <a href={`/author/banks/${current.bankId}`}>Back to bank</a>
      <QuestionForm key={current.versionId} bankId={current.bankId} current={current}
        initial={{ questionType, prompt, options, correctOptionId, defaultPoints, feedback }} />
      <h2>Select an exact revision</h2>
      <p>Existing selections never change when a new revision is saved.</p>
      <QuestionList items={versions.items} />
      {versions.nextCursor && <a href={`/author/questions/${questionId}?cursor=${encodeURIComponent(versions.nextCursor)}`}>Next revisions</a>}
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
