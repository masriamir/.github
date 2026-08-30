# Shared blocks

Canonical, repository-neutral content embedded in consumer-owned files through `meta_sync.py`
block mode. Each file is the single canonical version of content that must remain identical across
its adopters; consuming repositories wrap it in destination-appropriate marker comments and pin the
source commit in `.meta-manifest.toml`.

Blocks carry no leading indentation. `meta_sync.py` re-indents a block to the leading whitespace of
its own opening marker line, so one canonical file serves destinations that nest differently.

| Block file | Marker | Typical destination | Covers |
|---|---|---|---|
| `language-en-us.md` | `language-en-us` | `AGENTS.md` | American-English spelling rule, third-party exception, "state the pattern" guidance |
| `commit-conventions.md` | `commit-conventions` | `AGENTS.md` | Conventional Commits; PR-title-is-changelog/version; squash body blank |
| `branch-naming.md` | `branch-naming` | `AGENTS.md` | `<type>/<slug>` branch naming; no release branches |
| `board-transitions.md` | `board-transitions` | `AGENTS.md` | Agent-driven GitHub Project Status flow |
| `copilot-review-loop.md` | `copilot-review-loop` | `AGENTS.md` | Ready-for-review = threads resolved + CI green + codecov clean |
| `codecov-status-default.yml` | `codecov-project-status` and `codecov-patch-status` | `coverage.status.project` and `coverage.status.patch` in `codecov.yml` | Shared `default` status: 90% absolute target |
| `codecov-comment.yml` | `codecov-comment` | `comment` in `codecov.yml` | A PR comment on every PR, with header, diff, file, and footer sections |

Destination markers use the comment syntax appropriate to the consumer file. For example, an
instruction block in `AGENTS.md` uses HTML comments:

```markdown
<!-- >>> meta:language-en-us -->
...synced content...
<!-- <<< meta:language-en-us -->
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

## Codecov policy fragments

The Codecov policy is split into independently adoptable fragments so a repository can keep local
settings at every mapping level. `codecov-status-default.yml` is one file adopted twice — the
project and patch statuses share a target, so they share a canonical source, and a change to it
cannot leave the two disagreeing. A full adoption looks like this:

```yaml
coverage:
  status:
    project:
      # >>> meta:codecov-project-status
      default:
        target: 90%
      # <<< meta:codecov-project-status
    patch:
      # >>> meta:codecov-patch-status
      default:
        target: 90%
      # <<< meta:codecov-patch-status

comment:
  # >>> meta:codecov-comment
  # require_changes is explicit rather than left to Codecov's default: the shared
  # review gate reads this comment on every PR, so it has to be posted even when a
  # change moves coverage by nothing.
  require_changes: false
  layout: "condensed_header, diff, condensed_files, condensed_footer"
  # <<< meta:codecov-comment
```

The fragments themselves are un-indented; the indentation above comes from each marker line, which
`meta_sync.py` applies to the block it inserts. A repository that indents `codecov.yml` with four
spaces seeds its markers at that depth and adopts the same fragments unchanged.

Marker *placement* is still load-bearing: a fragment defines keys meaningful only under the parent
shown above, so keep each marker under the mapping named in the table. Moving one elsewhere
produces valid but semantically wrong YAML, which the byte-oriented drift check cannot catch.

`require_changes: false` is deliberate, not an accidental restatement of the Codecov default. The
[`copilot-review-loop`](copilot-review-loop.md) block makes "the codecov comment reports no
uncovered changed lines" a precondition for human review, which only holds if the comment is
always posted — under `require_changes: true` a PR that moves coverage by nothing gets no comment,
and the gate can never be satisfied.

Add one manifest entry for each adopted fragment, using the same exact merged upstream commit:

```toml
[[file]]
source = "masriamir/.github"
ref = "<40-char commit sha>"
path = "templates/blocks/codecov-status-default.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-project-status"

[[file]]
source = "masriamir/.github"
ref = "<40-char commit sha>"
path = "templates/blocks/codecov-status-default.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-patch-status"

[[file]]
source = "masriamir/.github"
ref = "<40-char commit sha>"
path = "templates/blocks/codecov-comment.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-comment"
```

Replace every `<40-char commit sha>` with the exact merged upstream commit when adopting the
fragments. `meta_sync.py` rejects anything that is not 40 hex characters with a message naming the
entry, so a placeholder left in place fails loudly rather than 404-ing later.

### Repository-specific settings and overrides

Settings under keys not owned by a marker remain local. Examples include `coverage.precision`, an
additional comment key such as `behavior`, and a top-level `ignore` list.

A repository can enforce a stricter target while retaining the shared baseline by adding a named
status after the relevant marker:

```yaml
coverage:
  status:
    project:
      # >>> meta:codecov-project-status
      default:
        target: 90%
      # <<< meta:codecov-project-status
      strict:
        target: 95%
```

Codecov publishes `codecov/project` for `default` and `codecov/project/strict` for the named
status. Require `codecov/project/strict` in that repository's GitHub ruleset to enforce 95%. The
same pattern can add a stricter named patch status. See Codecov's
[status-check documentation](https://docs.codecov.com/docs/commit-status) for named statuses.

A true replacement is an explicit opt-out at fragment granularity. A repository that wants only a
single 95% project status drops the `codecov-project-status` manifest entry, **deletes that
marker's two lines and the synced body between them**, and authors its local `project.default` at
95%; it can still adopt the patch and comment fragments. Likewise, a repository that needs a
different comment layout drops the `codecov-comment` entry, deletes its markers and body, and owns
its complete `comment` mapping locally.

Removing the manifest entry alone is not enough. `meta_sync.py` only ever rewrites blocks the
manifest names, so an orphaned marker keeps its last-synced body — leaving the locally authored key
alongside a stale copy of the one it was meant to replace, and the drift check green either way.

Never repeat a key already present inside an adopted marker. Duplicate YAML keys are ambiguous and
may be rejected; use a differently named status for stricter enforcement, or opt out of the
fragment as above to replace its default.

Instruction-block rationale and rollout: `crusty-meta` ADR-0002. The Codecov fragments are
account-generic and opt-in; each repository decides which ones to adopt.
