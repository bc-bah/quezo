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
