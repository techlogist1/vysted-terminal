# `sidecar/agents/`

First-party AI agent configs. Each `<id>.json` file in this directory whose
schema validates against `_schema.json` becomes a Phase-3 first-party agent
at sidecar startup. The agent runtime (`sidecar/services/agent_runtime.py`,
Teammate A) enumerates this directory on import, validates each file, and
registers the resulting `AgentSpec` instances with the chat sidebar's picker.

## Contract

The schema mirrors `AgentSpec` from `types/plugin.ts` (BLUEPRINT §3.4)
field-for-field. **Changing the schema is a Tier-2 decision** — the
contract itself stays on `types/plugin.ts` (Tier-1 locked), but the
discovery format here is a sidecar-internal convention and may evolve.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable identifier; lowercase + dash/underscore. **NOT** prefixed `custom:` (reserved for user-defined agents). |
| `name` | yes | Display name. |
| `philosophy` | yes | One-line lens / role summary. |
| `systemPrompt` | yes | The actual prompt. Substantive — 200-500 words capturing the agent's framework, not a generic persona blurb. |
| `tools` | yes | Allow-list of tool ids. |
| `defaultProvider` | yes | One of the seven BYOK provider ids. |
| `defaultModel` | no | Optional recommended model. |
| `icon` | no | Lucide icon name or asset path. |

## Phase-3 roster

The twelve first-party agent slots, per the Phase-3 plan's Tier-3 §3.4-vs-§4
roster resolution (`docs/superpowers/plans/2026-05-15-phase-3-ai-layer.md`):

1. `buffett` — Warren Buffett (value, margin of safety)
2. `graham` — Benjamin Graham (deep value)
3. `lynch` — Peter Lynch (growth at reasonable price / PEG)
4. `munger` — Charlie Munger (mental models, lattice)
5. `marks` — Howard Marks (cycles, risk-first)
6. `klarman` — Seth Klarman (contrarian, distressed)
7. `dalio` — Ray Dalio (all-weather, macro principles)
8. `druckenmiller` — Stanley Druckenmiller (concentrated macro)
9. `soros` — George Soros (reflexivity)
10. `researcher` — AI Researcher (equity-researcher pattern)
11. `portfolio_advisor` — AI Portfolio Advisor (rebalancing)
12. `strategy_critic` — AI Strategy Critic (added per Tier-3 BLUEPRINT
    §4 module 38 reference + Use Cases 2/3; forward-compatible with the
    Phase-4 backtest engine)

The Custom Agent Builder (BLUEPRINT module 36) lives separately — its
user-defined agents are persisted in a sidecar SQLite store, not as files
here, and their ids carry the `custom:` prefix. Teammate C owns that flow.

## Adding an agent (post-v0.4.0)

1. Create `sidecar/agents/<id>.json` with the fields above.
2. Validate locally against `_schema.json` (any JSON-schema-draft-07
   validator works; the agent runtime asserts the same invariants).
3. Run `pytest sidecar/tests/test_agent_runtime.py` — the discovery test
   picks up the new file automatically.
4. Add the agent's icon if `icon` references a repo-relative asset.

Plugins contributing agents do so through `capabilities.contributesAgents`
+ `getAgents()` per `types/plugin.ts` — not through this directory.
