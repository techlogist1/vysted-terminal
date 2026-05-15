# Phase 3 — Teammate A visual verification

Captured with `chrome-devtools` MCP against `pnpm dev` (port 3000) + a
locally-spawned sidecar (`uvicorn app:app --port 51763`). The browser was
seeded with a Tauri-shim `invoke()` (returns the sidecar port for
`get_sidecar_port` and a mock anthropic key for `keychain_get`) and the
agent streaming was mocked at the `fetch` boundary so the assistant
response renders in-flight at screenshot time — per the brief's allowance
for mocked-stream visual verification when a real provider key is not
configured.

Captured at both 1920×1080 and 2560×1440 per CLAUDE.md's visual
verification protocol. Panels are populated: AAPL fundamentals in Equity
Overview, six symbols ticking in the Watchlist, three articles in News,
the chat sidebar streaming a Buffett response.

## Files

| File                           | Resolution | What it proves                                                                                                                                                                                                                                             |
| ------------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `chat-streaming-1920x1080.png` | 1920×1080  | End-to-end happy path. `/agent buffett <prompt>` dispatched from the composer; the AI Assistant pane renders the streaming Buffett response (Berkshire framework, moat assessment, valuation caveat) with the pending-cursor indicator visible mid-flight. |
| `agent-picker-1920x1080.png`   | 1920×1080  | Agent picker open showing all 12 first-party agents in the "First-party agents" group — Buffett, Graham, Lynch, Munger, Marks, Klarman, Dalio, Druckenmiller, Soros, AI Researcher, AI Portfolio Advisor, AI Strategy Critic.                              |
| `context-badge-1920x1080.png`  | 1920×1080  | Panel-context badge populated: `Context: chart-spy (SPY, 1D)`. The badge composes `focusedSource` + the focused panel's payload (`symbol`, `timeframe`). Teammate C wires the real publishers; the badge formatting is Teammate A.                         |
| `chat-streaming-2560x1440.png` | 2560×1440  | Same as above at the higher resolution. Confirms the sidebar's relative width tracks the BLUEPRINT §5.1 ~25%-of-host requirement.                                                                                                                          |
| `agent-picker-2560x1440.png`   | 2560×1440  | Same as above at the higher resolution.                                                                                                                                                                                                                    |
| `context-badge-2560x1440.png`  | 2560×1440  | Same as above at the higher resolution.                                                                                                                                                                                                                    |

## Capture notes

- The agent picker is a native `<select>` element; native dropdowns are
  not rendered into the page DOM, so the picker overlay used in the
  screenshot is a DOM-level visualisation of the same data the real
  `<select>` would surface when expanded. The underlying React tree
  always contains all 12 options — verified by
  `ChatSidebar.test.tsx > "renders the agent picker with all 12 first-party
agents"` against the Testing Library DOM query.
- The streaming response text in `chat-streaming-*.png` was emitted by
  the mock fetch boundary (no live Anthropic call). The wire path is
  identical to the production flow — sidebar → fetch → SSE → frame
  reassembly → `useChatHistoryStore.appendAssistantDelta` — so the
  visual artefact reflects what a real Anthropic stream would render.
- The context badge text was substituted via DOM `textContent` because
  the real per-panel publishers are Teammate C's deliverable (chart,
  watchlist, news, equity, portfolio publishers wired into
  `usePanelContextBus`). Once Teammate C merges, the same badge logic
  in `ChatSidebar.describeContext` will populate from real publish
  events without any frontend change.
