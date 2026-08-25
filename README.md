# .github

Account-wide defaults and shared conventions for [@masriamir](https://github.com/masriamir)'s repositories.

## What GitHub reads from here (live defaults)

These files apply automatically to any repository under this account that does not carry its own copy:

- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Contributor Covenant
- [`SECURITY.md`](SECURITY.md) — generic reporting policy (private vulnerability reporting)

Issue and pull request templates are deliberately **not** provided as live defaults — they would
appear on every repository, including long-dormant ones. Repositories opt in by carrying their own
copies; canonical versions will live under `templates/`.

## Conventions (all active repos)

- **Branching:** `<type>/<slug>` from `main`, where type is `feature | bugfix | hotfix | docs | chore`;
  include the issue number in the slug when one exists (`feature/42-mmap-support`).
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/), enforced locally by
  lefthook's `commit-msg` hook.
- **PRs squash-merge, and the PR title becomes the only commit on `main`** — it is the Conventional
  Commit that drives changelogs and version bumps, so title PRs accordingly (`!` for breaking changes
  goes in the title).
- **Gates:** run the repository's documented pre-push gate before pushing; `gh pr checks` on the PR
  is the source of truth, not local results.
- **Reviews:** Copilot code review is requested by ruleset on every push; a PR is ready for human
  review only when all review threads are resolved and all required checks are green.
- **Supply chain:** third-party GitHub Actions are pinned to full commit SHAs (readable ref kept in a
  trailing comment); Dependabot proposes the bumps.

## Layout

- [`templates/`](templates/) — canonical copies of shared files, consumed by each repository's
  `.meta-manifest.toml` via the `meta-check` drift check; `templates/README.md` documents which
  entries are synced and which are one-time seeds
- [`scripts/`](scripts/) — `check-conventional-subject.py` (+ regression suite) and
  `meta_sync.py` (+ self-test)
- [`.github/workflows/`](.github/workflows/) — reusable `pr-title.yml` and `meta-check.yml`,
  plus this repository's own CI and PR-title gate

Conventions specific to the **crusty** family of repositories live in
[`crusty-meta`](https://github.com/masriamir/crusty-meta).

## License

Licensed under either of [Apache License, Version 2.0](LICENSE-APACHE) or
[MIT license](LICENSE-MIT) at your option.
