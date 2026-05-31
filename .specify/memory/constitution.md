# Vysted Terminal Constitution

The non-negotiable principles for the Vysted Terminal — an open-source, AI-native,
extensible finance workspace. These principles govern the "agent-at-the-center"
redesign and every feature and plugin built on the platform. They supersede
convenience, velocity, and individual preference. Where a spec or plan conflicts with
a principle, the principle wins (or the principle is formally amended — see Governance).

## Core Principles

### I. Agent at the Center, Hands Always on the Wheel (Dual-Mode)

The agent is a **co-equal primary surface**, not a bolted-on sidebar. It is
terminal-aware (it can open panels, set symbols, drive the watchlist, stage actions,
explain, and plan) and its natural output is **the cockpit itself** — panels are to
Vysted what files are to a code editor.

Two users are first-class **in one workspace, never two apps**: the agent-delegator
(a novice who talks to the terminal and is driven step-by-step) and the hands-on
driver (a finance-literate user pulling and arranging by hand). Every capability MUST
be reachable both by hand and by agent. The switch between leaning on the agent and
driving by hand MUST be a single, non-destructive gesture. The agent does the
ambiguous upfront work, then **hands off to the manipulable cockpit** — never trap a
user inside a chat transcript for work that wants direct manipulation.

### II. One Capability Catalog, Many Consumers (MCP-as-Framework)

Every terminal capability (quotes, charts, screener, fundamentals, portfolio, news,
quant, brokers, …) is defined **once** in a single capability catalog and projected to
**all** consumers: the built-in copilot/personas AND external MCP clients (Claude Code,
other agents). The internal agent adapter and the external MCP adapter are two
**renderers of the same source of truth**, not two hand-maintained surfaces. A
capability MUST NOT exist for only one consumer. One `read_only` declaration drives
both the internal mutation gate and the external `readOnlyHint`. Vysted is a
**framework people build finance agents and trade-bots on**, not a closed app.

### III. Safety Is Layered and Non-Negotiable (Defense-in-Depth)

Read-only by default; every mutation is explicit, gated, and audited. The BLUEPRINT
§6.5 invariants are permanent and may only be **strengthened**, never weakened without
operator sign-off:

- **Append-only audit log** enforced at the database level (SQLite triggers + a
  read-only reader connection), not by convention.
- **Type-gated execution** (mutations only reachable through an explicit confirm path)
  plus a grep-time audit over all call sites.
- **Kill-switch** that halts the mutating path.
- **Read-only-by-default wrappers** (no mutating methods on a provider's public
  surface; GET-only routers; `supportsControlPlane = false`).

Every agent-proposed change — panel config, portfolio, workspace build, and especially
orders — renders as a **reviewable preview→applied diff** (accept-all / reject-all /
per-item, keyboard-driven). **Orders never auto-apply; there is no "YOLO" path.**
Autonomous agent runs are bounded by a hard ceiling on tokens / spend / wall-clock /
steps (a BudgetGuard) — autonomous spend is a safety surface the same way execution is.

### IV. Local-First, Bring-Your-Own-Keys, Private by Default

Vysted runs **fully on the user's machine** with **no hosted backend**. All provider
and model keys are operator-supplied. Secrets live in the **OS keychain** (the renderer
reads them and passes them per request; the sidecar cannot read the keychain),
least-privilege at point of use, **never logged, echoed, or persisted** beyond process
memory; the sidecar binds loopback only. No user data leaves the machine unless a
plugin explicitly routes it outward, and that routing is visible. Credential storage
MUST NOT regress to plaintext files or machine-ID-derived encryption.

### V. Extensible by Contract (the Six-Capability Plugin Platform)

The `VystedPlugin` contract (`types/plugin.ts`) — six capabilities: **data, panels,
commands, agents, nodes, control plane** — is the platform's backbone and a **Tier-1
locked file**. It stays serializable (no framework types cross it). Changing it is a
breaking change for every downstream plugin and requires operator sign-off. **First-
party features are built as if they were plugins**, exercising the same contract, so
the extension surface is always real and dogfooded. The platform — not the agent roster
or the license — is the durable moat.

### VI. Verification Is the Product (Provenance & Auditability)

Finance has no compiler; **evidence is the substitute**. Every data response carries
**provenance** (which provider served it). Every agent claim that asserts a fact
carries **citations**. Every mutation lands in the append-only audit trail. The
provider/model/cost in use is always legible on the agent surface. Trust is earned with
verifiable artifacts, not asserted — and never simulated (no fabricated data behind a
"populated" surface; unverified is labeled unverified).

### VII. Minimal-Dark, Density with Progressive Disclosure

Keep the **grammar and density** of a professional terminal; reject the discoverability
tax. The UI is **dark-only, token-driven, keyboard-first** (canvas palette single-
sourced separately from CSS tokens). Simple by default — a new user is productive after
learning a few keystrokes (Ask / Edit-panel / Build); deep on demand — the full power
(command grammar, node editor, MCP servers, background agents) reveals itself through a
**command palette that teaches its own shortcuts**. Density is a feature for the target
user; complexity is **layered, not flattened**, and never dumped on the front door. A
minimal, populated starter cockpit is the default — plugins open as tabs the user or
agent opens, never preloaded en masse.

## Additional Constraints (Stack, Scope & Decision Authority)

**Stack (Locked — BLUEPRINT §2):** Tauri 2.x (Rust core) + Next.js 16 static export +
React 19 + TypeScript strict + Tailwind 4 + shadcn/ui + Zustand; lightweight-charts +
`@xyflow/react`; a Python 3.13 FastAPI sidecar (loopback, PyInstaller `--onefile`) for
data + AI compute; OS targets Windows + macOS + Linux; **AGPL-3.0 + commercial dual
license**. No hosted backend.

**Foundation to keep (reframe, don't rebuild):** the FastAPI sidecar + data layer,
dockview panels + persistent workspace layouts, the §6.5 safety architecture, Kite
read-only + BYOK keychain, and the copilot's existing tool loop. The redesign rebuilds
the **experience** on this foundation, not the foundation.

**Out of scope for the redesign (note, do not design):** broker **order execution** is
deferred behind the safety layer; the Tradesa plugin is a separate track. _(This
deferral reverses a prior BLUEPRINT §2 Locked decision — a Tier-4 change requiring
explicit operator ratification; see the spec's open-decisions.)_

**Decision Authority (blast-radius tiers):** (1) **Locked** — BLUEPRINT §2; never
reopen unilaterally. (2) **Spec-derivable** — decide and proceed. (3) **Spec-ambiguous,
derives from DNA** — decide from positioning, record a one-line trail. (4) **High blast
radius** — the plugin contract, licensing, the §6.5 safety model, core architecture, or
**reversing a Locked decision** — block and ask the operator. Only Tier 4 surfaces.

## Development Workflow & Quality Gates

- **Full-scope, no half-ships.** Build the complete scope of a feature the first time;
  no "Phase 2" TODOs rotting in production code. Prefer one strong implementation over
  several half-considered options; avoid premature abstraction.
- **Living documentation.** `CLAUDE.md` (current-state DNA + active rules),
  `docs/CURRENT_STATE.md` (the honest baseline), and the per-subsystem docs are updated
  in the same PR that changes the behavior they describe. Build history goes to
  `CHANGELOG.md`, not into the rules.
- **CI-parity verification is a hard gate.** `pnpm ci-local` (lint + format + typecheck
  - clippy `-D warnings` + ruff + vitest + cargo test + pytest) and the sidecar
    smoke-test pass before any release tag. A skipped or red gate invalidates the tag.
- **Conventional commits, one per deliverable. No emojis in code or commits.**
- **TDD where it pays:** contract tests for the plugin contract, the capability
  catalog, and the §6.5 safety surface are written and must hold before the behavior
  they protect is changed.

## Governance

This constitution supersedes other practices when they conflict. **Amendments** require:
a written rationale, operator approval, a semantic-version bump (below), and propagation
to dependent artifacts (`CLAUDE.md`, the relevant spec, and any template that encodes a
principle). Reversing a Locked decision (BLUEPRINT §2) or weakening a §6.5 safeguard is
a **Tier-4** action — it MUST be ratified by the operator and recorded here, never made
silently. Every plan and PR is reviewed for principle compliance; unjustified
complexity is rejected. Runtime development guidance lives in `CLAUDE.md`; the
current-state baseline lives in `docs/CURRENT_STATE.md`.

**Versioning:** MAJOR = principle removed/redefined or governance incompatibility;
MINOR = principle/section added or materially expanded; PATCH = clarifications and
wording.

**Version**: 1.0.0 | **Ratified**: 2026-05-30 | **Last Amended**: 2026-05-30
