# jay-claude

A Claude Code plugin marketplace. Currently ships one plugin: **jay-session**.

한국어 문서: [README-ko.md](README-ko.md)

---

# jay-session

Carry your work across session boundaries.

Long tasks outlive a single context window. The usual fix — `/compact` — is lossy, and it fires at the worst possible moment: when your context is fullest and you have the most to lose. This plugin takes the other route. Write down what matters *before* clearing, then let the next session pick it up automatically.

## Install

```bash
claude plugin marketplace add jaymunsh/jay-claude
claude plugin install jay-session@jay-claude
```

The first command clones this repository; the second installs the plugin from it. Then run `/reload-plugins` — commands and hooks are loaded at that point, and `/clear` does not reload them.

Requires `python3`, which ships with macOS and most Linux distributions. Works in any project; you install it once, not per repository.

To update later:

```bash
claude plugin marketplace update jay-claude
claude plugin update jay-session@jay-claude
```

The first line refreshes the cloned repository; the second refreshes what is actually installed. Run both, then `/reload-plugins`.

---

## The core flow

Two commands you type, and one thing that happens on its own.

```
── Session 1 ──────────────────────────────────
  (you work for a while)

  > /jay-new

    Claude reviews the conversation and your git state,
    writes .claude/session/handoff-20260807-1430.md,
    and asks only about what it genuinely can't infer.

    It also hands you a prompt to copy:
    ┌──────────────────────────────────────────────┐
    │ read .claude/session/handoff-20260807-1430.md│
    │ verify it, and continue                      │
    └──────────────────────────────────────────────┘

  > /clear                     ← you type this yourself

── Session 2 ──────────────────────────────────
  (the handoff's location is already in context)

  > paste the prompt above   or just   "keep going"

    Claude confirms the handoff is still accurate,
    briefs you in a few lines, and picks up at the
    next task.
```

**Either input works.**

- **The copied prompt** — it has the file path baked in, so that one line stands on its own. It works even if the hook didn't fire for any reason.
- **"keep going"** — the hook already put the handoff's path in context, so two words are enough. Claude reads the file at that point.

The filename carries a timestamp, so you can't memorize it and can't look it up once the conversation is gone. That's why `/jay-new` gives you the prompt **with the real filename already in it** — you just copy it.

> **A git repository isn't required.** The prompt never mentions git — it just says "verify it," and Claude picks the check that fits: `git status` and `git log` inside a repo, the handoff's own re-verify command outside one. Outside a repo the handoff also omits its branch and uncommitted-changes fields.

**What you still do yourself:** type `/clear`, and send a first message in the new session. A session waits for input; loading context doesn't make Claude speak first.

### Why `/clear` isn't automatic

`/clear` throws away the whole conversation. Slash commands only run from your input, and no hook can clear a session — but even if one could, this is a decision about timing that belongs to you, not to the model.

---

## Commands

| Command | What it does | Setup needed |
|---|---|---|
| `/jay-new` | Writes a handoff, then tells you to `/clear` | None — creates the directory on first use |
| `/jay-init` | Turns on automatic devlog recording for this project | None |
| `/jay-brief` | Writes a document explaining this project to another project or agent | None |

You can narrow the handoff's focus: `/jay-new auth refactor only`

### `/jay-brief` — explaining this project to another one

`/jay-new` hands *the work you were doing* to your next session. `/jay-brief` explains *the project itself* to someone outside it — an agent in a different project that has never opened this repository.

```
/jay-brief
```

No arguments. One document per project.

It reads the repository (`git ls-files`, `git log`, the README, `CLAUDE.md`, the package manifest) and writes `.claude/session/project-brief.md`: what the project does, how it's laid out, why it was built this way, how to run it, where it's been heading lately, and what to watch out for. It's written to **stand on its own** — the reader may not have the repository, so pointers like "see the README" are addresses they can't open.

You get back a prompt with an absolute path in it. **Paste that into the other project's session, then say what you want done.**

```
/Users/me/projects/foo/.claude/session/project-brief.md read this and get up to speed on the project.
```

The path is absolute because the reader's working directory is somewhere else entirely; a relative one means nothing there.

**Running it again updates the file.** It reads what's there first rather than overwriting. Sections derived from git — layout, recent direction — get regenerated; **architecture decisions and gotchas are carried forward and added to**, since those are the parts no amount of reading the repo will recover. The `created` line at the top stays; only `last updated` moves.

### What goes in a handoff

Goal, what was done, current state (branch, uncommitted changes, whether it was verified), the command to re-verify it, next steps, and — most importantly — **what you tried that didn't work**.

That last part is the whole point. `git log` already tells the next session what changed. Nothing but the handoff can tell it which approach you abandoned and why, which is exactly what saves it from walking into the same wall.

---

## Devlog (optional)

An append-only record of every turn: the request, the result, files changed. Useful for retrospectives and for "how did we fix that last month?"

```
/jay-init
```

**This one needs an explicit opt-in** because it writes on every single turn. Nothing should quietly start accumulating files in your repository without you saying so. Run it once per project where you want it.

Recording starts from the *next* turn. Turning it on mid-session doesn't recover the earlier part of that session, and it never backfills a project's history.

### Reading it back

No command needed — just ask:

- *"how did we fix that timeout error last week?"* → searches the devlog
- *"what did I get done this week?"* → summarizes by topic, not a flat list

### Decisions

Tag an entry with `**결정:**` (or `**Decision:**`) when a real choice was made, recording **what you picked, what you rejected, and why**:

```markdown
## 2026-08-07 17:22 — Auth approach settled
**Decision:** Server sessions over JWT — JWT can't be revoked instantly,
which conflicts with the logout requirement. Scaling handled by Redis.
```

Then pull just the decisions out later:

```bash
grep -B4 '^\*\*Decision:' .claude/session/devlog*.md
```

There's no separate `decisions.md` on purpose. One place to write means never deciding which file something belongs in, and the surrounding entry carries the context the decision was made in.

### Manual entries

The hook extracts what it can see. When something matters that it can't — a reason, a dead end, a constraint you discovered — say *"log this one"* and it gets written with that reasoning included.

---

## What gets created

Nothing until you ask for it. `/jay-new` creates the directory on first use, and the devlog hook exits immediately unless `devlog.md` exists.

```
<your project>/.claude/session/
├── handoff-20260807-1430.md   # up to 10 kept
├── handoff-20260807-1105.md
├── project-brief.md           # from /jay-brief — one per project, updated in place
├── devlog.md                  # current month — its existence is the on/off switch
├── devlog-2026-07.md          # previous months, rotated automatically
└── .devlog-state              # dedup cursor for the hook
```

The first time this directory is created you'll be asked once whether to add `.claude/session/` to `.gitignore`. Default is yes: it's a personal workflow trail that duplicates your commit log, and the devlog grows every turn and would pollute diffs. Say no if you want to share handoffs with your team.

### Data lifecycle

| What | Policy | Why |
|---|---|---|
| **Handoffs** | Keep the newest **10**; older ones are removed when a new one is written | Resuming only ever reads the latest one. Beyond that they just pile up |
| **Project brief** | One file, updated in place | One per project is enough; multiple versions just raise the question of which is current |
| **Devlog** | **Kept forever**, only split by month | The value of a devlog is in the old entries. There's no reason to delete them |

**The devlog is not one file per day.** Entries accumulate inside a single file as `## 2026-08-07 14:30 — ...`, and only when the month changes does everything so far get moved to `devlog-2026-07.md`.

Nothing ever merges — it only ever splits. Searches glob `devlog*.md` and cover everything at once, so the split costs you nothing while keeping any single file from growing without bound.

If losing old handoffs bothers you, leave `.claude/session/` out of `.gitignore` and commit it — deleted ones then survive in git history.

---

## How it works

Three hooks, one script.

| Hook | Fires when | Does |
|---|---|---|
| `Stop` | Every turn ends | Appends to the devlog, rotates monthly. Exits instantly if the devlog is off |
| `SessionStart` (`clear`, `compact`) | Right after the conversation is discarded | Injects **only the path and age** of the newest handoff. On `clear` Claude reads it, briefs you, and asks where to start; on `compact` it opens the file only if the summary dropped something |
| `PreCompact` | Context is about to be compacted | Records where the uncompacted transcript lives |

**There's no time limit.** Instead the handoff arrives labeled with how old it is — "방금" (just now), "5시간 전" (5 hours ago), "31일 전" (31 days ago). If it's more than a day old, Claude confirms you actually mean to resume that work before diving in, since you may have cleared in order to start something unrelated.

There's deliberately no cutoff constant. A "handoffs expire after N minutes" rule is one more thing you'd have to remember, and whether a document is stale is a judgment the age already supports.

**`SessionStart` passes a path, not the document,** on purpose. The hook fires on every clear — including the ones where you wiped the context precisely to go do something else. Injecting the body there means inhaling a few thousand tokens and throwing them away. A path costs two lines, and you read the file only when you're actually continuing.

**`PreCompact` saves a path, not a snapshot,** for the same reason. Compaction only clears the model's context — the transcript file stays on disk. What you need afterwards is a pointer to it, not a copy of it.

**The split between skill and hook** follows what can be forgotten. Judgment work (what belongs in a handoff, how to summarize a search) lives in the `session-manager` skill. Mechanical work lives in the hooks, because "remember to log every turn" is exactly the kind of instruction that quietly stops happening once a session gets long.

---

## Turning things off

```bash
rm .claude/session/devlog.md    # stop devlog recording
claude plugin uninstall jay-session@jay-claude
```

Deleting `devlog.md` deletes the log — move it first if you want to keep it. Uninstalling removes the hooks and commands; files already written to `.claude/session/` stay where they are.

## Notes

- The plugin never touches your `settings.json`. Hooks ship inside the plugin, so they coexist with anything else you have installed.
- Skill and command instructions are written in Korean. Claude replies in whatever language you use.

## License

MIT
