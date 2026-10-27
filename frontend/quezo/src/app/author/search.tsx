import { apiData, questionClient } from "../../lib/server/questions";
import { failure } from "../../lib/server/errors";
import { QuestionList } from "./shared";

export type SearchParams = {
  cursor?: string; text?: string; category?: string; tag?: string; pageSize?: string; includeArchived?: string;
};

export function SearchFields({ values }: { values: SearchParams }) {
  return <>
    <label>Search text<input name="text" maxLength={4000} defaultValue={values.text} /></label>
    <label>Filter category<input name="category" maxLength={100} defaultValue={values.category} /></label>
    <label>Filter tag<input name="tag" maxLength={50} defaultValue={values.tag} /></label>
    <label>Questions per page<input name="pageSize" type="number" min={1} max={100}
      defaultValue={values.pageSize ?? "25"} /></label>
    <label><input name="includeArchived" type="checkbox" value="true"
      defaultChecked={values.includeArchived === "true"} /> Include archived questions and banks (history only)</label>
  </>;
}

export async function SearchResults({ values, bankId }: { values: SearchParams; bankId?: string }) {
  const client = await questionClient();
  const size = values.pageSize ?? "25";
  if (!/^\d+$/.test(size) || !Number.isSafeInteger(Number(size))) {
    throw failure(422, "VALIDATION_FAILED", "Questions per page must be a whole number from 1 to 100.");
  }
  const questions = await apiData(client.GET("/api/v1/questions", { params: { query: {
    bankId: bankId ?? null, cursor: values.cursor ?? null, text: values.text || null, category: values.category || null,
    tag: values.tag || null, pageSize: Number(size),
    includeArchived: values.includeArchived === "true",
  } } }));
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) if (value) next.set(key, value);
  if (questions.nextCursor) next.set("cursor", questions.nextCursor);
  const path = bankId ? `/author/banks/${bankId}` : "/author/questions";
  return <>
    <form action={path}><h2>Find reusable questions</h2><SearchFields values={values} /><button>Search questions</button></form>
    <p>Text matches the prompt (case-insensitive literal text); category and tag match exactly.
      Archived questions and archived banks are excluded unless explicitly included for history; they cannot enter new quiz selections.</p>
    <QuestionList items={questions.items} />
    {questions.nextCursor && <a href={`${path}?${next}`}>Next questions</a>}
  </>;
}
