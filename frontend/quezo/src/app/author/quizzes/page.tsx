import { apiData, questionClient } from "../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../shared";
import { Composition } from "./composition";

export const dynamic = "force-dynamic";

export default async function QuizzesPage({ searchParams }: { searchParams: Promise<{ cursor?: string }> }) {
  try {
    const client = await questionClient();
    const { cursor } = await searchParams;
    const [quizzes, choices] = await Promise.all([
      apiData(client.GET("/api/v1/quizzes", { params: { query: { cursor: cursor ?? null } } })),
      apiData(client.GET("/api/v1/questions")),
    ]);
    return <AuthorPage><h1>Quizzes</h1>
      {quizzes.items.length ? <ul>{quizzes.items.map((quiz) => <li key={quiz.id}>
        <a href={`/author/quizzes/${quiz.id}`}>{quiz.title}</a> ({quiz.state})
      </li>)}</ul> : <p>No quizzes yet.</p>}
      {quizzes.nextCursor && <a href={`/author/quizzes?cursor=${encodeURIComponent(quizzes.nextCursor)}`}>Next quizzes</a>}
      <Composition choices={choices} />
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
