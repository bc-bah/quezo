"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api/schema";
import { readAttempt, saveResponse } from "../../actions";

type S = components["schemas"];
type Pending = { command: S["SaveCommand"]; edit: number };
type Item = {
  response: S["SavedResponse"];
  value: string | null;
  edit: number;
  acknowledgedEdit: number;
  pending?: Pending | undefined;
  busy: boolean;
  needsReconcile: boolean;
  conflict: boolean;
  status: string;
};

export function ResponseEditor({ attempt }: { attempt: S["Attempt"] }) {
  const [items, setItems] = useState<Record<string, Item>>(() => Object.fromEntries(
    attempt.questions.map((q) => [q.attemptQuestionId, {
      response: q.response, value: q.response.selectedOptionId, edit: 0, acknowledgedEdit: 0,
      busy: false, needsReconcile: false, conflict: false,
      status: q.response.revision ? "Saved" : "Unanswered",
    }]),
  ));
  const current = useRef(items);
  const [state, setState] = useState(attempt.state);
  const [blocked, setBlocked] = useState(false);
  const [notice, setNotice] = useState("");
  const [reconciling, setReconciling] = useState(false);
  const reconciliation = useRef(false);
  const [offline, setOffline] = useState(false);
  const change = useCallback((id: string, update: Partial<Item>) => {
    current.current = { ...current.current, [id]: { ...current.current[id]!, ...update } };
    setItems(current.current);
  }, []);
  const dirty = Object.values(items).some((item) => item.edit !== item.acknowledgedEdit || item.pending || item.busy);

  function edit(id: string, value: string | null) {
    const item = current.current[id]!;
    change(id, { value, edit: item.edit + 1,
      status: item.conflict ? item.status : item.busy ? "Saving an earlier edit; newer input is unsaved." : "Unsaved" });
  }

  const reconcile = useCallback(async () => {
    if (reconciliation.current || Object.values(current.current).some((item) => item.busy)) return;
    reconciliation.current = true;
    setReconciling(true);
    setNotice("Checking persisted answers before retrying.");
    try {
      const result = await readAttempt(attempt.id);
      if (!result.ok) {
        setNotice(result.error.message + " Local edits remain unsaved. Reconcile before retrying.");
        for (const id of Object.keys(current.current)) change(id, { needsReconcile: true });
        return;
      }
      setState(result.value.state);
      for (const question of result.value.questions) {
        const id = question.attemptQuestionId;
        const item = current.current[id]!;
        const response = question.response;
        // An uncertain command must keep its original revision/key until replay resolves it.
        if (item.pending) {
          change(id, { needsReconcile: false, status: "Unsaved - persisted state checked; retry to resolve the previous save." });
        } else if (response.revision !== item.response.revision && item.edit !== item.acknowledgedEdit) {
          change(id, { response, conflict: true, needsReconcile: false, status: "Conflict - another session saved an answer. Your edit is unsaved." });
        } else if (item.edit === item.acknowledgedEdit) {
          change(id, { response, value: response.selectedOptionId, needsReconcile: false, conflict: false,
            status: response.revision ? "Saved" : "Unanswered" });
        } else {
          change(id, { needsReconcile: false, status: item.conflict ? item.status : "Unsaved - persisted state checked." });
        }
      }
      setNotice("Persisted answers reconciled. Local unsaved edits have been preserved.");
    } catch {
      setNotice("Connection failed. Local edits remain unsaved. Reconcile before retrying.");
      for (const id of Object.keys(current.current)) change(id, { needsReconcile: true });
    } finally {
      reconciliation.current = false;
      setReconciling(false);
    }
  }, [attempt.id, change]);

  useEffect(() => {
    const disconnected = () => {
      setOffline(true);
      setNotice("Offline - local edits are not saved.");
      for (const id of Object.keys(current.current)) change(id, { needsReconcile: true });
    };
    const connected = () => { setOffline(false); void reconcile(); };
    const resumed = () => { if (document.visibilityState === "visible") void reconcile(); };
    if (!navigator.onLine) disconnected();
    window.addEventListener("offline", disconnected);
    window.addEventListener("online", connected);
    window.addEventListener("focus", resumed);
    document.addEventListener("visibilitychange", resumed);
    return () => {
      window.removeEventListener("offline", disconnected);
      window.removeEventListener("online", connected);
      window.removeEventListener("focus", resumed);
      document.removeEventListener("visibilitychange", resumed);
    };
  }, [change, reconcile]);

  useEffect(() => {
    if (!dirty) return;
    const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const navigate = (event: MouseEvent) => {
      const link = event.target instanceof Element ? event.target.closest("a") : null;
      if (link && !link.getAttribute("href")?.startsWith("#")
        && !window.confirm("Leave this attempt and discard unsaved local edits?")) {
        event.preventDefault(); event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", unload);
    document.addEventListener("click", navigate, true);
    return () => {
      window.removeEventListener("beforeunload", unload);
      document.removeEventListener("click", navigate, true);
    };
  }, [dirty]);

  async function save(id: string) {
    const item = current.current[id]!;
    if (item.busy || item.conflict || offline || reconciliation.current
      || ((blocked || state !== "in_progress") && !item.pending)) return;
    if (item.needsReconcile) { await reconcile(); return; }
    const pending = item.pending ?? {
      edit: item.edit,
      command: { requestId: crypto.randomUUID(), expectedRevision: item.response.revision, selectedOptionId: item.value },
    };
    change(id, { busy: true, pending, status: "Saving" });
    try {
      const result = await saveResponse(attempt.id, id, pending.command);
      if (!result.ok) {
        const details = result.error.details;
        if (result.error.code === "RESPONSE_REVISION_CONFLICT" && details && "currentRevision" in details) {
          change(id, { pending: undefined, conflict: true, response: {
            revision: details.currentRevision, selectedOptionId: details.selectedOptionId, savedAt: details.savedAt,
          }, status: "Conflict - another session saved an answer. Your edit is unsaved." });
        } else {
          const terminal = result.error.code === "ATTEMPT_FINALIZED" || result.error.code === "DEADLINE_PASSED";
          if (terminal) setBlocked(true);
          if (details && "attemptState" in details) setState(details.attemptState);
          change(id, { pending: terminal ? undefined : pending, needsReconcile: true,
            status: result.error.message + " Your edit is not confirmed saved." });
        }
        return;
      }
      const ack = result.value.acknowledgement;
      if (ack.requestId !== pending.command.requestId || ack.responseRevision !== pending.command.expectedRevision + 1) {
        change(id, { needsReconcile: true, status: "Invalid save acknowledgement. Your edit is not confirmed saved." });
        return;
      }
      setState(result.value.attemptState);
      change(id, { response: { selectedOptionId: pending.command.selectedOptionId, revision: ack.responseRevision, savedAt: ack.savedAt },
        acknowledgedEdit: pending.edit, pending: undefined,
        status: current.current[id]!.edit === pending.edit ? "Saved" : "Unsaved - a newer edit has not been saved." });
      // Replay can acknowledge an older revision; refresh before any subsequent command.
      if (item.pending) change(id, { needsReconcile: true });
    } catch {
      change(id, { needsReconcile: true, status: "Connection failed - save outcome unknown. Your edit is not confirmed saved." });
    } finally {
      change(id, { busy: false });
    }
  }

  return <>
    <p>Attempt state: {state.replaceAll("_", " ")}</p>
    <p>Choose an answer, then save it. Submission is not available yet.</p>
    <p role="status" aria-live="polite">{offline ? "Offline. " : ""}{notice}</p>
    {state !== "in_progress" || blocked ? <p role="alert">This attempt no longer accepts new answers. Unsaved local edits cannot be submitted.</p> : null}
    {dirty && <p>Unsaved local edits will be lost if you leave or close this page.</p>}
    <button type="button" onClick={() => void reconcile()} disabled={reconciling || offline || Object.values(items).some((i) => i.busy)}>
      {reconciling ? "Reconciling" : "Reconcile saved answers"}
    </button>
    <nav aria-label="Questions">{attempt.questions.map((q, index) =>
      <a key={q.attemptQuestionId} href={`#question-${q.attemptQuestionId}`}>Question {index + 1} </a>)}</nav>
    <ol>{attempt.questions.map((question, index) => {
      const id = question.attemptQuestionId;
      const item = items[id]!;
      return <li key={id} data-question-id={id} id={`question-${id}`} tabIndex={-1}>
        <fieldset disabled={state !== "in_progress" || blocked}>
          <legend className="plain-text">Question {index + 1}: {question.prompt}</legend>
          <p>{question.effectivePoints} points</p>
          {question.options.map((option) => <label key={option.id} data-option-id={option.id} className="plain-text">
            <input type="radio" name={id} value={option.id} checked={item.value === option.id} onChange={() => edit(id, option.id)} />
            {option.text}
          </label>)}
          <button type="button" onClick={() => edit(id, null)}>
            Clear answer
          </button>
        </fieldset>
        <button type="button" disabled={item.busy || item.conflict || offline || reconciling
          || ((state !== "in_progress" || blocked) && !item.pending) || (item.edit === item.acknowledgedEdit && !item.pending)}
          onClick={() => void save(id)}>{item.busy ? "Saving" : item.pending ? "Retry save" : "Save answer"}</button>
        <p role="status" aria-live="polite">{item.status}</p>
        {item.conflict && <div role="alert">
          <p>Persisted answer: {question.options.find((o) => o.id === item.response.selectedOptionId)?.text ?? "Unanswered"}.
            Choose explicitly; neither tab silently overwrites the other.</p>
          <button type="button" onClick={() => change(id, { value: item.response.selectedOptionId, acknowledgedEdit: item.edit,
            conflict: false, status: "Saved" })}>Use persisted answer</button>
          <button type="button" disabled={state !== "in_progress" || blocked} onClick={() =>
            change(id, { conflict: false, status: "Unsaved - local answer kept. Save explicitly to replace the persisted answer." })}>Keep my local answer</button>
        </div>}
      </li>;
    })}</ol>
  </>;
}
