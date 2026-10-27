# PHP environment clearance

## Project / commit / date

Quezo / `354da4975eb12174f4cdd627713c1dc758a6b83e` / 26 October 2026  
(HEAD committed `2026-10-23T12:40:08-04:00`)

## PHP use

**Not detected in tracked files.**

## Evidence

- `git grep` found no matches for PHP/framework/Composer indicators.
- `git ls-files` found no PHP or Composer filenames.
- No tracked `composer.json` or `composer.lock`.
- Tracked CI, `.github/workflows/ci.yml`, configures Node, uv/Python, PostgreSQL, and Keycloak—not PHP.
- Docker definitions are `infra/docker/api.Dockerfile`, `infra/docker/web.Dockerfile`, `compose.yaml`, and `compose.local.yaml`.
- Broad text search produced only `Apache-2.0` license-string hits in `package-lock.json`; these are not PHP or Apache HTTP Server findings.

## PHP CLI / actual runtime

PHP CLI was unavailable on the checked development machine. Actual deployed runtime: **N/A** — Quezo is not provided to an environment; no local Docker containers, Compose services, or Kubernetes context were present.

## Runtime advisory

**N/A** — no PHP runtime was identified or available to assess.

## Composer audit

**N/A** — no Composer manifest or lockfile is tracked, and Composer was not present.

## Images / exclusions / errors

- Scanned clean for PHP/Composer paths and package records:
  - `postgres:17` at `sha256:b8faeff7712663c2773a190181e1246e37e364b887611c04658c28b44e2408fe`
  - `quay.io/keycloak/keycloak:26.4.7` at `sha256:9409c59bdfb65dbffa20b11e6f18b8abb9281d480c7ca402f51ed3d5977e6007`
  - built `quezo-local-api` at `sha256:b4de5b64d9ea92d02f67326831d5fc3cf7ff91908baacaeeaa1ef494aff19061`
  - `node:24-bookworm-slim` base image
  - built `quezo-local-web` at `sha256:a73b0fcb0c662300954a0aff838e468767101e2ca5f7ccc8a3110445f5cfd031`
- The final web image built successfully with the approved `npm_ca` secret. Filesystem, Debian-package, and production npm-package-path scans found no PHP/Composer indicators. Its build-time `npm audit` reported 0 vulnerabilities.
- `syft`, `trivy`, and Docker Scout were unavailable; completed checks are package/filesystem inventories, not standards-format SBOMs.
- Image-tag results apply to the listed pulled digests only.

## Conclusion

**No PHP use identified in checked scope. No known findings in completed checks.**
