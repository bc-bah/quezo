import { apiData, questionClient } from "../../../../lib/server/questions";
import { BankForm } from "../../forms";
import { AuthorError, AuthorPage, QuestionList } from "../../shared";

export const dynamic = "force-dynamic";

export default async function BankPage({ params, searchParams }: {
  params: Promise<{ bankId: string }>; searchParams: Promise<{ cursor?: string }>;
}) {
  try {
    const { bankId } = await params;
    const { cursor } = await searchParams;
    const client = await questionClient();
    const [bank, questions] = await Promise.all([
      apiData(client.GET("/api/v1/question-banks/{bank_id}", { params: { path: { bank_id: bankId } } })),
      apiData(client.GET("/api/v1/questions", { params: { query: { bankId, cursor: cursor ?? null } } })),
    ]);
    return <AuthorPage><h1>{bank.name}</h1>
      <a href={`/author/banks/${bankId}/new`}>Create question</a>
      <QuestionList items={questions.items} />
      {questions.nextCursor && <a href={`/author/banks/${bankId}?cursor=${encodeURIComponent(questions.nextCursor)}`}>Next questions</a>}
      <BankForm bank={bank} />
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
