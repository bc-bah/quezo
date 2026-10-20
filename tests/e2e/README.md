# Future end-to-end coverage

No browser test framework or assessment tests are installed yet. The root
`npm test` command runs Python/pytest checks for the backend scaffold's HTTP
behavior and generated liveness OpenAPI contract, not browser journeys.

After approval, add browser coverage alongside each complete vertical slice:

- Role-based login and account access administration.
- Question reuse, quiz preview/publication, and assignment.
- Attempt start, navigation, acknowledged save, refresh and resume.
- Submit/retry, authoritative expiry, and permitted result disclosure.
- Learner history and author summary/submission review.
- Cross-author/cross-learner denial, keyboard navigation and accessible save state.

Use synthetic identities/content and an isolated PostgreSQL database. Exercise
concurrent save/start/finalize behavior in backend integration tests as well;
browser happy paths alone cannot establish transaction correctness.
