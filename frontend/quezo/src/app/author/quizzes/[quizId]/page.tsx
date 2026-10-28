import { apiData, questionClient } from "../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../shared";
import { Composition } from "../composition";
import { Publication } from "../publication";

export const dynamic = "force-dynamic";

export default async function QuizPage({ params, searchParams }: {
  params: Promise<{ quizId: string }>; searchParams: Promise<{ cursor?: string }>;
}) {
  try {
    const { quizId } = await params;
    const client = await questionClient();
    const quiz = await apiData(client.GET("/api/v1/quizzes/{quiz_id}", { params: { path: { quiz_id: quizId } } }));
    const editable = quiz.state === "draft" || quiz.state === "published";
    const { cursor } = await searchParams;
    const [choices, history] = await Promise.all([
      quiz.hasDraft && editable ? apiData(client.GET("/api/v1/questions")) : null,
      apiData(client.GET("/api/v1/quizzes/{quiz_id}/versions", {
        params: { path: { quiz_id: quizId }, query: { cursor: cursor ?? null } },
      })),
    ]);
    return <AuthorPage><h1>{quiz.title}</h1>
      <a href={`/author/quizzes/${quizId}/results`}>Participation and results</a>
      <p>Draft revision: {quiz.draftRevision}</p>
      <Publication key={`${quiz.id}-${quiz.draftRevision}-${quiz.state}`} quiz={quiz} />
      {quiz.draft && choices && <Composition key={quiz.draftRevision} quiz={quiz} initial={quiz.draft} choices={choices} />}
      <section><h2>Publication history</h2>
        <p>Each publication is immutable. New publications never reassign existing learners.</p>
        {history.items.length ? <ul>{history.items.map((item) => <li key={item.id}>
          <a href={`/author/quizzes/${quizId}/versions/${item.id}`}>Publication from draft revision {item.draftRevision}</a>
          {" "}{item.title}; {item.possiblePoints} points; {item.publishedAt}
        </li>)}</ul> : <p>No publications yet.</p>}
        {history.nextCursor && <a href={`/author/quizzes/${quizId}?cursor=${encodeURIComponent(history.nextCursor)}`}>Next publications</a>}
      </section>
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
