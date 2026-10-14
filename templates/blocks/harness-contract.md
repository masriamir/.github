How an agent harness builds, tests, and ships this repository is declared directly below this
block, under the same `## Harness contract` heading, as a fenced `toml` block with one
`[harness]` table. This block is the specification and is synced from upstream; the fenced
values are this repository's own.

| Field | Required | Meaning | Default |
|---|---|---|---|
| `gate` | yes | the pre-push gate command | |
| `board` | yes | the GitHub Project number under the repository owner | |
| `test` | no | the full test command, when it is more than the gate | `""` (the gate) |
| `screenshot` | no | `none`, `playwright`, `cli-transcript`, or a command that writes images | `none` |
| `plans` | no | where implementation plans are written; `""` means an untracked plans directory the repository ignores | `""` |
| `specs` | no | where design specs are written | `""` |
| `review` | no | how an automated review is requested: `ruleset` (on push), `workflow` (a repo workflow), or `manual` | `ruleset` |
| `coverage` | no | `codecov` or `none` | `none` |
| `merge` | no | `manual`; `auto` is reserved and refused | `manual` |
| `skills` | no | names of stack review passes to run after the code review | `[]` |
| `[harness.env]` `up`, `down` | no | commands that start and stop the environment the tests need | `""` |

The harness reads the first `toml` fence after the heading and nothing else. Repository
visibility and rulesets are read live from GitHub, never declared here. A missing required
field stops the harness before any work starts, with the lines to add.
