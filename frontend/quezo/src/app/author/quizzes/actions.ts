"use server";

import type { components } from "../../../lib/api/schema";
import { apiData, questionClient } from "../../../lib/server/questions";
import { failure, publicError } from "../../../lib/server/errors";
import type { ActionResult } from "../actions";

type S = components["schemas"];

export async function assignLearner(body: S["AssignmentCreate"]): Promise<ActionResult<S["Assignment"]>> {
  try {
    const client = await questionClient(true);
    return { ok: true, value: await apiData(client.POST("/api/v1/assignments", { body })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function eligibleLearners(cursor: string | null): Promise<ActionResult<S["Page_EligibleLearner_"]>> {
  try {
    const client = await questionClient();
    return { ok: true, value: await apiData(client.GET("/api/v1/eligible-learners", { params: { query: { cursor } } })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function saveQuiz(body: S["QuizComposition"], target?: {
  id: string; expectedRevision: number;
}): Promise<ActionResult<S["Quiz"]>> {
  try {
    const client = await questionClient(true);
    const value = target
      ? await apiData(client.PATCH("/api/v1/quizzes/{quiz_id}", {
        params: { path: { quiz_id: target.id } }, body: { ...body, expectedRevision: target.expectedRevision },
      }))
      : await apiData(client.POST("/api/v1/quizzes", { body }));
    return { ok: true, value };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function publishQuiz(id: string, expectedRevision: number, key: string):
Promise<ActionResult<S["PublishAcknowledgement"]>> {
  try {
    const client = await questionClient(true);
    return { ok: true, value: await apiData(client.POST("/api/v1/quizzes/{quiz_id}/publish", {
      params: { path: { quiz_id: id }, header: { "idempotency-key": key } }, body: { expectedRevision },
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function createRevision(id: string, expectedRevision: number): Promise<ActionResult<S["Quiz"]>> {
  try {
    const client = await questionClient(true);
    return { ok: true, value: await apiData(client.POST("/api/v1/quizzes/{quiz_id}/drafts", {
      params: { path: { quiz_id: id } }, body: { expectedRevision },
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function availableQuestions(cursor: string | null, filters?: {
  text: string | null; category: string | null; tag: string | null; bankId: string | null;
}): Promise<ActionResult<S["Page_QuestionSummary_"]>> {
  try {
    const client = await questionClient();
    return { ok: true, value: await apiData(client.GET("/api/v1/questions", { params: { query: { cursor, ...filters } } })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function exactQuestion(questionId: string, versionId?: string): Promise<ActionResult<S["QuestionVersion"]>> {
  try {
    const client = await questionClient();
    const organization = await apiData(client.GET("/api/v1/questions/{question_id}/organization", {
      params: { path: { question_id: questionId } },
    }));
    if (organization.archived || organization.bankArchived) {
      throw failure(409, "INVALID_STATE", "Archived content cannot enter a new selection. Existing pinned selections retain their history.");
    }
    const value = versionId !== undefined
      ? await apiData(client.GET("/api/v1/questions/{question_id}/versions/{version_id}", {
        params: { path: { question_id: questionId, version_id: versionId } },
      }))
      : await apiData(client.GET("/api/v1/questions/{question_id}", {
        params: { path: { question_id: questionId } },
      }));
    return { ok: true, value };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function transitionQuiz(id: string, expectedRevision: number, target: "close" | "archive"):
Promise<ActionResult<S["Quiz"]>> {
  try {
    const client = await questionClient(true);
    const options = { params: { path: { quiz_id: id } }, body: { expectedRevision } };
    const value = target === "close"
      ? await apiData(client.POST("/api/v1/quizzes/{quiz_id}/close", options))
      : await apiData(client.POST("/api/v1/quizzes/{quiz_id}/archive", options));
    return { ok: true, value };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}
