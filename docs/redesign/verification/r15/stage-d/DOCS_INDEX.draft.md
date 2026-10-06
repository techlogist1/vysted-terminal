<!-- DRAFT at 6bc6d378cbbf9cfbefd8d155e027c2dc80214331 by the Stage D gap-check pass; refresh before rc2 -->
<!-- Promotes to docs/README.md as-is (strip this header comment and the "Gap fixed"
     note at the end first). Surgical addition only: one new section, "Redesign process
     (current)", inserted after "The redesign (in flight)". Every other line is
     byte-identical to docs/README.md at this head. -->

# Vysted Terminal — documentation

Start here. Current-state references live at the top of `docs/`; historical per-phase
artifacts are under `docs/archive/`.

## Read first

- **[CURRENT_STATE.md](./CURRENT_STATE.md)** — honest, current-state inventory of the
  whole app (architecture, every subsystem, the full endpoint table, the copilot,
  safety, persistence, and a works/buggy/deferred status table). The baseline the
  redesign builds on.

## The redesign (in flight)

- **[`../specs/001-agent-native-redesign/spec.md`](../specs/001-agent-native-redesign/spec.md)**
  — the "agent-native finance workspace" specification (user stories, requirements,
  success criteria, open product decisions).
- **[`../.specify/memory/constitution.md`](../.specify/memory/constitution.md)** — the
  seven governing principles.

## Redesign process (current)

- **[`../docs/redesign/DECISIONS_FOR_OPERATOR.md`](../docs/redesign/DECISIONS_FOR_OPERATOR.md)**
  — the open Tier-4 decision ledger: every blocked_tier4 register item, its smallest
  unblock, and the operator-only calls the R15 run has surfaced. Cited throughout the
  release collateral (release notes, runbook, briefing) but not previously indexed here.
- **[`../docs/redesign/KEYCHAIN_DEV_SIGNING.md`](../docs/redesign/KEYCHAIN_DEV_SIGNING.md)**
  — the dev-keystore + macOS dev-signing runbook referenced by `CLAUDE.md`'s keychain
  gotcha; one-time setup so `tauri dev` keeps a stable keychain identity across
  hot-reloads.

## Architecture references (current)

| Doc                                                | Covers                                                                                          |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [BLUEPRINT.md](./BLUEPRINT.md)                     | Original architectural blueprint — §2 locked decisions, §6.5 safety, module catalog, phase plan |
| [SAFETY_ARCHITECTURE.md](./SAFETY_ARCHITECTURE.md) | §6.5 agent-write safety enforcement, file:line pointers                                         |
| [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)         | MCP on both sides — proxied subprocesses + the serve-out FastMCP surface                        |
| [SIDECAR_API.md](./SIDECAR_API.md)                 | Sidecar HTTP surface overview                                                                   |
| [PLUGIN_DEVELOPMENT.md](./PLUGIN_DEVELOPMENT.md)   | The `VystedPlugin` six-capability contract and how to build a plugin                            |
| [BROKER_INTEGRATIONS.md](./BROKER_INTEGRATIONS.md) | Removal note — trading was removed permanently (D81, 23 Sep 2026)                               |
| [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)             | Design tokens and the (current) visual language                                                 |
| [PHASE_10_HANDOFF.md](./PHASE_10_HANDOFF.md)       | Historical phase handoff (copilot + reskin) — its §3 broker/Kite content is superseded by D81   |

## History

- **[../CHANGELOG.md](../CHANGELOG.md)** — build-time decisions and per-phase outcomes.
- **[archive/](./archive/)** — historical phase handoffs, audits, bug catalogs, test plans.

## Project root

- **[../CLAUDE.md](../CLAUDE.md)** — current-state DNA + active rules (loaded every session).
- **[../BLOCKERS.md](../BLOCKERS.md)** — open carry-forward items.

<!-- Gap fixed (Stage D gap-check pass, this head): the index previously linked neither
     DECISIONS_FOR_OPERATOR.md nor KEYCHAIN_DEV_SIGNING.md, though both exist on disk
     (git cat-file -e passed for both at this head) and both are cited by name from
     CLAUDE.md and from every other Stage D draft (FACTS.md, OPEN_QUESTIONS.md,
     README.draft.md, RELEASE_NOTES.draft.md, RELEASE_RUNBOOK.draft.md,
     OPERATOR_BRIEFING.draft.md). No other line changed; docs/PLUGIN_DEVELOPMENT.md's
     stale panel-registration content (R15-DOCS-015, blocked_tier4) is a content issue
     inside that file, not an index-listing issue, and is left to the operator's
     standing disposition rather than silently patched here. -->
