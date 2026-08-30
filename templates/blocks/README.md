# Shared blocks

Canonical, repository-neutral content embedded in consumer-owned files through `meta_sync.py`
block mode. Each file is the single canonical version of content that must remain identical across
its adopters; consuming repositories wrap it in destination-appropriate marker comments and pin the
source commit in `.meta-manifest.toml`.

| Block file | Marker | Typical destination | Covers |
|---|---|---|---|
| `language-en-us.md` | `language-en-us` | `AGENTS.md` | American-English spelling rule, third-party exception, "state the pattern" guidance |
| `commit-conventions.md` | `commit-conventions` | `AGENTS.md` | Conventional Commits; PR-title-is-changelog/version; squash body blank |
| `branch-naming.md` | `branch-naming` | `AGENTS.md` | `<type>/<slug>` branch naming; no release branches |
| `board-transitions.md` | `board-transitions` | `CLAUDE.md` | Agent-driven GitHub Project Status flow |
| `copilot-review-loop.md` | `copilot-review-loop` | `AGENTS.md` | Ready-for-review = threads resolved + CI green + codecov clean |
| `codecov-policy.yml` | `codecov-policy` | `codecov.yml` | Strict 90% project and patch coverage statuses plus changed-lines-only PR comments |

Destination markers use the comment syntax appropriate to the consumer file. For example, an
instruction block in `AGENTS.md` uses HTML comments:

```markdown
<!-- >>> meta:language-en-us -->
...synced content...
<!-- <<< meta:language-en-us -->
```

The Codecov block in `codecov.yml` uses YAML comments:

```yaml
# >>> meta:codecov-policy
coverage:
  status:
    project:
      default:
        target: 90%
        threshold: 0%
        base: auto
    patch:
      default:
        target: 90%
        threshold: 0%
        base: auto

comment:
  layout: "reach, diff, files"
  require_changes: true
# <<< meta:codecov-policy
```

Manifest entry for an instruction block:

```toml
[[file]]
source = "masriamir/.github"
ref    = "<40-char commit sha>"   # meta_sync requires an exact 40-hex-char commit, not a tag or short SHA
path   = "templates/blocks/language-en-us.md"
dest   = "AGENTS.md"
mode   = "block"
marker = "language-en-us"
```

Manifest entry for the Codecov policy:

```toml
[[file]]
source = "masriamir/.github"
ref = "0123456789abcdef0123456789abcdef01234567"
path = "templates/blocks/codecov-policy.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-policy"
```

The sample SHA demonstrates the required 40-character form. Replace it with the exact merged
upstream commit when adopting the block.

Instruction-block rationale and rollout: `crusty-meta` ADR-0002. The Codecov block is
account-generic and opt-in; each repository decides whether to adopt it.
