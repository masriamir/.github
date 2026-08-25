PRs are reviewed automatically by `copilot-pull-request-reviewer`. Work through its comments — review threads **and** the suppressed comments in the review body — across as many rounds as needed. Verify each finding against the actual code before acting; bots are sometimes wrong or working from a stale diff.

A PR is ready for human review only when **all** of these hold:

- every automated review thread is resolved,
- every required CI check passes (`gh pr checks`), and
- the codecov comment reports no uncovered changed lines (or each remaining miss is consciously justified).

Resolved threads over a red required check — or unaddressed missing coverage — do **not** make a PR ready. Whether a fresh review is auto-requested on push or must be requested by hand is a per-repo ruleset detail (`review_on_push`); check the ruleset when a request seems stuck rather than assuming.
