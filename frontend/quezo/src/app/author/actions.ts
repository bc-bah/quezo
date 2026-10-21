"use server";

import type { components } from "../../lib/api/schema";
import { apiData, questionClient } from "../../lib/server/questions";
import { publicError, type ErrorEnvelope } from "../../lib/server/errors";

export type ActionResult<T> = { ok: true; value: T } | { ok: false; error: ErrorEnvelope };
type Schemas = components["schemas"];

export async function saveBank(
  name: string, id?: string,
): Promise<ActionResult<Schemas["Bank"]>> {
  try {
    const client = await questionClient(true);
    const value = id
      ? await apiData(client.PATCH("/api/v1/question-banks/{bank_id}", {
        params: { path: { bank_id: id } }, body: { name },
      }))
      : await apiData(client.POST("/api/v1/question-banks", { body: { name } }));
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error: publicError(error).envelope };
  }
}

export async function createQuestion(
  body: Schemas["QuestionCreate"],
): Promise<ActionResult<Schemas["QuestionVersion"]>> {
  try {
    const client = await questionClient(true);
    return { ok: true, value: await apiData(client.POST("/api/v1/questions", { body })) };
  } catch (error) {
    return { ok: false, error: publicError(error).envelope };
  }
}

export async function editQuestion(
  id: string, body: Schemas["QuestionEdit"],
): Promise<ActionResult<Schemas["QuestionVersion"]>> {
  try {
    const client = await questionClient(true);
    return { ok: true, value: await apiData(client.PATCH("/api/v1/questions/{question_id}", {
      params: { path: { question_id: id } }, body,
    })) };
  } catch (error) {
    return { ok: false, error: publicError(error).envelope };
  }
}
