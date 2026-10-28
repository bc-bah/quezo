import type { components } from "../../../lib/api/schema";
import { apiData } from "../../../lib/server/questions";
import { accountClient } from "../../../lib/server/accounts";
import { publicError } from "../../../lib/server/errors";
import { AccountControls, ProvisionForm } from "./controls";

export const dynamic = "force-dynamic";

type Account = components["schemas"]["AccountAdminView"];

export default async function AccountsPage() {
  try {
    const client = await accountClient();
    const page = await apiData(client.GET("/api/v1/admin/accounts"));
    return <main id="main" tabIndex={-1}>
      <nav aria-label="Account administration navigation"><a href="/">Home</a></nav>
      <h1>Account administration</h1>
      <p>Administrators manage application roles and access only; assessment answers are not available here.</p>
      <ProvisionForm />
      <h2>Accounts</h2>
      {page.items.length ? <ul>{page.items.map((account: Account) =>
        <li key={account.userId}><AccountControls account={account} /></li>)}</ul> : <p>No accounts are listed.</p>}
    </main>;
  } catch (error) {
    const safe = publicError(error);
    return <main id="main" tabIndex={-1}><nav><a href="/">Home</a></nav>
      <h1>Account administration</h1><p role="alert">{safe.envelope.message}</p>
      <p>Reference: {safe.envelope.requestId}</p>
    </main>;
  }
}
