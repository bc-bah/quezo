"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../../lib/api/schema";
import { availableQuestions, exactQuestion, saveQuiz } from "./actions";
import { demoPolicy, PolicySettings } from "./policy-settings";

type S = components["schemas"];
type Selection = S["Selection"];

export function QuizError({ error }: { error: S["ErrorEnvelope"] | string | null }) {
  if (!error) return null;
  if (typeof error === "string") return <p role="alert">{error}</p>;
  return <div role="alert"><p>{error.code === "DRAFT_REVISION_CONFLICT"
    ? "This draft changed in another tab. Your edits are not saved. Reload the saved draft before editing again."
    : error.message}</p>
    {error.details && "fields" in error.details && error.details.fields.map((field, index) => <p key={index}>
      {field.path.join(".")}: {field.reason.replaceAll("_", " ")}
    </p>)}
    <p>Reference: {error.requestId}</p>
    {error.code === "DRAFT_REVISION_CONFLICT" && <button type="button"
      onClick={() => window.location.reload()}>Reload saved draft (discard local edits)</button>}
  </div>;
}

export function Composition({ quiz, initial, choices }: {
  quiz?: S["Quiz"]; initial?: S["QuizComposition"]; choices: S["Page_QuestionSummary_"];
}) {
  const router = useRouter();
  const [body, setBody] = useState<S["QuizComposition"]>(initial ?? {
    title: "", instructions: "", questions: [], policy: demoPolicy,
  });
  const [available, setAvailable] = useState(choices);
  const [laterPage, setLaterPage] = useState(false);
  const [questionId, setQuestionId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [filters, setFilters] = useState({ text: "", category: "", tag: "", bankId: "" });
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<S["ErrorEnvelope"] | string | null>(null);
  const selected = body.questions ?? [];
  const policy = body.policy ?? demoPolicy;
  function add(item: Selection) {
    if (selected.some((entry) => entry.questionId === item.questionId)) {
      setError("This question is already selected. Remove it before explicitly selecting another revision."); return;
    }
    if (selected.length >= 200) { setError("A quiz can contain at most 200 questions."); return; }
    setError(null);
    setBody({ ...body, questions: [...selected, item] });
  }
  function move(index: number, offset: number) {
    const next = [...selected];
    [next[index], next[index + offset]] = [next[index + offset]!, next[index]!];
    setBody({ ...body, questions: next });
  }
  async function loadChoices(cursor: string | null) {
    setPending(true); setError(null);
    try {
      const result = await availableQuestions(cursor, {
        text: filters.text || null, category: filters.category || null,
        tag: filters.tag || null, bankId: filters.bankId || null,
      });
      if (!result.ok) { setError(result.error); return; }
      setAvailable(result.value);
      setLaterPage(cursor !== null);
    } catch { setError("Questions could not be loaded. Your draft is unchanged."); }
    finally { setPending(false); }
  }
  async function addExact() {
    setPending(true); setError(null);
    try {
      const result = await exactQuestion(questionId, versionId);
      if (!result.ok) { setError(result.error); return; }
      add({ questionId: result.value.questionId, versionId: result.value.versionId, pointOverride: null });
    } catch { setError("The revision could not be loaded. Your draft is unchanged."); }
    finally { setPending(false); }
  }
  async function updateVersion(index: number) {
    setPending(true); setError(null); setNotice("");
    try {
      const result = await exactQuestion(selected[index]!.questionId);
      if (!result.ok) { setError(result.error); return; }
      setBody({ ...body, questions: selected.map((item, i) =>
        i === index ? { ...item, versionId: result.value.versionId } : item) });
      setNotice(`Question ${index + 1} explicitly selected revision ${result.value.revision}. Save the draft to retain this choice.`);
    } catch { setError("The current revision could not be loaded. Your pinned selection is unchanged."); }
    finally { setPending(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError(null);
    try {
      const result = await saveQuiz(body, quiz ? { id: quiz.id, expectedRevision: quiz.draftRevision } : undefined);
      if (!result.ok) { setError(result.error); return; }
      router.push(`/author/quizzes/${result.value.id}`);
      router.refresh();
    } catch { setError("The save could not be confirmed. Your edits remain here. Reload to reconcile before retrying."); }
    finally { setPending(false); }
  }
  return <form onSubmit={submit} autoComplete="off">
    <h2>{quiz ? `Edit draft revision ${quiz.draftRevision}` : "Create a quiz"}</h2>
    <p>Save before previewing or publishing. Question revisions are pinned explicitly, never updated automatically.</p>
    <fieldset disabled={pending}>
      <legend>Quiz composition</legend>
      <label>Quiz title<input required maxLength={200} value={body.title}
        onChange={(event) => setBody({ ...body, title: event.target.value })} /></label>
      <label htmlFor="quiz-instructions">Instructions</label>
      <textarea id="quiz-instructions" maxLength={10000} value={body.instructions ?? ""}
        onChange={(event) => setBody({ ...body, instructions: event.target.value })} />
      <h3>Ordered selected revisions</h3>
      {selected.length === 0 && <p>No questions selected.</p>}
      <ol>{selected.map((item, index) => <li key={item.questionId}>
        <a href={`/author/questions/${item.questionId}/versions/${item.versionId}`} target="_blank" rel="noreferrer">
          Inspect selected question {index + 1}
        </a>
        <p>Question: <code>{item.questionId}</code>; pinned version: <code>{item.versionId}</code></p>
        <button type="button" onClick={() => updateVersion(index)}>Use latest revision for question {index + 1}</button>
        <label>Point override for question {index + 1}<input type="number" min={0} max={10000} step={1}
          value={item.pointOverride ?? ""} onChange={(event) => setBody({ ...body, questions: selected.map((entry, i) =>
            i === index ? { ...entry, pointOverride: event.target.value === "" ? null : Number(event.target.value) } : entry) })} /></label>
        <p>Leave blank to use this question revision&apos;s default points.</p>
        <button type="button" disabled={index === 0} onClick={() => move(index, -1)}>Move question {index + 1} up</button>
        <button type="button" disabled={index === selected.length - 1} onClick={() => move(index, 1)}>Move question {index + 1} down</button>
        <button type="button" onClick={() => setBody({ ...body, questions: selected.filter((_, i) => i !== index) })}>
          Remove question {index + 1}
        </button>
      </li>)}</ol>
      <h3>Available current revisions</h3>
      <label>Selection search text<input maxLength={4000} value={filters.text}
        onChange={(event) => setFilters({ ...filters, text: event.target.value })} /></label>
      <label>Selection category<input maxLength={100} value={filters.category}
        onChange={(event) => setFilters({ ...filters, category: event.target.value })} /></label>
      <label>Selection tag<input maxLength={50} value={filters.tag}
        onChange={(event) => setFilters({ ...filters, tag: event.target.value })} /></label>
      <label>Selection bank ID<input value={filters.bankId}
        onChange={(event) => setFilters({ ...filters, bankId: event.target.value })} /></label>
      <button type="button" onClick={() => loadChoices(null)}>Search available questions</button>
      {available.items.length === 0 && <p>Create questions in your question banks first.</p>}
      <ul>{available.items.map((item) => <li key={item.questionId}>
        <p className="plain-text">{item.promptExcerpt}</p>
        <p>{item.questionType}; revision {item.revision}; {item.defaultPoints} default points</p>
        <button type="button" disabled={selected.some((entry) => entry.questionId === item.questionId)}
          onClick={() => add({ questionId: item.questionId, versionId: item.versionId, pointOverride: null })}>
          Add revision {item.revision} of {item.promptExcerpt}
        </button>
      </li>)}</ul>
      {available.nextCursor && <button type="button" onClick={() => loadChoices(available.nextCursor)}>Next available questions</button>}
      {laterPage && <button type="button" onClick={() => loadChoices(null)}>First available questions</button>}
      <h3>Select an exact historical revision</h3>
      <p>Copy both IDs from a question revision page. Adding a revision does not save this draft.</p>
      <label>Question ID<input value={questionId} onChange={(event) => setQuestionId(event.target.value)} /></label>
      <label>Version ID<input value={versionId} onChange={(event) => setVersionId(event.target.value)} /></label>
      <button type="button" onClick={addExact}>Add exact revision</button>
      <PolicySettings policy={policy} onChange={(value) => setBody({ ...body, policy: value })} />
    </fieldset>
    <QuizError error={error} />
    <button disabled={pending}>{quiz ? "Save draft" : "Create quiz"}</button>
    <p role="status">{pending ? "Working..." : notice}</p>
  </form>;
}
