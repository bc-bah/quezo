"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../lib/api/schema";
import { archiveBank, availableBanks, createQuestion, editQuestion, organizeQuestion, saveBank } from "./actions";

type Schemas = components["schemas"];
type Content = Omit<Schemas["QuestionCreate"], "bankId">;
type ErrorEnvelope = Schemas["ErrorEnvelope"];

function FormError({ error }: { error: ErrorEnvelope | string | null }) {
  if (!error) return null;
  if (typeof error === "string") return <p role="alert">{error}</p>;
  return <div role="alert">
    <p>{error.code === "DRAFT_REVISION_CONFLICT"
      ? "This question changed in another tab. Your edits have not been saved. Reload the current revision before editing again."
      : error.message}</p>
    {error.details && "fields" in error.details && error.details.fields.map((field, index) => <p key={index}>
      {field.path.join(".")}: {field.reason.replaceAll("_", " ")}
    </p>)}
    <p>Reference: {error.requestId}</p>
    {error.code === "DRAFT_REVISION_CONFLICT" && <button type="button"
      onClick={() => window.location.reload()}>Reload current question (discard local edits)</button>}
  </div>;
}

const interrupted = "The save could not be confirmed. Your edits are still here. Reload to check the saved state before retrying.";

export function BankForm({ bank }: { bank?: Schemas["Bank"] }) {
  const router = useRouter();
  const [name, setName] = useState(bank?.name ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ErrorEnvelope | string | null>(null);
  const [saved, setSaved] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true); setError(null); setSaved(false);
    try {
      const result = await saveBank(name, bank?.id);
      if (!result.ok) { setError(result.error); return; }
      setSaved(true);
      router.push(`/author/banks/${result.value.id}`);
      router.refresh();
    } catch { setError(interrupted); }
    finally { setPending(false); }
  }
  return <form onSubmit={submit} autoComplete="off">
    <h2>{bank ? "Edit bank name" : "Create a bank"}</h2>
    <label>Bank name<input name="name" value={name} onChange={(event) => setName(event.target.value)}
      required maxLength={100} disabled={pending} /></label>
    <FormError error={error} />
    <button disabled={pending}>{bank ? "Save bank name" : "Create bank"}</button>
    <p role="status">{pending ? "Saving bank..." : saved ? "Bank saved." : ""}</p>
  </form>;
}

export function QuestionForm({ bankId, initial, current }: {
  bankId: string; initial: Content; current?: Schemas["QuestionVersion"];
}) {
  const router = useRouter();
  const [body, setBody] = useState<Content>(initial);
  const [points, setPoints] = useState(String(initial.defaultPoints));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ErrorEnvelope | string | null>(null);
  function changeType(kind: Content["questionType"]) {
    if (kind === body.questionType) return;
    const options = (kind === "true_false" ? ["True", "False"] : ["", ""])
      .map((text) => ({ id: crypto.randomUUID(), text }));
    setBody({ ...body, questionType: kind, options, correctOptionId: options[0]!.id });
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!/^\d+$/.test(points) || Number(points) > 10000) {
      setError("Points must be a whole number from 0 to 10,000."); return;
    }
    setPending(true);
    const content = { ...body, defaultPoints: Number(points) };
    try {
      const result = current
        ? await editQuestion(current.questionId, { ...content, expectedRevision: current.revision })
        : await createQuestion({ ...content, bankId });
      if (!result.ok) { setError(result.error); return; }
      router.push(`/author/questions/${result.value.questionId}/versions/${result.value.versionId}`);
      router.refresh();
    } catch { setError(interrupted); }
    finally { setPending(false); }
  }
  return <form onSubmit={submit} autoComplete="off">
    <h2>{current ? `Edit revision ${current.revision}` : "Create a question"}</h2>
    <p>Plain text only, displayed literally. Saving an edit creates a new immutable revision.
      Changing type replaces the choices; unchanged choices keep their option IDs.</p>
    <fieldset disabled={pending}>
      <legend>Question content</legend>
      <label>Question type<select value={body.questionType}
        onChange={(event) => changeType(event.target.value === "true_false" ? "true_false" : "mcq")}>
        <option value="mcq">Single-answer MCQ</option><option value="true_false">True/false</option>
      </select></label>
      <label htmlFor="question-prompt">Prompt</label>
      <textarea id="question-prompt" value={body.prompt} required maxLength={4000}
        onChange={(event) => setBody({ ...body, prompt: event.target.value })} />
      <label>Default points<input type="number" min={0} max={10000} step={1} value={points} required
        onChange={(event) => setPoints(event.target.value)} /></label>
      <label>Category<input maxLength={100} value={body.category ?? ""}
        onChange={(event) => setBody({ ...body, category: event.target.value || null })} /></label>
      <fieldset><legend>Tags</legend>
        {(body.tags ?? []).map((tag, index) => <div key={index}>
          <label>Tag {index + 1}<input required maxLength={50} value={tag}
            onChange={(event) => setBody({ ...body, tags: (body.tags ?? []).map((item, i) =>
              i === index ? event.target.value : item) })} /></label>
          <button type="button" onClick={() => setBody({ ...body,
            tags: (body.tags ?? []).filter((_, i) => i !== index) })}>Remove tag {index + 1}</button>
        </div>)}
        <button type="button" disabled={(body.tags ?? []).length >= 20}
          onClick={() => setBody({ ...body, tags: [...(body.tags ?? []), ""] })}>Add tag</button>
      </fieldset>
      <fieldset>
        <legend>Choices and one correct answer</legend>
        {body.options.map((option, index) => <div key={option.id} className="question-option">
          <label>Option {index + 1}<input value={option.text} required maxLength={1000}
            readOnly={body.questionType === "true_false"}
            onChange={(event) => setBody({ ...body, options: body.options.map((item) =>
              item.id === option.id ? { ...item, text: event.target.value } : item) })} /></label>
          <label><input type="radio" name="correct" checked={body.correctOptionId === option.id}
            onChange={() => setBody({ ...body, correctOptionId: option.id })} required /> Correct option {index + 1}</label>
          {body.questionType === "mcq" && <button type="button" disabled={body.options.length <= 2}
            onClick={() => setBody({ ...body, options: body.options.filter((item) => item.id !== option.id),
              correctOptionId: body.correctOptionId === option.id ? "" : body.correctOptionId })}>
            Remove option {index + 1}
          </button>}
        </div>)}
        {body.questionType === "mcq" && <button type="button" disabled={body.options.length >= 10}
          onClick={() => setBody({ ...body, options: [...body.options, { id: crypto.randomUUID(), text: "" }] })}>
          Add option
        </button>}
      </fieldset>
      <label htmlFor="question-feedback">Explanatory feedback</label>
      <textarea id="question-feedback" maxLength={4000} value={body.feedback}
        onChange={(event) => setBody({ ...body, feedback: event.target.value })} />
    </fieldset>
    <FormError error={error} />
    <button disabled={pending}>{current ? "Save new revision" : "Create question"}</button>
    <p role="status">{pending ? "Saving question..." : ""}</p>
  </form>;
}

export function OrganizationControls({ bank, question, organization, banks }: {
  bank?: Schemas["Bank"]; question?: Schemas["QuestionVersion"];
  organization?: Schemas["Organization"]; banks?: Schemas["Page_Bank_"];
}) {
  const router = useRouter();
  const [choices, setChoices] = useState(banks);
  const [target, setTarget] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ErrorEnvelope | string | null>(null);
  async function archive() {
    setPending(true); setError(null);
    try {
      const result = bank ? await archiveBank(bank.id) : await organizeQuestion(question!.questionId);
      if (!result.ok) { setError(result.error); return; }
      router.refresh();
    } catch { setError("Archive could not be confirmed. Reload to inspect the saved state."); }
    finally { setPending(false); }
  }
  async function move() {
    setPending(true); setError(null);
    try {
      const result = await organizeQuestion(question!.questionId, {
        bankId: target, expectedRevision: question!.revision,
      });
      if (!result.ok) { setError(result.error); return; }
      router.refresh();
    } catch { setError("Move could not be confirmed. Reload to inspect the saved bank."); }
    finally { setPending(false); }
  }
  async function load(cursor: string | null) {
    setPending(true); setError(null);
    try {
      const result = await availableBanks(cursor);
      if (!result.ok) { setError(result.error); return; }
      setChoices(result.value); setTarget("");
    } catch { setError("Banks could not be loaded. The question has not been moved."); }
    finally { setPending(false); }
  }
  const archived = bank?.archived || organization?.archived;
  return <section><h2>Organization</h2>
    <p>Archiving excludes content from new selection. Existing drafts, publications, assignments and attempts retain their pinned history.
      Archiving a bank also excludes its questions from search and new selection.</p>
    {archived ? <p>This {bank ? "bank" : "question"} is archived and read-only.</p> : <>
      {question && choices && <fieldset disabled={pending}>
        <legend>Move between owned banks without changing question identity</legend>
        <label>Destination bank<select value={target} onChange={(event) => setTarget(event.target.value)}>
          <option value="">Select a bank</option>
          {choices.items.filter((item) => item.id !== question.bankId).map((item) =>
            <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
        {choices.nextCursor && <button type="button" onClick={() => load(choices.nextCursor)}>Next destination banks</button>}
        <button type="button" onClick={() => load(null)}>First destination banks</button>
        <button type="button" disabled={!target} onClick={move}>Move question</button>
      </fieldset>}
      <label><input type="checkbox" checked={confirmed} disabled={pending}
        onChange={(event) => setConfirmed(event.target.checked)} /> I understand history is retained when archiving</label>
      <button type="button" disabled={pending || !confirmed} onClick={archive}>Archive {bank ? "bank" : "question"}</button>
    </>}
    <FormError error={error} />
    <p role="status">{pending ? "Working..." : ""}</p>
  </section>;
}
