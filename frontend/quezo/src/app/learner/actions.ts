"use server";

import type { components } from "../../lib/api/schema";
import { apiData, assessmentClient } from "../../lib/server/questions";
import { publicError } from "../../lib/server/errors";
import type { ActionResult } from "../author/actions";

export async function startAttempt(assignmentId: string, key: string):
Promise<ActionResult<components["schemas"]["Attempt"]>> {
  try {
    const client = await assessmentClient("learner", true);
    return { ok: true, value: await apiData(client.POST("/api/v1/assignments/{assignment_id}/attempts", {
      params: { path: { assignment_id: assignmentId }, header: { "idempotency-key": key } }, body: {},
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function readAttempt(attemptId: string): Promise<ActionResult<components["schemas"]["Attempt"]>> {
  try {
    const client = await assessmentClient("learner");
    return { ok: true, value: await apiData(client.GET("/api/v1/attempts/{attempt_id}", {
      params: { path: { attempt_id: attemptId } },
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function saveResponse(attemptId: string, questionId: string, body: components["schemas"]["SaveCommand"]):
Promise<ActionResult<components["schemas"]["SaveResult"]>> {
  try {
    const client = await assessmentClient("learner", true);
    return { ok: true, value: await apiData(client.PUT("/api/v1/attempts/{attempt_id}/responses/{question_id}", {
      params: { path: { attempt_id: attemptId, question_id: questionId } }, body,
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}

export async function submitAttempt(attemptId: string): Promise<ActionResult<components["schemas"]["Completion"]>> {
  try {
    const client = await assessmentClient("learner", true);
    return { ok: true, value: await apiData(client.POST("/api/v1/attempts/{attempt_id}/submission", {
      params: { path: { attempt_id: attemptId } }, body: {},
    })) };
  } catch (error) { return { ok: false, error: publicError(error).envelope }; }
}
