"use server";

import type { components } from "../../../lib/api/schema";
import { accountClient } from "../../../lib/server/accounts";
import { apiData } from "../../../lib/server/questions";
import { publicError, type ErrorEnvelope } from "../../../lib/server/errors";

type Schemas = components["schemas"];
export type AccountAction<T> = { ok: true; value: T } | { ok: false; error: ErrorEnvelope };

export async function provisionAccount(
  body: Schemas["AccountProvisionRequest"],
): Promise<AccountAction<Schemas["AccountAdminView"]>> {
  try {
    const client = await accountClient(true);
    return { ok: true, value: await apiData(client.POST("/api/v1/admin/accounts", { body })) };
  } catch (error) {
    return { ok: false, error: publicError(error).envelope };
  }
}

export async function changeRoles(
  id: string, roles: Schemas["AccountRoleUpdate"]["roles"],
): Promise<AccountAction<Schemas["AccountAdminView"]>> {
  try {
    const client = await accountClient(true);
    return { ok: true, value: await apiData(client.PUT("/api/v1/admin/accounts/{account_id}/roles", {
      params: { path: { account_id: id } }, body: { roles },
    })) };
  } catch (error) {
    return { ok: false, error: publicError(error).envelope };
  }
}

export async function setAccountStatus(
  id: string, action: "activate" | "deactivate",
): Promise<AccountAction<Schemas["AccountAdminView"]>> {
  try {
    const client = await accountClient(true);
    const value = action === "activate"
      ? await apiData(client.POST("/api/v1/admin/accounts/{account_id}/activate", {
        params: { path: { account_id: id } },
      }))
      : await apiData(client.POST("/api/v1/admin/accounts/{account_id}/deactivate", {
        params: { path: { account_id: id } },
      }));
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error: publicError(error).envelope };
  }
}
