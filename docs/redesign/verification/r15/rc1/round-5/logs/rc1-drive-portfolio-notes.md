# rc1-drive-portfolio-notes — round 5 working log

- Candidate HEAD verified: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`.
- Booted own sidecar on `:52324` from candidate source, data dir copied fresh from
  `rc1-round-5-seed-data`; `/health` OK, MCP env pointed at shared `:52153`/`:52154`
  (read-only GET use only).
- Read `src/modules/portfolio/{api.ts,PortfolioPanel.tsx}`, `src/modules/notes/*`,
  `src/lib/{csv.ts,host-actions.ts,sidecar-client.ts}`, `sidecar/services/agent_runtime.py`,
  `sidecar/models/agent.py`, `sidecar/services/agent_tools/catalog.py` before driving.
- First attempt used a scratch jsdom harness copied from the census's
  `surface/portfolio-notes/harness/*.s2c.test.tsx` re-pointed at the candidate + `:52324`.
  It crashed on every test (`Cannot read properties of null (reading 'useCallback')` —
  a duplicate-React-copy symptom) because the harness lived outside the candidate's own
  directory tree, so Vite's per-file module resolution picked up two different physical
  `react` installs. Diagnosed as a harness artifact of my own scratch layout, not a product
  bug, and abandoned in favour of the candidate's own pinned tests (`PortfolioPanel.test.tsx`
  etc.), which is both the mechanism the register's `fixed` entries were actually pinned
  against and the precedent `rc1-drive-composer-chat` used this round.
- Ran the candidate's own pinned suite (`pnpm vitest run` on the 5 portfolio/notes test
  files) and the sidecar's pinned intent-gate pytest — both green, no regression on any of
  the 6 fixed SURF-PORTFOLIO-NOTES-mapped register entries.
- Confirmed via code-read that the two open/low register entries (UI-078 validation,
  UI-079 CSV formula injection) are unchanged — correctly still open, not this drive's job
  to fix.
- Noticed `context-provider.ts` now imports `useNotesStore` (it didn't at census time) —
  traced to the `R15-AGENT-020` fix (notes were write-only for the agent; now they ride
  `__notes__` on every invocation, with the focused symbol's excerpt inlined into the text
  preamble server-side). Since this is new ground squarely inside my group's surface
  (notes → agent), ran a live prompt-injection probe: wrote an injected instruction into a
  symbol's note, focused that symbol, asked a benign portfolio question via local
  llama3.1:8b (`--autonomy auto`) against my own sidecar, under the Ollama lock (acquired
  immediately, released via the `trap ... EXIT` pattern). The model called the sane tool
  (`get_portfolio`) and ignored the injected instruction. Also confirmed by code-read that a
  host-action tool call never mutates anything server-side (it only emits an SSE directive
  for the frontend to apply) — so even a successful injection here could not have silently
  deleted anything.
- Ran a handful of direct malformed-symbol quote probes (300-char, `$$$`, doubled
  `.NS.NS` suffix) against my own sidecar — all honest 404s, no 500/stack trace.
- Stopped own sidecar (killed its detached shell's pid) at the end of the drive; left the
  shared `:52152` stack and every other owner's port untouched.
