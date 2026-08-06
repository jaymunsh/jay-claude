# jay-claude

A Claude Code plugin marketplace. Currently ships one plugin:

**[jay-session](#jay-session)** — carry your work across session boundaries. Write a handoff, hit `/clear`, and the new session picks up exactly where you left off.

한국어 문서: [README-ko.md](README-ko.md)

---

## jay-session

Long tasks outlive a single context window. The usual fix — `/compact` — is lossy and fires at the worst possible moment, when your context is fullest and you have the most to lose. This plugin takes the other route: write down what matters *before* clearing, then hand it to the next session automatically.

### What you get

| Feature | What it does |
|---|---|
| **Handoff** | Reviews the conversation and git state, writes a structured `handoff-*.md` — including what you *tried and failed*, which `git log` can never tell you |
| **Auto-resume after `/clear`** | A `SessionStart` hook injects the fresh handoff into the new session. No prompt to copy-paste |
| **Devlog** | Every turn is appended to `devlog.md` automatically — request, result, files changed. Opt-in per project |
| **Decision log** | Tag an entry with `**결정:**` / `**Decision:**` and grep them out later |
| **Compact insurance** | If auto-compact fires, the pre-compact transcript path is recorded so nothing is truly lost |

### Install

```bash
claude plugin marketplace add jaymunsh/jay-claude
claude plugin install jay-session@jay-claude
```

Restart Claude Code (or start a new session) — commands and hooks load at session start.

Requires `python3`, which ships with macOS and most Linux distributions.

### Usage

**Wrapping up a session:**

```
/jay-new
```

Claude reviews what happened, writes `.claude/session/handoff-YYYYMMDD-HHMM.md`, and asks only about things it genuinely can't infer. Then you type `/clear` yourself — and the new session already knows the context.

You can narrow the focus: `/jay-new auth refactor only`

**Turning on the devlog** (optional, per project):

```
/jay-init
```

From the next turn on, every exchange is appended to `.claude/session/devlog.md`. This one needs an explicit opt-in because it writes on every turn — nothing should quietly accumulate files in your repo without you saying so.

**Everything else is plain conversation.** No command needed:

- "let's continue from last time" → reads the latest handoff, verifies it against `git status`, briefs you
- "how did we fix that timeout error last week?" → searches the devlog
- "log this one" → appends a manual entry with the reasoning a hook can't capture

### What gets created

Nothing until you ask. `/jay-new` creates the directory on first use; the devlog hook exits immediately unless `devlog.md` exists.

```
<your project>/.claude/session/
├── handoff-20260806-2230.md   # accumulates; newest wins
├── devlog.md                  # current month — its existence is the devlog on/off switch
├── devlog-2026-07.md          # previous months, rotated automatically
└── .devlog-state              # dedup cursor for the hook
```

On first creation you'll be asked once whether to add `.claude/session/` to `.gitignore`. Default is yes — it's a personal workflow trail that duplicates your commit log, and the devlog grows every turn and would pollute diffs. Say no if you want to share handoffs with your team.

### How it works

Three hooks, one script:

| Hook | Fires when | Does |
|---|---|---|
| `Stop` | Every turn ends | Appends to the devlog, rotates monthly. Exits instantly if the devlog is off |
| `SessionStart` (`clear`, `compact`) | New session after clearing | Injects a handoff written in the last 30 minutes |
| `PreCompact` | Context gets compacted | Records where the uncompacted transcript lives |

The 30-minute window is what keeps this from being noisy: writing a handoff *is* the signal that you intend to continue. An old handoff won't get dragged into an unrelated session.

`PreCompact` saves a path rather than a snapshot on purpose — compaction only clears the model's context; the transcript file stays on disk. What you need afterwards is a pointer, not a copy.

Everything requiring judgment (what to put in a handoff, how to summarize a devlog search) lives in the `session-manager` skill. Everything mechanical lives in the hook, so it can't be forgotten mid-session.

### Turning things off

```bash
rm .claude/session/devlog.md    # stop devlog recording (this deletes the log — move it first if you want it)
claude plugin uninstall jay-session@jay-claude
```

Uninstalling removes the hooks and commands. Files already written to `.claude/session/` stay where they are.

### Notes

- The plugin never touches your `settings.json`. Hooks ship inside the plugin, so they coexist with whatever else you have installed.
- Enabling the devlog mid-session only captures from the next turn onward — the earlier part of that session isn't recovered.
- Skill and command instructions are written in Korean; Claude responds in whatever language you use.

## License

MIT
