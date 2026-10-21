"use server";

import type { components } from "../../../lib/api/schema";
import { apiData, questionClient } from "../../../lib/server/questions";
import { publicError } from "../../../lib/server/errors";
import type { ActionResult } from "../actions";

type S = components["schemas"];

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

export async function availableQuestions(cursor: string | null): Promise<ActionResult<S["Page_QuestionSummary_"]>> {
  try {
    const client = await questionClient();
    return { ok: true, value: await apiData(client.GET("/api/v1/questions", { params: { query: { cursor } } })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function exactQuestion(questionId: string, versionId: string): Promise<ActionResult<S["QuestionVersion"]>> {
  try {
    const client = await questionClient();
    return { ok: true, value: await apiData(client.GET("/api/v1/questions/{question_id}/versions/{version_id}", {
      params: { path: { question_id: questionId, version_id: versionId } },
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}
