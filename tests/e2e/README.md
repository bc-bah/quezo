# End-to-end acceptance

No browser test framework is installed yet. I02 is active under B.C.; use its
[copy-ready prompt](../../docs/implementation/AGENT-HANDOFF.md#i02-dispatch-prompt).
The root `npm test` runs web and Python checks, `test:web:production` exercises
built Next.js through HTTP with controlled peers, and `test:identity:integration`
uses actual Keycloak through HTTP. None is real-browser/facade acceptance.

I02 adds the focused browser runner and isolated browser -> Next.js -> FastAPI
-> Keycloak/PostgreSQL proof, reusable synthetic logins and CI evidence.
First resolve [EX-I02-01](../../docs/implementation/BACKLOG.md#ex-i02-01-native-loginlogout-origin):
exercise native login/logout forms without injected Origin headers, preserve
CSRF denial and document the outcome. No auth bypass, mocked `/me`, password-grant
shortcut or injected session cookie establishes this gate. Keep credentials and
usable tokens/cookies out of committed logs, traces, HAR and browser state files.

Later explicitly assigned vertical slices add:

- Role-based login and account access administration.
- Question reuse, quiz preview/publication, and assignment.
- Attempt start, navigation, acknowledged save, refresh and resume.
- Submit/retry, authoritative expiry, and permitted result disclosure.
- Learner history and author summary/submission review.
- Cross-author/cross-learner denial, keyboard navigation and accessible save state.

Use synthetic identities/content and an isolated PostgreSQL database. Exercise
concurrent save/start/finalize behavior in backend integration tests as well;
browser happy paths alone cannot establish transaction correctness.
