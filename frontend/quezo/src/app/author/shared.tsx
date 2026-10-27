import type { ReactNode } from "react";
import type { components } from "../../lib/api/schema";
import { publicError } from "../../lib/server/errors";

export function AuthorPage({ children }: { children: ReactNode }) {
  return <main id="main" tabIndex={-1}>
    <nav aria-label="Author navigation"><a href="/">Home</a><a href="/author">Question banks</a><a href="/author/questions">Search questions</a><a href="/author/quizzes">Quizzes</a></nav>
    {children}
  </main>;
}

export function AuthorError({ error }: { error: unknown }) {
  const safe = publicError(error);
  return <AuthorPage><h1>Request not completed</h1>
    <p role="alert">{safe.envelope.message}</p>
    <p>Reference: {safe.envelope.requestId}</p>
    <a href="/">Return home or sign in</a>
  </AuthorPage>;
}

export function QuestionList({ items }: { items: components["schemas"]["QuestionSummary"][] }) {
  return items.length ? <ul>{items.map((item) => <li key={item.versionId}>
    <p className="plain-text">{item.promptExcerpt}</p>
    <p>{item.questionType === "mcq" ? "Single-answer MCQ" : "True/false"}; {item.defaultPoints} points; revision {item.revision}</p>
    <p>Category: {item.category ?? "None"}; tags: {(item.tags ?? []).join(", ") || "None"}</p>
    {(item.archived || item.bankArchived) && <p>Archived content: retained history only; unavailable for new selection.</p>}
    <a href={`/author/questions/${item.questionId}`}>Read or edit question</a>{" | "}
    <a href={`/author/questions/${item.questionId}/versions/${item.versionId}`}>Select revision {item.revision}</a>
  </li>)}</ul> : <p>No questions yet.</p>;
}
