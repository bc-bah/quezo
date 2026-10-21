import { randomUUID } from "node:crypto";
import { apiData, questionClient } from "../../../../../lib/server/questions";
import { QuestionForm } from "../../../forms";
import { AuthorError, AuthorPage } from "../../../shared";

export const dynamic = "force-dynamic";

export default async function NewQuestionPage({ params }: { params: Promise<{ bankId: string }> }) {
  try {
    const { bankId } = await params;
    const client = await questionClient();
    const bank = await apiData(client.GET("/api/v1/question-banks/{bank_id}", { params: { path: { bank_id: bankId } } }));
    const options = [{ id: randomUUID(), text: "" }, { id: randomUUID(), text: "" }];
    return <AuthorPage><h1>New question in {bank.name}</h1>
      <QuestionForm bankId={bankId} initial={{
        questionType: "mcq", prompt: "", options, correctOptionId: options[0]!.id,
        defaultPoints: 1, feedback: "",
      }} />
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
