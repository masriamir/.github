# templates

Canonical copies of files shared across repositories. GitHub reads nothing from this
directory — its contents reach repositories only through the sync mechanism.

Two kinds of entry:

- **Synced** — the repository's copy must stay identical to the canonical file here
  (whole-file, or a marker-delimited block). Each consuming repository lists the entry
  in a `.meta-manifest.toml` pinned to a commit of this repository, and
  `python3 scripts/meta_sync.py check` — run locally and by the reusable `meta-check`
  workflow — fails on drift. Adopting a canonical change is deliberate: bump the
  entry's `ref` pin, run `python3 scripts/meta_sync.py sync`, commit both.
- **Seed** — a starting point copied once when setting a repository up, expected to
  diverge afterwards. Listed in no manifest.

| Entry | Kind | Notes |
|---|---|---|
| `editorconfig` | synced | dest `.editorconfig` |
| `CODEOWNERS` | synced | dest `.github/CODEOWNERS` |
| `rust/lefthook.yml` | synced | whole file; assumes the vendored validator below |
| `rust/rustfmt.toml` | synced | |
| `rust/deny.toml` | seed | audit config legitimately diverges (e.g. wildcard-path exemptions) |
| `python/lefthook.yml` | synced | whole file; assumes the vendored validator below, plus `uv` and ruff/mypy/ty in a dev group |
| `python/pyproject.toml` | seed | packaging metadata only, no `[tool.*]`; supplies the dev group `python/lefthook.yml` needs; replace `PROJECT_NAME` |
| `python/ruff.toml` | seed | |
| `python/mypy.ini` | seed | `files` is load-bearing — the hook runs `mypy` with no path argument |
| `python/ty.toml` | seed | ty is pre-1.0; pin it, and expect per-repo `[[overrides]]` |
| `python/pytest.toml` | seed | needs pytest 9.0+; out-ranks `pytest.ini` and `[tool.pytest.ini_options]` |
| `python/uv.toml` | seed | uv rejects `default-groups` here, so it is omitted — `uv sync --all-groups` picks up `test` |
| `python/hatch.toml` | seed | build config; replace `PACKAGE_NAME` |
| `github/bug_report.yml` | seed | dest `.github/ISSUE_TEMPLATE/bug_report.yml`; per-repo fields diverge |
| `github/feature_request.yml` | seed | dest `.github/ISSUE_TEMPLATE/feature_request.yml`; per-repo fields diverge |
| `github/config.yml` | seed | dest `.github/ISSUE_TEMPLATE/config.yml`; replace `REPO` with the repo name |
| `github/pull_request_template.md` | seed | dest `.github/PULL_REQUEST_TEMPLATE.md`; per-repo validation steps diverge |
| `gitignore/base.gitignore` | synced (block) | marker `gitignore-base` inside the repo's `.gitignore` |
| `gitignore/rust.gitignore` | synced (block) | marker `gitignore-rust` |
| `gitignore/python.gitignore` | synced (block) | marker `gitignore-python` |
| `../scripts/check-conventional-subject.py` | synced | vendored to `scripts/`, together with `test-conventional-subject.sh` |
| `../scripts/meta_sync.py` | synced | vendored to `scripts/`; the sync tool itself is manifest-tracked |

Block-mode markers in a destination file (comment leader is the destination's own):

```text
# >>> meta:gitignore-base
…canonical content…
# <<< meta:gitignore-base
```

Manifest example (`.meta-manifest.toml` at a consuming repository's root):

```toml
[[file]]
source = "masriamir/.github"
ref = "<40-char commit sha>"
path = "templates/rust/lefthook.yml"
dest = "lefthook.yml"
mode = "file"

[[file]]
source = "masriamir/.github"
ref = "<40-char commit sha>"
path = "templates/gitignore/base.gitignore"
dest = ".gitignore"
mode = "block"
marker = "gitignore-base"
```
