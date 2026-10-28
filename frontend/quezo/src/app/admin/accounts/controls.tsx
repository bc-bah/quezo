"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { components } from "../../../lib/api/schema";
import { changeRoles, provisionAccount, setAccountStatus } from "./actions";

type Schemas = components["schemas"];
type Role = Schemas["AccountRoleUpdate"]["roles"][number];
type Account = Schemas["AccountAdminView"];
type UiError = Schemas["ErrorEnvelope"] | string;
const roles: Role[] = ["administrator", "author", "learner"];

function ActionError({ error, retryHint }: { error: UiError | null; retryHint?: string }) {
  if (!error) return null;
  if (typeof error === "string") return <p role="alert">{error}</p>;
  return <div role="alert">
    <p>{error.message}</p><p>Reference: {error.requestId}</p>
    {retryHint && <p>{retryHint}</p>}
  </div>;
}

export function ProvisionForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [selected, setSelected] = useState<Role[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<UiError | null>(null);
  const [notice, setNotice] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true); setError(null); setNotice("");
    try {
      const result = await provisionAccount({ username, email: email || null, roles: selected });
      if (!result.ok) { setError(result.error); router.refresh(); return; }
      setUsername(""); setEmail(""); setSelected([]);
      setNotice("Account identity was provisioned disabled. Activate it when ready.");
      router.refresh();
    } catch {
      setError("The result could not be confirmed. Refresh before retrying.");
      router.refresh();
    } finally { setPending(false); }
  }

  return <form onSubmit={submit} autoComplete="off">
    <h2>Provision account</h2>
    <p>No password is collected or stored. New identities remain disabled until explicitly activated.</p>
    <fieldset disabled={pending}>
      <label>Username<input value={username} required minLength={3} maxLength={128}
        pattern="[A-Za-z0-9._@+-]+" onChange={(event) => setUsername(event.target.value)} /></label>
      <label>Email (optional)<input type="email" maxLength={254} value={email}
        onChange={(event) => setEmail(event.target.value)} /></label>
      <fieldset><legend>Application roles</legend>
        {roles.map((role) => <label key={role}>
          <input type="checkbox" checked={selected.includes(role)} onChange={(event) =>
            setSelected(event.target.checked ? [...selected, role] : selected.filter((item) => item !== role))} />
          {role}
        </label>)}
      </fieldset>
    </fieldset>
    <ActionError error={error}
      retryHint="The account remains disabled. Retry using the same username and profile." />
    <button disabled={pending}>{pending ? "Provisioning..." : "Provision disabled account"}</button>
    <p role="status">{notice}</p>
  </form>;
}

export function AccountControls({ account }: { account: Account }) {
  const router = useRouter();
  const [selected, setSelected] = useState<Role[]>(account.roles);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<UiError | null>(null);
  const [notice, setNotice] = useState("");

  async function updateRoleSelection() {
    setPending(true); setError(null); setNotice("");
    try {
      const result = await changeRoles(account.userId, selected);
      if (!result.ok) { setError(result.error); router.refresh(); return; }
      setNotice("Roles updated."); router.refresh();
    } catch {
      setError("The result could not be confirmed. Refresh before retrying.");
      router.refresh();
    } finally { setPending(false); }
  }

  async function changeStatus(action: "activate" | "deactivate") {
    setPending(true); setError(null); setNotice("");
    try {
      const result = await setAccountStatus(account.userId, action);
      if (!result.ok) { setError(result.error); router.refresh(); return; }
      setNotice(action === "activate" ? "Account activated." : "Application access revoked.");
      router.refresh();
    } catch {
      setError("The result could not be confirmed. Refresh before retrying.");
      router.refresh();
    } finally { setPending(false); }
  }

  async function retryProvision() {
    if (!account.username || account.provisioningState !== "failed") return;
    setPending(true); setError(null); setNotice("");
    try {
      const result = await provisionAccount({
        username: account.username, email: account.email, roles: account.roles,
      });
      if (!result.ok) { setError(result.error); router.refresh(); return; }
      setNotice("Provisioning completed; the account remains disabled.");
      router.refresh();
    } catch {
      setError("The result could not be confirmed. Refresh before retrying.");
      router.refresh();
    } finally { setPending(false); }
  }

  return <section aria-label={`Manage ${account.username ?? account.userId}`}>
    <h3>{account.username ?? "Account"} {account.email ? `(${account.email})` : ""}</h3>
    <p>Status: {account.status}; roles: {account.roles.join(", ") || "none"}</p>
    <p>Provisioning: {account.provisioningState}; identity sync: {account.identitySyncState}</p>
    {account.provisioningErrorCode && <p>Provisioning error: {account.provisioningErrorCode}</p>}
    {account.identityErrorCode && <p>Identity sync error: {account.identityErrorCode}</p>}
    {account.provisioningState === "failed" && <button disabled={pending} onClick={retryProvision}>
      Retry provisioning
    </button>}
    {account.provisioningState === "complete" && <>
      <fieldset disabled={pending}>
        <legend>Application roles</legend>
        {roles.map((role) => <label key={role}>
          <input type="checkbox" checked={selected.includes(role)} onChange={(event) =>
            setSelected(event.target.checked ? [...selected, role] : selected.filter((item) => item !== role))} />
          {role}
        </label>)}
      </fieldset>
      <button disabled={pending} onClick={updateRoleSelection}>Save roles</button>
      {account.status === "active"
        ? <button disabled={pending} onClick={() => changeStatus("deactivate")}>Deactivate</button>
        : <button disabled={pending} onClick={() => changeStatus("activate")}>Activate</button>}
    </>}
    <ActionError error={error} /><p role="status">{pending ? "Saving..." : notice}</p>
  </section>;
}
