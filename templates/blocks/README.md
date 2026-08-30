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
| `board-transitions.md` | `board-transitions` | `CLAUDE.md` | Agent-driven GitHub Project Status flow |
| `copilot-review-loop.md` | `copilot-review-loop` | `AGENTS.md` | Ready-for-review = threads resolved + CI green + codecov clean |
| `codecov-status-default.yml` | `codecov-project-status` and `codecov-patch-status` | `coverage.status.project` and `coverage.status.patch` in `codecov.yml` | Shared blocking `default` status: 90% target; a missing report fails |
| `codecov-comment.yml` | `codecov-comment` | `comment` in `codecov.yml` | One project-and-patch comment on every PR: header, diff, files, footer |

`board-transitions.md` is the one block whose adopters place it in `CLAUDE.md` rather than
`AGENTS.md` (`crustyview` and `crustywad` both pin it there). The destination is per-adopter and
comes from each consumer's manifest either way — this column records what adopters actually do.

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
      # One source shared by the project and patch statuses, so they cannot drift apart.
      default:
        target: 90%
        if_not_found: failure  # a missing report is a broken upload, not a pass
        if_ci_failed: error    # a red CI run cannot yield a green coverage status
        informational: false   # this status blocks; it does not merely report
      # <<< meta:codecov-project-status
    patch:
      # >>> meta:codecov-patch-status
      # One source shared by the project and patch statuses, so they cannot drift apart.
      default:
        target: 90%
        if_not_found: failure  # a missing report is a broken upload, not a pass
        if_ci_failed: error    # a red CI run cannot yield a green coverage status
        informational: false   # this status blocks; it does not merely report
      # <<< meta:codecov-patch-status

comment:
  # >>> meta:codecov-comment
  # Every key here is explicit because the shared review gate depends on it, not
  # because it differs from Codecov's current default. The gate in
  # copilot-review-loop.md reads "the codecov comment" on every PR, so the comment
  # has to exist, stay singular, and show coverage on the changed lines.
  require_changes: false  # post even when a change moves coverage by nothing
  require_base: false     # post on a PR with no base report (a repo's first PRs)
  behavior: default       # update the one comment rather than adding another
  # layout and hide_project_coverage are one decision, not two: condensed_* plus
  # hide_project_coverage reduces the comment to the git diff. This policy keeps
  # project coverage, so both codecov/project and codecov/patch are explained when
  # either goes red.
  layout: "header, diff, files, footer"
  hide_project_coverage: false
  # <<< meta:codecov-comment
```

The fragments themselves are un-indented; the indentation above comes from each marker line, which
`meta_sync.py` applies to the block it inserts. A repository that indents `codecov.yml` with four
spaces seeds its markers at that depth and adopts the same fragments unchanged.

Marker *placement* is still load-bearing: a fragment defines keys meaningful only under the parent
shown above, so keep each marker under the mapping named in the table. Moving one elsewhere
produces valid but semantically wrong YAML, which the byte-oriented drift check cannot catch.

### Why the comment fragment pins current defaults

The [`copilot-review-loop`](copilot-review-loop.md) block makes "the codecov comment reports no
uncovered changed lines" a precondition for human review. That gate holds only if the comment
reliably exists, stays singular, and shows the changed lines — so the keys it depends on are
pinned even where they match Codecov's default today, and each one carries its reason in the
fragment:

| Key | Why it is pinned |
|---|---|
| `require_changes: false` | Under `true`, Codecov posts nothing when coverage does not move, so a docs, CI-config, or pure-refactor PR gets no comment and the gate can never be satisfied. |
| `require_base: false` | Under `true`, a PR with no base report — a repository's first PRs, or a new default branch — gets no comment, with the same result. |
| `behavior: default` | Updates one comment in place. `new` posts a fresh comment per push, leaving several to disagree about which one the gate means. |

`layout` and `hide_project_coverage` are one decision rather than two. Codecov documents two comment
shapes: `header, files, footer` with `hide_project_coverage: false` for a full comment, and
`condensed_header, condensed_files, condensed_footer` with `hide_project_coverage: true` for a
git-diff-only comment — the `condensed_` prefix is what reduces the comment to patch coverage, not a
per-status variant. This policy takes the full shape, adding `diff` so patch coverage on the changed
lines is always present, because the status fragment sets a project status too and a patch-only
comment would leave `codecov/project` failures unexplained.

`layout` is a single key under `comment`; a status entry accepts no `layout`, so the project and
patch statuses cannot be given different comment formats.

### Settings that must stay local

`after_n_builds` delays the comment until a given number of uploads have arrived. Repositories that
upload from several CI jobs need it, or Codecov comments on the first partial upload and the gate
reads misleading coverage — but the right value is the number of uploads that repository makes, so
it cannot be shared. Set it locally, outside the marker. The same applies to `flags`, `paths`,
`branches`, and `component_management`.

### Adoption prerequisite

`if_not_found: failure` inverts Codecov's default, under which a status with no coverage report
passes — making a broken upload indistinguishable from full coverage. A repository must therefore
be uploading coverage before it adopts the status fragment; adopting it first leaves both statuses
red until uploads work.

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

Settings under keys not owned by a marker remain local. Examples include `coverage.precision`, a
comment key the fragment does not set — `after_n_builds`, say, per "Settings that must stay local"
above — and a top-level `ignore` list. `behavior`, `require_changes`, `require_base`, `layout`, and
`hide_project_coverage` are owned by the `codecov-comment` fragment; setting any of them locally
would duplicate a key the marker already carries.

A repository can enforce a stricter target while retaining the shared baseline by adding a named
status after the relevant marker:

```yaml
coverage:
  status:
    project:
      # >>> meta:codecov-project-status
      # One source shared by the project and patch statuses, so they cannot drift apart.
      default:
        target: 90%
        if_not_found: failure  # a missing report is a broken upload, not a pass
        if_ci_failed: error    # a red CI run cannot yield a green coverage status
        informational: false   # this status blocks; it does not merely report
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
