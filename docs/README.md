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
- **[research/redesign/](./research/redesign/)** — the reference study (Cursor, OpenBB,
  Fincept, MCP patterns, landscape) + `REFERENCE_SYNTHESIS.md` (design implications).

## Architecture references (current)

| Doc                                                | Covers                                                                                          |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [BLUEPRINT.md](./BLUEPRINT.md)                     | Original architectural blueprint — §2 locked decisions, §6.5 safety, module catalog, phase plan |
| [SAFETY_ARCHITECTURE.md](./SAFETY_ARCHITECTURE.md) | §6.5 execution-safety enforcement, file:line pointers, revert procedure                         |
| [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)         | MCP on both sides — proxied subprocesses + the serve-out FastMCP surface                        |
| [SIDECAR_API.md](./SIDECAR_API.md)                 | Sidecar HTTP surface overview                                                                   |
| [PLUGIN_DEVELOPMENT.md](./PLUGIN_DEVELOPMENT.md)   | The `VystedPlugin` six-capability contract and how to build a plugin                            |
| [BROKER_INTEGRATIONS.md](./BROKER_INTEGRATIONS.md) | Per-broker setup, Kite read-only OAuth, static-IP UX                                            |
| [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)             | Design tokens and the (current) visual language                                                 |
| [PHASE_10_HANDOFF.md](./PHASE_10_HANDOFF.md)       | Latest phase handoff (copilot + integrations + reskin)                                          |

## History

- **[../CHANGELOG.md](../CHANGELOG.md)** — build-time decisions and per-phase outcomes.
- **[archive/](./archive/)** — historical phase handoffs, audits, bug catalogs, test plans.

## Project root

- **[../CLAUDE.md](../CLAUDE.md)** — current-state DNA + active rules (loaded every session).
- **[../BLOCKERS.md](../BLOCKERS.md)** — open carry-forward items.
