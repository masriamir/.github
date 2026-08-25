Move the GitHub Project board yourself as work progresses and **announce each change** in your reply ("moved #201 → In progress") rather than asking first — board edits are internal and easily reversed.

| Transition | Trigger |
|---|---|
| `Backlog → Ready` | the user says they want to start work on an issue |
| `Ready → In progress` | you begin brainstorming or drafting a plan — **before** any branch or code |
| `In progress → In review` | the PR opens |
| `In review → Done` | the PR merges/closes — **board-automated**, not manual |

`In review` holds through the entire review loop, until human review and merge. Transitions apply only to an issue that is on the board; if one exists but isn't on the board, add it first. Epics carry an **aggregate** Status: `In progress` when their first sub-issue starts work, and `Done` (board-automated) only when every sub-issue closes — set the epic's Status yourself and announce it, since GitHub rolls up completion progress but not the Status field.
