import { AuthorError, AuthorPage } from "../shared";
import { SearchResults, type SearchParams } from "../search";

export const dynamic = "force-dynamic";

export default async function QuestionsPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  try {
    const values = await searchParams;
    return <AuthorPage><h1>Search all owned questions</h1>
      {await SearchResults({ values })}
    </AuthorPage>;
  } catch (error) { return <AuthorError error={error} />; }
}
