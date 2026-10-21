# Local synthetic identity setup

I01 supplies `realm.json` and the explicit `provision.py` command. Neither the API
nor the web process imports the provisioner or receives Keycloak administration
credentials. This is a loopback-only development runbook, not deployment or A01
account administration. The bootstrap administrator exists only in `master`;
it is never mapped to an application account.

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
| Disabled capabilities | Registration, implicit flow, direct password grants, service accounts, full-scope access |

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

## Explicit setup and provisioning

First bootstrap/migrate the local application database per
[`docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md). Use a dedicated local shell;
the root `.env` is for Compose and is not automatically loaded by Python.
Export nonempty, distinct local-only secrets without placing them in command
arguments or source control. The provisioner requires secrets of at least
16 characters.

| Provisioning-only variable | Purpose |
| --- | --- |
| `KEYCLOAK_LOCAL_ORIGIN` | Exact loopback HTTP origin, default `http://localhost:8080` |
| `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` | Explicit local `master` bootstrap administration; never an application identity |
| `QUEZO_OIDC_CLIENT_SECRET` | Injected into the new confidential client in memory; share only with the web server |
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
The API requires only database, issuer and API audience settings. The web needs
its own restricted database and confidential client settings, never admin access.
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
