import { apiData, questionClient } from "../../../../lib/server/questions";
import { BankForm, OrganizationControls } from "../../forms";
import { AuthorError, AuthorPage } from "../../shared";
import { SearchResults, type SearchParams } from "../../search";

export const dynamic = "force-dynamic";

export default async function BankPage({ params, searchParams }: {
  params: Promise<{ bankId: string }>; searchParams: Promise<SearchParams>;
}) {
  try {
    const { bankId } = await params;
    const values = await searchParams;
    const client = await questionClient();
    const bank = await apiData(client.GET("/api/v1/question-banks/{bank_id}", { params: { path: { bank_id: bankId } } }));
    return <AuthorPage><h1>{bank.name}</h1>
      {!bank.archived && <>
        <a href={`/author/banks/${bankId}/new`}>Create question</a>
        <BankForm bank={bank} />
      </>}
      {await SearchResults({ values: bank.archived ? { ...values, includeArchived: "true" } : values, bankId })}
      <OrganizationControls bank={bank} />
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
