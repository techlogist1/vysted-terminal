# R15 Census — World sweep: agent-native desktop UX (state of the art, Sept 2026)

Worker model id: `claude-opus-5[1m]`
Date of sweep: 2026-09-19
Scope: what the best agent-native tools have PROVEN about agent UX — Cursor, Claude Code,
Zed, Warp, Raycast, Linear, Notion, Perplexity Comet, Devin-class background agents.
Read-only sweep. No repo files changed except this one.

## Evidence conventions

- `[FETCHED]` = primary doc fetched and quoted verbatim.
- `[SNIPPET]` = the domain refused fetch (network/enterprise block) or 308'd to a doc root;
  claim rests on search-engine snippets of that page, labelled as such. Treated as weaker.
- Blocked domains encountered this sweep (honest disclosure): `cursor.com` /
  `docs.cursor.com`, `docs.warp.dev`, `www.notion.com`, and `code.claude.com` (ECONNRESET
  on repeated attempts). Their claims below are `[SNIPPET]`-grade unless a third-party
  primary-quality source is cited instead.

---

## 1. Findings — the proven patterns

### W-1. Plan/approval gate before execution is universal

Three independent tools converge on the same gate: the agent writes a plan, the human
approves or edits it, only then does it touch anything.

- Claude Code: plan mode "makes Claude Code read-only until you approve a written plan";
  modes cycle `default → acceptEdits → plan` on Shift+Tab, or `claude --permission-mode
  plan`. `[SNIPPET]` — https://likeone.ai/blog/claude-code-permission-modes-guide-2026/
- Cursor: "For complex tasks, use Plan Mode first where the agent will outline what it
  plans to do and you can approve or adjust before it starts executing" — "turns a vague
  task into an explicit, reviewable list of steps and files so you can catch a wrong
  approach in seconds instead of unwinding a bad multi-file change." `[SNIPPET]` —
  https://www.learncursor.dev/learn/cursor-agents
- Warp: "Agents will present developers with a plan before acting, and developers can
  control how autonomously the agent should act." `[SNIPPET]` —
  https://www.warp.dev/blog/reimagining-coding-agentic-development-environment
- Linear makes the plan a first-class *protocol object*: the agent UI surfaces "a
  checklist-style plan showing pending, in-progress, completed, and canceled tasks."
  `[FETCHED]` — https://linear.app/developers/agent-interaction

**Verdict: table stakes.** Not "a nice affordance" — the gate is where the human's
judgment is applied, and every serious tool has one.

### W-2. Every mutation is reviewable as a diff with per-hunk accept/reject

- Zed: "accept or reject each individual change hunk, or the whole set of changes made by
  the agent", via a multi-buffer review pane (Ctrl+Shift+R); `agent.single_file_review`
  puts keep/reject controls inline per file and "temporarily overrid[es] the buffer's git
  diff while review is active." `[FETCHED]` — https://zed.dev/docs/ai/agent-panel
- Warp exposes "whether agents should auto-accept their code diffs" as an explicit
  permission toggle, i.e. diff review is the default and auto-accept is the opt-out.
  `[SNIPPET]` — https://docs.warp.dev/agents/autonomy/agent-permissions

**Verdict: table stakes.** The unit of review is the *change*, not the transcript.

### W-3. Checkpoints / undo that are automatic, not opt-in

- Claude Code: "checkpointing automatically captures the state of your code before each
  prompt you send that starts a turn", retaining "file snapshots for the 100 most recent
  checkpoints in a session." Crucially documented limit: "if Claude runs `rm`, `mv`, or
  `cp`, those changes cannot be undone through rewind because only direct edits through
  Claude's file-editing tools are tracked." `[SNIPPET]` (code.claude.com ECONNRESET ×3) —
  https://code.claude.com/docs/en/checkpointing ; corroborated
  https://theaiarchitects.com/blog/claude-code-checkpoints
- Cursor: "snapshots of your codebase during an Agent session, auto-created before making
  significant changes, and restorable from the chat timeline … eliminating the common
  failure mode where an agent would delete migrations or corrupt files with no recovery
  path." `[SNIPPET]` — https://www.morphllm.com/cursor-background-agents
- Zed: "Every time the model performs an edit, you should see a 'Restore Checkpoint'
  button" — and it works "even if interrupting mid-edit." `[FETCHED]` —
  https://zed.dev/docs/ai/agent-panel

**Verdict: table stakes.** And the honest disclosure of what undo does NOT cover (Claude
Code's `rm`/`mv` carve-out) is itself the pattern — tools state the boundary rather than
implying total undo.

### W-4. Queueing and mid-run steering are separate, both expected

Zed is the clearest specification of the distinction: messages sent while the agent is
generating "are queued by default"; to interrupt instead of wait you "Toggle 'Steer' on
that message" and it lands "at the next step rather than wait for completion"; a queued
message can be forced through with "Send Now" (double-enter); and a stop button
"interrupt[s] generation immediately." `[FETCHED]` — https://zed.dev/docs/ai/agent-panel

That is four distinct stop/steer semantics in one panel: queue, steer-at-next-step,
send-now, hard-stop. **Table stakes: queue + hard stop. Differentiator: steer-at-next-step.**

### W-5. Context/token consumption is displayed continuously, not on request

Zed "surfaces how many tokens you are consuming for your currently active thread near the
profile selector", with automatic compaction that "summarizes earlier messages when
approaching threshold limits." `[FETCHED]` — https://zed.dev/docs/ai/agent-panel

**Verdict: table stakes.** The user must be able to see the window filling before it fills.

### W-6. Permission model is per-tool and rule-ordered, not a global boolean

Zed moved off a single boolean to an ordered rule system:
"In Zed v0.224.0 and above, tool approval is controlled by `agent.tool_permissions.default`"
(`"confirm" | "allow" | "deny"`), with precedence "built-in security rules → `always_deny`
→ `always_confirm` → `always_allow` → tool-specific defaults → global default", and
built-in rules that "cannot be bypassed" for destructive commands (`rm -rf /`, `rm -rf ~`).
`[FETCHED]` — https://zed.dev/docs/ai/tool-permissions

Warp exposes four orthogonal permission axes — file reads, command execution, code-diff
acceptance, MCP server use — plus an allowlist/denylist, where "when all four permissions
are set to 'Always allow,' the agent gains full autonomy ('YOLO mode'); however, any
denylist rules will still override these settings." `[SNIPPET]` —
https://docs.warp.dev/agents/autonomy/agent-permissions

**Verdict: table stakes for a tool with side effects.** The proven shape is: ordered rules,
an unbypassable floor, and a per-capability (not per-session) grant.

### W-7. Background/durable runs are their own product surface with their own lifecycle

- Cursor background agents "run autonomously in a Cursor-hosted sandbox on a separate
  branch where you queue a task, close your laptop, and return to a completed pull
  request, billed per-compute-minute in addition to standard model token costs."
  `[SNIPPET]` — https://www.morphllm.com/cursor-background-agents
- Devin-class: "The lifecycle is the same across every tool: ticket → cloud sandbox →
  autonomous edit → PR → human review." `[SNIPPET]` —
  https://techsy.io/en/blog/background-coding-agents-compared
- Linear formalises the lifecycle into a state machine: `AgentSession` has exactly six
  states — "`pending`, `active`, `error`, `awaitingInput`, `complete`, and `stale`" —
  managed "based on the last emitted activity", with a liveness contract: "If you receive a
  `created` event, you are expected to send an activity or update your external URL within
  10 seconds to avoid the session being marked as unresponsive", and staleness after
  30 minutes of silence, "recoverable by sending another agent activity." `[FETCHED]` —
  https://linear.app/developers/agent-interaction ,
  https://linear.app/developers/agent-best-practices

**Verdict: the Linear state machine is the most transferable artifact in this whole sweep.**
`awaitingInput` and `stale` as *first-class states* are what most homegrown run models miss.

### W-8. A durable run must emit a typed activity stream, not a log

Linear's five activity types: "**thought**: Internal reasoning notes; **action**: Tool
invocations, optionally including results; **elicitation**: Requests for user clarification
or confirmation; **response**: Work completion or final results; **error**: Failure
reporting with optional remediation links." Plus user-generated `prompt` follow-ups.
`[FETCHED]` — https://linear.app/developers/agent-interaction

The best-practice doc adds two rules a finance terminal should copy wholesale:

1. Acknowledge instantly: "Upon receiving the `created` webhook, your agent should respond
   immediately with a `thought` activity to acknowledge that the agent has started working."
2. Never reconstruct history from mutable text: "Comments may not be reliable to read from,
   as they are editable and may have changed since your agent's last run. Instead, rely on
   **Agent Activities** as these are frozen-in-time snapshots of user input."
   `[FETCHED]` — https://linear.app/developers/agent-best-practices

**Verdict: table stakes for durable runs.** `error` carrying "optional remediation links" is
the error-recovery UX pattern: a failure is a *resumable object*, not a red toast.

### W-9. Following the agent's attention is a distinct affordance from reading its output

Zed: "follow the agent as it reads and edits files by clicking the crosshair icon … which
makes your editor jump to each file the agent touches", or "hold `cmd`/`ctrl` when
submitting a message to automatically follow." `[FETCHED]` —
https://zed.dev/docs/ai/agent-panel

**Verdict: emerging, strong.** Not yet universal, but it is the answer to "what is it doing
right now" that a scrolling transcript never gives.

### W-10. Memory is an editable artifact the user can read, not an opaque store

Notion: "give your Agent an instructions page so it feels like a teammate who knows your
work and style … it remembers over time, so you don't have to keep repeating yourself";
permissions are scoped per-agent, "giving each agent access only to the databases, pages,
and tools it needs." `[SNIPPET]` (notion.com blocked) —
https://www.notion.com/product/agents , https://www.notion.com/releases/2026-02-24

Claude Code's equivalent is `CLAUDE.md` — a plain file the user edits directly.

**Verdict: table stakes.** The proven form is *a document the user can open and edit*, not
a learned embedding the user must trust.

### W-11. Agents are scheduled/triggered, not only invoked

Notion Custom Agents (GA 24 Feb 2026) "are proactive — they run on triggers like schedules,
Slack messages, emails, and database changes." `[SNIPPET]` —
https://www.notion.com/releases/2026-02-24 , corroborated
https://matthiasfrank.de/en/notion-custom-agents-full-tutorial-use-cases-pricing-changes/

**Verdict: table stakes in knowledge tools as of 2026; still emerging in dev tools.**

### W-12. Cost/budget is a metered, user-visible resource

- Notion moved Custom Agents onto credits: "Starting May 4, 2026, Custom Agents will run on
  Notion credits … the more work they do for you, the more credits they use", at "$10 per
  1,000 credits." `[SNIPPET]` — https://www.notion.com/releases/2026-02-24 (corroborated by
  https://almcorp.com/blog/notion-custom-agents/)
- Cursor background agents are "billed per-compute-minute in addition to standard model
  token costs." `[SNIPPET]` — https://www.morphllm.com/cursor-background-agents

**Verdict: table stakes for durable/background runs specifically.** Foreground chat mostly
still hides cost; background runs universally expose it, because they spend while unwatched.

