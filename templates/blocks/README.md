# Shared instruction blocks

Canonical, repo-neutral text for conventions that are identical across the crusty family. Each
file is the single canonical version of one convention; consuming repos embed it in their root
`AGENTS.md` between marker lines and keep it current with a `mode = "block"` entry in their
`.meta-manifest.toml`, drift-checked by `meta-check`.

| Block file | Marker | Covers |
|---|---|---|
| `language-en-us.md` | `language-en-us` | American-English spelling rule, third-party exception, "state the pattern" guidance |
| `commit-conventions.md` | `commit-conventions` | Conventional Commits; PR-title-is-changelog/version; squash body blank |
| `branch-naming.md` | `branch-naming` | `<type>/<slug>` branch naming; no release branches |
| `board-transitions.md` | `board-transitions` | Agent-driven GitHub Project Status flow |
| `copilot-review-loop.md` | `copilot-review-loop` | Ready-for-review = threads resolved + CI green + codecov clean |

In the consuming repo's `AGENTS.md`:

```markdown
<!-- >>> meta:language-en-us -->
...synced content...
<!-- <<< meta:language-en-us -->
```

Manifest entry (per block):

```toml
[[file]]
source = "masriamir/.github"
ref    = "<40-char commit sha>"   # meta_sync requires an exact 40-hex-char commit, not a tag or short SHA
path   = "templates/blocks/language-en-us.md"
dest   = "AGENTS.md"
mode   = "block"
marker = "language-en-us"
```

Rationale and rollout: `crusty-meta` ADR-0002.
