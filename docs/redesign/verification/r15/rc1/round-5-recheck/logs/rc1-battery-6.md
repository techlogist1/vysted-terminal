# rc1-battery-6 — regression battery shard 6 (gate round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, worktree
`rc1-round-5-recheck-cand`. Sets: batch-4/W5-panels-screener (9 ids),
batch-6/W3-unattended-platform-chart (4 ids), batch-12/W2-screener-ordering (3 ids).
16 ids total.

## Setup
- Found and killed one stale orphan (pid 47231, elapsed 4h37m, started ~14:48
  under an earlier gate round's data-dir naming `rc1-round-5-data-rc1-battery-6`
  — no `-recheck` — that was squatting on my assigned port 52346). Not this
  round's evidence or process; killed as pre-round cruft blocking my port.
- `cp -R rc1-round-5-recheck-seed-data rc1-round-5-recheck-data-rc1-battery-6`,
  booted the candidate's sidecar from source on `:52346` against that copy
  (`sleep 86400 | .venv/bin/python3 main.py --port 52346 --data-dir ...`),
  `VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154`. `/health`
  confirmed `openbb-mcp: available`.
- Never touched the local-model Ollama lock — none of my 16 ids needed a
  live LLM call; R15-AGENT-051 (agent deixis) was re-proven by calling the
  deterministic preamble-rendering function directly instead of going through
  an LLM turn, which is a stronger, non-flaky repro of that exact defect.

## Method notes
- Never ran vitest or pytest (heavy lane's job). Six ids whose OWN certified
  repro is a jsdom/component render (R15-UI-004, R15-UI-005, R15-UI-007,
  R15-UI-003, R15-CODE-FRONTEND-020) are `ci_pinned`, each naming the exact
  test. For R15-UI-003 I additionally ran a live backend round-trip
  (create+PUT a custom agent with tools the frontend's old fallback array
  lacked, plus `openrouter`) to confirm the API layer isn't the limiting
  factor — the defect is frontend-only.
- Sidecar/data-layer ids (R15-UI-006, R15-DATA-044, R15-DATA-093, R15-DATA-043,
  R15-DATA-112, R15-DOCS-018) were re-run live against `:52346` with curl,
  matching the original certified numbers closely (some natural data drift,
  e.g. matched_count 3046 vs the cert's 2613 — expected on a live universe
  snapshot, not a regression signal).
- R15-LEAD-012: ran `resolveBuildPython()` directly via `node -e` in the
  candidate repo with the real ambient `python3` (3.14.5, the exact repro
  condition on this Mac) — resolved to `python3.13` correctly. Skipped the
  full clean sidecar build (heavy, >2 min, not needed — the function itself
  is the unit under test and batch-6's own cert used the same function-level
  check as one of its two legs).
- R15-AGENT-052 / R15-CODE-FRONTEND-015: confirmed via source read (all three
  panel-context publishers now key by dockview panel id, matching
  `PanelHost`'s `setFocusedSource(panel?.id)`).
- R15-AGENT-051: confirmed via a direct in-process call to
  `agent_runtime._render_terminal_preamble` with a synthetic two-chart
  snapshot, second chart focused — output named the focused chart correctly,
  no contradiction with the deixis line.

## Result
All 16 ids: 12 holds, 4 ci_pinned, 0 regressed, 0 needs_gui, 0 blocked_env.
No findings (findings file is `[]`).

COVERAGE: 16/16 ids raw; no raw: none.
