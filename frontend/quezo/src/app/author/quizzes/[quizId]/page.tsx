import { apiData, questionClient } from "../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../shared";
import { Composition } from "../composition";
import { Publication } from "../publication";

export const dynamic = "force-dynamic";

export default async function QuizPage({ params }: { params: Promise<{ quizId: string }> }) {
  try {
    const { quizId } = await params;
    const client = await questionClient();
    const quiz = await apiData(client.GET("/api/v1/quizzes/{quiz_id}", { params: { path: { quiz_id: quizId } } }));
    const choices = quiz.hasDraft ? await apiData(client.GET("/api/v1/questions")) : null;
    return <AuthorPage><h1>{quiz.title}</h1>
      <p>Draft revision: {quiz.draftRevision}</p>
      <Publication key={`${quiz.id}-${quiz.draftRevision}`} quiz={quiz} />
      {quiz.draft && choices && <Composition key={quiz.draftRevision} quiz={quiz} initial={quiz.draft} choices={choices} />}
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
