# Keycloak development placeholder

Compose can start a local Keycloak instance, but it does not create a Quezo realm,
client, roles, users, or application integration. The bootstrap administrator is
not a Quezo application user.

After architecture approval, agree on and document:

- A dedicated development realm, exact issuer, web redirect/logout URIs, and
  application audience; no wildcard production redirects.
- Authorization-code login with PKCE; client type/secret handling appropriate
  to the chosen server-side session library.
- `administrator`, `author`, and `learner` role mapping, and stable issuer/subject
  identity mapping in the application database.
- A separate least-privilege administration identity for account operations.
- Synthetic test identities and safe provisioning without committed credentials.
- Session expiry, logout/revocation, CSRF protection and disabled-account behavior.

Local `start-dev` and file-backed storage are not production configuration.
Production requires TLS, a dedicated supported database, managed secrets, and
approved operating/recovery procedures.
