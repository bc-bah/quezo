# Planned assessment modules

No domain modules are implemented yet. Introduce them one vertical slice at a
time after [architecture review](../../../../docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md).
Future modules are Python packages under `quezo_api.modules`; FastAPI routers
translate HTTP inputs/outputs without becoming a second home for domain rules.

| Future directory | Responsibility |
| --- | --- |
| `identity/` | Actors, account/access administration, roles and ownership |
| `questions/` | Banks, question authoring/search and immutable question revisions |
| `quizzes/` | Draft composition, preview and publication lifecycle |
| `distribution/` | Named-learner assignments and eligibility |
| `attempts/` | Start/resume, snapshots, autosave, deadlines and finalization |
| `scoring/` | Pure objective grading from fixed attempt inputs |
| `results/` | Policy-filtered learner results and author reporting |

Keep each module's rules behind a small interface. HTTP handlers must not duplicate
those rules. Test through the same interface used by callers; add real PostgreSQL
tests for persistence and concurrency rather than relying on in-memory substitutes.
