# Phase 4-5: Hardening, operations and acceptance

These packages verify the completed P0 workflows, not just the scaffold.
Use [BACKLOG.md](BACKLOG.md) for prerequisites and the
[software specification](../SOFTWARE-SPECIFICATION.md) for acceptance IDs/gates.
Run destructive/failure exercises only against explicitly isolated synthetic data.

## Q01: Integrity and access failure suite

**Rules:** IAM-01/02/03, ATT-01 through ATT-04, RESULT-01, QUAL-01/02/04.
**Evidence:** AT-01/02/04/06/07/08/09/10/12, emphasizing failure and concurrency.
**Surfaces:** backend integration/contract tests and browser failure scenarios;
coordinate any production fixes with the owning module.

Exercise concurrent starts and stale/replayed saves, response loss after commit,
database rollback/unavailability, submit/expiry races, restart catch-up and
question edits while attempts are active. Test cross-role/cross-owner requests,
invalid JWTs, disabled access, CSRF and hidden-field disclosure in payloads/caches.
Verify log/error redaction against synthetic recognizable secret/answer values.

**Done:** each invariant has a repeatable real-database test; failures are fixed
and linked to regression cases; no unacknowledged fallback or duplicate grade is
accepted. Record failure injection setup and residual risks. Existing happy-path
tests still pass. Handoff a stable correctness baseline for Q03.

**Excluded:** claiming compliance certification or testing a shared/live database.

## Q02: Accessibility and workflow acceptance

**Rules:** section 8, QUAL-03, approved DEC-09. **Evidence:** AT-08/14.
**Surfaces:** browser/accessibility tests and targeted UI corrections.

Exercise author, learner and administrator workflows using keyboard, responsive
viewports and screen-reader review. Check focus, labels, errors, save-status
announcements, offline/conflict handling and approved timer behavior. Include
expired sessions, hidden results and empty/loading/failure states.

**Done:** automated checks and documented manual observations cover core flows;
blocking findings are resolved; remaining limitations identify scope/severity/
owner rather than an unsupported blanket WCAG claim. Coordinate changes in
feature-owned UI with the integration owner.

## O01: Deployment observability and recovery

**Rules:** QUAL-02/05/06/07/10. **Evidence:** AT-15/17.
**Decisions:** DEC-08/10 operating/recovery values; no external provisioning or
real-data deployment without explicit authorization.
**Surfaces:** web/backend Dockerfiles, environment configuration, release scripts,
readiness/observability implementation, runbooks and CI integration.

Build reproducible separate application images, single-run migration release
step, restricted runtime configuration and real readiness distinct from liveness.
Provide structured correlation/error logs and save/finalization/expiry/pool
signals without sensitive payloads. Document secret management, TLS and production
Keycloak persistence separately from local `start-dev`.

Rehearse backup and restore in an isolated target, covering assessment data and
identity/session dependencies. Verify restored user mapping/access and scores,
measure recovery duration/data loss, and document rollback/incident ownership.
Fail readiness explicitly when required dependencies/schema/configuration are
unavailable; liveness should not claim data readiness.

**Done:** a reviewer can reproduce deployment and isolated restoration from the
runbook; approved recovery/operational targets have recorded evidence; unavailable
dependencies and restart behavior are understandable from health/log signals.
Handoff the reproducible benchmark environment to Q03.

If targets remain unapproved, synthetic local rehearsals may be delivered but
O01 stays blocked for its operational acceptance. No guessed RPO/RTO is approval.

## Q03: Load and multi-process evidence

**Rules:** QUAL-08/09; approved DEC-08. **Evidence:** AT-16.
**Surfaces:** load scenarios, synthetic generators, benchmark reports and narrowly
scoped fixes identified by measurement.

Run the agreed workload including autosave traffic and submission bursts against
O01's environment after Q01's integrity baseline. Include multiple backend
processes, pool-budget checks and periodic-expiry contention. Measure frontend
usable-time separately from backend read latency.

**Done:** report actual hardware/configuration/data volumes and p50/p95/p99,
throughput/error rate, CPU/memory/connections, and correctness assertions.
Compare actual results with approved thresholds; investigate failures rather than
weakening them silently. Re-run affected correctness cases after tuning.
Store reproducible scripts and sanitized summarized results, not learner data.

**Excluded:** generic framework benchmarks, unapproved load against shared systems,
or interpreting a load-test pass as monthly availability evidence.

## G01: Prototype acceptance and pilot decision

**Owner:** Product + Engineering + designated operational/privacy reviewers.
**Type:** evidence review and release decision, not another feature bundle.

Reconcile every P0 trace row and QUAL rule in the software specification with
integrated code and AT-01 through AT-17 evidence. Record approved numeric gates,
actual outcomes, any accepted exceptions with owner/impact/follow-up, and remaining
pilot decisions. Demonstrate the complete workflow with synthetic accounts/data.

**Done:** named approvers accept the prototype or explicitly list blockers; the
tracker links an acceptance record with date, integrated revision and evidence.
If pilot approval is sought, DEC-10/11 must also be closed and operating ownership
assigned. Distinguish "prototype accepted for synthetic demo" from "approved for
real-data pilot." Integrity or disclosure failures block acceptance.

Do not announce deployment, production readiness or completed work based solely
on an agent report, a generated checklist or green scaffold tests.
