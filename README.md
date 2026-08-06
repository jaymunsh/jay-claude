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

The first command clones this repository; the second installs the plugin from it. Then restart Claude Code — commands and hooks load at session start.

Requires `python3`, which ships with macOS and most Linux distributions. Works in any project; you install it once, not per repository.

To update later:

```bash
claude plugin marketplace update jay-claude
```

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
    │ verify against git status, and continue      │
    └──────────────────────────────────────────────┘

  > /clear                     ← you type this yourself

── Session 2 ──────────────────────────────────
  (the handoff is already loaded into context)

  > paste the prompt above   or just   "keep going"

    Claude checks git status to confirm the handoff is
    still accurate, briefs you in a few lines, and
    picks up at the next task.
```

**Either input works.**

- **The copied prompt** — it has the file path baked in, so that one line stands on its own. It works even if the hook didn't fire for any reason.
- **"keep going"** — the hook already put the handoff in context, so two words are enough.

The filename carries a timestamp, so you can't memorize it and can't look it up once the conversation is gone. That's why `/jay-new` gives you the prompt **with the real filename already in it** — you just copy it.

**What you still do yourself:** type `/clear`, and send a first message in the new session. A session waits for input; loading context doesn't make Claude speak first.

### Why `/clear` isn't automatic

`/clear` throws away the whole conversation. Slash commands only run from your input, and no hook can clear a session — but even if one could, this is a decision about timing that belongs to you, not to the model.

---

## Commands

| Command | What it does | Setup needed |
|---|---|---|
| `/jay-new` | Writes a handoff, then tells you to `/clear` | None — creates the directory on first use |
| `/jay-init` | Turns on automatic devlog recording for this project | None |

You can narrow the handoff's focus: `/jay-new auth refactor only`

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
├── handoff-20260807-1430.md   # accumulates; the newest is used
├── devlog.md                  # current month — its existence is the on/off switch
├── devlog-2026-07.md          # previous months, rotated automatically
└── .devlog-state              # dedup cursor for the hook
```

The first time this directory is created you'll be asked once whether to add `.claude/session/` to `.gitignore`. Default is yes: it's a personal workflow trail that duplicates your commit log, and the devlog grows every turn and would pollute diffs. Say no if you want to share handoffs with your team.

---

## How it works

Three hooks, one script.

| Hook | Fires when | Does |
|---|---|---|
| `Stop` | Every turn ends | Appends to the devlog, rotates monthly. Exits instantly if the devlog is off |
| `SessionStart` (`clear`, `compact`) | A new session after clearing | Injects a handoff written in the last 30 minutes |
| `PreCompact` | Context is about to be compacted | Records where the uncompacted transcript lives |

**The 30-minute window** is what keeps auto-resume from being noisy. Writing a handoff *is* the signal that you intend to continue, so a handoff from last week never gets dragged into an unrelated session.

**`PreCompact` saves a path, not a snapshot,** on purpose. Compaction only clears the model's context — the transcript file stays on disk. What you need afterwards is a pointer to it, not a copy of it.

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
