import { apiData, questionClient } from "../../../../../lib/server/questions";
import { AuthorError, AuthorPage } from "../../../shared";

export const dynamic = "force-dynamic";

export default async function PreviewPage({ params }: { params: Promise<{ quizId: string }> }) {
  try {
    const { quizId } = await params;
    const client = await questionClient();
    const path = { quiz_id: quizId };
    const quiz = await apiData(client.GET("/api/v1/quizzes/{quiz_id}", { params: { path } }));
    const preview = await apiData(client.POST("/api/v1/quizzes/{quiz_id}/preview", {
      params: { path }, body: { expectedRevision: quiz.draftRevision },
    }));
    return <AuthorPage><h1>Preview: {preview.title}</h1>
      <p>This is an author-only preview using the saved presentation settings. Choices are not saved or graded.
        No assignment, attempt or allowance is created or consumed.</p>
      <p className="plain-text">{preview.instructions}</p>
      <p>Possible points: {preview.possiblePoints}</p>
      {preview.questions.map((item) => <fieldset key={item.position}>
        <legend>Question {item.position}: {item.effectivePoints} points</legend>
        <p className="plain-text">{item.prompt}</p>
        {item.options.map((option) => <label key={option.id}>
          <input type="radio" name={`question-${item.position}`} value={option.id} />{option.text}
        </label>)}
      </fieldset>)}
      <a href={`/author/quizzes/${quizId}`}>Back to quiz</a>
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
