import { apiData, questionClient } from "../../lib/server/questions";
import { BankForm } from "./forms";
import { AuthorError, AuthorPage } from "./shared";

export const dynamic = "force-dynamic";

export default async function BanksPage({ searchParams }: {
  searchParams: Promise<{ cursor?: string }>;
}) {
  try {
    const client = await questionClient();
    const { cursor } = await searchParams;
    const banks = await apiData(client.GET("/api/v1/question-banks", { params: { query: { cursor: cursor ?? null } } }));
    return <AuthorPage><h1>Question banks</h1>
      {banks.items.length ? <ul>{banks.items.map((bank) =>
        <li key={bank.id}><a href={`/author/banks/${bank.id}`}>{bank.name}</a></li>)}</ul>
        : <p>No banks yet. Create your first bank below.</p>}
      {banks.nextCursor && <a href={`/author?cursor=${encodeURIComponent(banks.nextCursor)}`}>Next banks</a>}
      <BankForm />
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
