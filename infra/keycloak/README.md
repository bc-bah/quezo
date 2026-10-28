# Local synthetic identity setup

I01 supplies `realm.json` and the explicit `provision.py` command. The API never
receives the bootstrap `master` administrator credentials. A01's API receives
only the dedicated local `quezo-account-admin` client secret; the web process
never receives it. This is a loopback-only development runbook, not deployment.
The bootstrap administrator exists only in `master`; it is never mapped to an
application account.

For the all-container Docker Desktop workflow, use the
[full-app startup instructions](../../docs/DEVELOPMENT.md#full-app-with-docker-desktop).
Its explicit `provision` tool runs this same provisioner in the local stack's
shared loopback network; no runtime provisioning or automatic grants are added.

The [second-wave DEC-06/07 approval](../../docs/SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01)
selected openid-client and pg for F03, and PyJWT with cryptography plus HTTPX for
I01. Both packages are now merged; I02 owns the combined real-browser proof,
not new runtime administration privileges.

## Realm and F03 client contract

| Setting | Value |
| --- | --- |
| Keycloak image | `quay.io/keycloak/keycloak:26.4.7`, `start-dev` |
| Realm / default issuer | `quezo-local` / `http://localhost:8080/realms/quezo-local` |
| Web client | `quezo-web`, confidential, client-secret authentication |
| Login | Authorization code only; S256 PKCE required; F03 owns state/nonce validation |
| Exact redirect | `http://localhost:3000/auth/callback` |
| Exact web origin / registered post-logout URI | `http://localhost:3000` / `http://localhost:3000` |
| Scope / access-token audience | `openid quezo-api` / `quezo-api` |
| Signing / access-token lifetime | RS256 / 300 seconds |
| Web client disabled capabilities | Registration, implicit flow, direct password grants, service accounts, full-scope access |
| A01 client | Separate confidential client; service account enabled, full-scope access disabled |

The optional `quezo-api` client scope supplies **both** the audience mapper and
Keycloak 26's access-token `sub` mapper. Omitting the latter can produce an
otherwise correctly signed access token without a subject; the API correctly
rejects it. No identity/profile/email/role claims are needed for API access.
Realm role names are labels only and are not automatically assigned or trusted.

F03 uses local Quezo logout: it deletes the durable local session and does not
invoke global Keycloak logout. The exact post-logout URI is registered for
compatibility, not a claim that F03 performs SSO logout. Do not add wildcards or
change F03's redirect/session behavior. To use another web origin, coordinate
an explicit exact-URI configuration change; there is no runtime redirect input.

## A01 local account-administration service

The verified local Keycloak 26.4.7 installation uses a separate confidential
`quezo-account-admin` service client with service accounts enabled and
`fullScopeAllowed=false`. Its service account is scoped to
`realm-management/query-users` and `view-users`; the latter transitively includes
read-only `query-groups`. Fine-grained admin permissions are enabled. A client
policy targeting only this service client grants `view` and `manage` on the
`Users` resource type. A user policy is not sufficient for the
client-credentials request context. No `manage-users`, role-mapping, group
mutation, client or realm administration role is assigned.

The approved Keycloak `manage` scope still includes deletion/password-reset
effects. The Quezo API deliberately has no delete, password or credential-reset
operation. The secret is generated into ignored `.env.docker`, passed only to
the API, and never goes to the web process or browser. The service fails closed
when this local configuration is absent. Realm bootstrap does not provision
application credentials; account identities start disabled and no password is
collected or stored. The local operator must use an independently controlled
Keycloak credential process before an account can sign in.

Before using A01 against any local realm, verify the client identity and exact
effective policy/role mapping against this table. Do not copy this permission
set to a shared or production realm without a separate approval. `view-users`
is an explicit B.C. approval and is not an implicit grant for query-groups.

## Explicit setup and provisioning

First bootstrap/migrate the local application database per
[`docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md). Use a dedicated local shell;
the root `.env` is for Compose and is not automatically loaded by Python.
Export nonempty, distinct local-only secrets without placing them in command
arguments or source control. Provisioning-only secrets require at least 16
characters; the generated A01 client secret must match the configured client.

Realm import and the existing synthetic provisioner do not create or grant the
A01 service identity. That is a separate explicit local setup operation. Before
starting A01, create/verify the exact client and permission rows in the A01
configuration table above; the API does not bootstrap or broaden those grants.
`Initialize-Local.ps1` stores a fresh service secret in ignored `.env.docker`,
and `compose.local.yaml` passes it only to the API. If the client/policy is
absent, A01 calls fail closed rather than falling back to the master user.

| Local-only variable | Purpose |
| --- | --- |
| `KEYCLOAK_LOCAL_ORIGIN` | Exact loopback HTTP origin, default `http://localhost:8080` |
| `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` | Explicit local `master` bootstrap administration; never an application identity |
| `QUEZO_OIDC_CLIENT_SECRET` | Injected into the new confidential client in memory; share only with the web server |
| `QUEZO_ACCOUNT_ADMIN_CLIENT_ID`, `QUEZO_ACCOUNT_ADMIN_CLIENT_SECRET` | Dedicated local A01 service identity; the client secret goes to the API only |
| `QUEZO_SYNTHETIC_PASSWORD` | Password for the selected synthetic account; choose a distinct value per account |
| `QUEZO_DATABASE_URL` | Restricted `quezo_runtime` URL to the local migrated database; no migration/admin DB credential |
| `QUEZO_OIDC_ISSUER` | Must exactly equal the local origin plus `/realms/quezo-local` |

From the repository root:

```powershell
docker compose --profile identity up -d keycloak
curl.exe --fail --silent --output NUL http://localhost:8080/realms/master/.well-known/openid-configuration
uv run --directory postgres --locked python ..\infra\keycloak\provision.py --confirm-local-synthetic --setup-realm
uv run --directory postgres --locked python ..\infra\keycloak\provision.py --confirm-local-synthetic --account administrator
uv run --directory postgres --locked python ..\infra\keycloak\provision.py --confirm-local-synthetic --account author
uv run --directory postgres --locked python ..\infra\keycloak\provision.py --confirm-local-synthetic --account learner
```

For POSIX shells use the corresponding path separators and `/dev/null` instead
of `NUL`. Wait for discovery HTTP 200; container startup alone is not readiness.
Realm creation refuses an existing realm; it never overwrites an existing
client/realm. It configures admin-only unmanaged attributes for the synthetic
provisioning marker. A partially failed realm setup has no application grants:
inspect/repair that dedicated local realm explicitly rather than deleting
volumes or blindly rerunning imports.

The only supported account selectors are:

| Selector | Keycloak username | Application roles |
| --- | --- | --- |
| `administrator` | `quezo-test-administrator` | administrator only |
| `author` | `quezo-test-author` | author only |
| `learner` | `quezo-test-learner` | learner only |
| `combined` | `quezo-test-combined` | author and learner |
| `empty` | `quezo-test-empty` | none |

These are synthetic users, with synthetic names and reserved `example.invalid`
email addresses to satisfy Keycloak's profile requirements. No email is sent.
There is no arbitrary username, subject, role, or activation input. Creation
starts disabled, sets the credential, enables the user and reads back its identity
before committing an application grant. Keycloak generates the subject; the
adapter never assumes that a caller-supplied ID will be honored.

Application provisioning is one `Database.transaction()` under an advisory lock.
It records the verified `(issuer, subject)`, current roles and active status only
after identity operations succeed. Synthetic application UUIDs are deterministic
UUIDv5 values scoped to issuer and allowlisted fixture name, separate from
Keycloak subjects; they identify explicit local provisioning retries, not login.
An existing application account is always refused, even if disabled or stripped
of roles. First-admin bootstrap also refuses another active administrator.
It cannot restore revoked privileges or replace an existing mapping.

On identity/database/cancellation failure, no new eligible application grant is
committed. A Keycloak-only user may remain; the same explicit command can retry
only the marked synthetic identity. A foreign/unmarked existing user is refused.
An already committed application grant requires reviewed account management,
not this bootstrap. Runtime login never provisions anything. Safe command output
contains only outcome/code and, on success, application UUID; no tokens/passwords.
The local operator is the provisioning actor; full A01 audit/admin operations
and last-admin mutation protection remain A01 work (this command removes none).

Remove administration and synthetic-password variables from application shells.
The API requires its restricted database, issuer, API audience and dedicated
account-administration service-client settings for A01; it never receives the
bootstrap administrator credentials. The web needs its own restricted database
and confidential client settings, never A01 or master administration access.
No application passwords are stored in PostgreSQL.

## Isolated actual Keycloak check

`keycloak-test` uses tmpfs storage, a separate loopback port and the `identity-test`
profile; it never shares the development `keycloak-data` volume. Use the isolated
PostgreSQL variables from the development runbook and distinct synthetic
Keycloak/client/account secrets. Set `KEYCLOAK_TEST_PORT=58080` and
`KEYCLOAK_LOCAL_ORIGIN=http://localhost:58080`, then:

```powershell
docker compose -p quezo-i01-test --profile test --profile identity-test up -d --wait postgres-test keycloak-test
curl.exe --fail --silent --output NUL http://localhost:58080/realms/master/.well-known/openid-configuration
npm run test:identity:integration
docker compose -p quezo-i01-test --profile test --profile identity-test rm -s -f postgres-test keycloak-test
```

The explicit test refuses the default development port or an existing realm,
creates its own realm, and deletes only that creation on completion. A test
interrupted after creation may require removing/recreating just its disposable
Keycloak service. Never delete a development realm to make a test pass.
It uses real code+PKCE exchange, actual JWT/JWKS and real isolated PostgreSQL;
it proves all role combinations, empty roles, ID-token rejection, role/status
revocation with old tokens and refusal of provisioning replay/password grants.
HTTPX's cookie jar does not implement browsers' localhost Secure-cookie exception,
so the test replays only the returned login cookies to the exact local provider.
It is **not** a real browser or F03-facade test; I02 owns that combined gate.

Local file-backed Keycloak, HTTP loopback and these accounts are not production
configuration. Shared deployment requires TLS, durable supported identity
storage, managed secrets, recovery/retention policy and separate approval.
