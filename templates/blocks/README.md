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
| `codecov-project-status.yml` | `codecov-project-status` | `coverage.status.project` in `codecov.yml` | Default project status with a strict 90% target |
| `codecov-patch-status.yml` | `codecov-patch-status` | `coverage.status.patch` in `codecov.yml` | Default patch status with a strict 90% target |
| `codecov-comment.yml` | `codecov-comment` | `comment` in `codecov.yml` | Changed-lines-only PR comments with reach, diff, and file details |

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

The Codecov policy is split into three independently adoptable fragments so a repository can keep
local settings at every mapping level. A full adoption looks like this:

```yaml
coverage:
  status:
    project:
      # >>> meta:codecov-project-status
      default:
        target: 90%
        threshold: 0%
        base: auto
      # <<< meta:codecov-project-status
    patch:
      # >>> meta:codecov-patch-status
      default:
        target: 90%
        threshold: 0%
        base: auto
      # <<< meta:codecov-patch-status

comment:
  # >>> meta:codecov-comment
  layout: "reach, diff, files"
  require_changes: true
  # <<< meta:codecov-comment
```

The fragments contain their destination indentation because `meta_sync.py` inserts their bytes
verbatim. Keep the markers at the nesting shown above; moving a fragment to another mapping can
produce invalid or semantically incorrect YAML.

Add one manifest entry for each adopted fragment, using the same exact merged upstream commit:

```toml
[[file]]
source = "masriamir/.github"
ref = "0123456789abcdef0123456789abcdef01234567"
path = "templates/blocks/codecov-project-status.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-project-status"

[[file]]
source = "masriamir/.github"
ref = "0123456789abcdef0123456789abcdef01234567"
path = "templates/blocks/codecov-patch-status.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-patch-status"

[[file]]
source = "masriamir/.github"
ref = "0123456789abcdef0123456789abcdef01234567"
path = "templates/blocks/codecov-comment.yml"
dest = "codecov.yml"
mode = "block"
marker = "codecov-comment"
```

The sample SHA demonstrates the required 40-character form. Replace every occurrence with the
exact merged upstream commit when adopting the fragments.

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
        threshold: 0%
        base: auto
      # <<< meta:codecov-project-status
      strict:
        target: 95%
        threshold: 0%
        base: auto
```

Codecov publishes `codecov/project` for `default` and `codecov/project/strict` for the named
status. Require `codecov/project/strict` in that repository's GitHub ruleset to enforce 95%. The
same pattern can add a stricter named patch status. See Codecov's
[status-check documentation](https://docs.codecov.com/do/docs/commit-status) for named statuses.

A true replacement is an explicit opt-out at fragment granularity. A repository that wants only a
single 95% project status omits the `codecov-project-status.yml` manifest entry and authors its
local `project.default` at 95%; it can still adopt the patch and comment fragments. Likewise, a
repository that needs a different comment layout omits `codecov-comment.yml` and owns its complete
`comment` mapping locally.

Never repeat a key already present inside an adopted marker. Duplicate YAML keys are ambiguous and
may be rejected; use a differently named status for stricter enforcement or omit the fragment to
replace its default.

Instruction-block rationale and rollout: `crusty-meta` ADR-0002. The Codecov fragments are
account-generic and opt-in; each repository decides which ones to adopt.
