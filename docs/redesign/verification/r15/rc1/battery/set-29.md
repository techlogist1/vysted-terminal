# batch-7/W5-agent-writes-portfolio

`R15-UI-082` is `open`+`low`; `R15-UI-084` is `needs_gui`+`medium`; `R15-UI-086` is `fixed`+`medium`;
`R15-UI-088` is `blocked_tier4`+`medium`; the 5 `CODE-PLATFORM-0{34,36,38,40,42}` entries are
`open`+`low`. Own sidecar: candidate `4c6dfe8c`, `127.0.0.1:52345`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-082 | Live `POST /workspace` with `name:"मेरा लेआउट २"` and with a 260-char name, both with `-w "%{http_code}"`. | Unicode name: `HTTP 200`, `{"status":"saved",...}` — saves cleanly (no 400 at all). 260-char name: `HTTP 400`, `"Workspace name '…' is too long to save."` — a clean, readable 400, not the register's documented `500 "Errno 63 File name too long"`. **Both halves of this entry now behave better than the register describes**, even though the register still tags it `open`/`low` — flagging the register for a status refresh rather than treating this as a regression (nothing certified got worse; the opposite happened). | holds (better than documented; register status looks stale — flag for the lead, not a fix-round item) |
| R15-UI-084 | Read `src/store/agent-dock.ts`. | `AGENT_DOCK_MAX_WIDTH = 1200` still hard-caps the dock; the drag-resize behavior itself needs a real display to observe. Unchanged. | needs_gui (unchanged) |
| R15-UI-086 | Read `src/components/CommandPalette.tsx`'s row renderer. | `binding = useKeybindingsStore(...).bindingFor(item.commandSpec.id)`, and the `<kbd>` chip renders only `{binding && ...}` — "a row only ever shows a chord that actually fires" per the comment. This is the real fix: every bound action/panel row now shows its actual shortcut, not just the static "Enter" on the Ask-agent row (which is unrelated and unchanged). | holds |
| R15-UI-088 | `grep playwright` over `package.json`; searched for `playwright.config.*` and `*.e2e.*` outside `node_modules`. | No Playwright dependency, config or e2e spec exists anywhere in the candidate tree. Unchanged — no automated drag-drop coverage exists. | blocked_tier4 (unchanged, per DECISIONS; not a fix-round item) |
| R15-CODE-PLATFORM-034 | In-process `services.backtest_engine._slice_dates("2024-01-01","2024-01-11",2)`; read the slice filter. | `[('2024-01-01','2024-01-06'), ('2024-01-06','2024-01-11')]` — `2024-01-06` is still the end of slice 1 AND the start of slice 2, and the bar filter is still `slice_start <= b.timestamp <= slice_end` (both ends inclusive) — the boundary bar is still traded in both slices. Unchanged. | holds (unchanged known-open) |
| R15-CODE-PLATFORM-036 | Read `CustomDslStrategy.__init__` in `services/backtest_dsl.py`. | Still calls `validate_definition(params)` (which compiles both rules internally to build its report) and then calls `compile_rule` again for `entry` and `exit` separately — the double-compile is unchanged. | holds (unchanged known-open) |
| R15-CODE-PLATFORM-038 | Read `ChatSidebar.tsx`'s `ErrorRow`/`onRetry` wiring; `streaming.ts`'s error-code constants. | `onRetry` is attached whenever `lastPrompt` exists, with no branch on `frame.code`; the comment literally reads "Retry stays." The declared error-code union (`provider_402`, `auth`, `model_not_found`, …) still has no consumer that hides Retry for an unretryable code. Unchanged. | holds (unchanged known-open) |
| R15-CODE-PLATFORM-040 | `grep -rn "price_asian_mc\|price_barrier_mc\|from .monte_carlo\|from services.quant.monte_carlo"` across the whole candidate tree. | 0 hits outside `monte_carlo.py` itself — still no importer anywhere. Unchanged, still dead code. | holds (unchanged known-open) |
| R15-CODE-PLATFORM-042 | Read `services/quant/greeks.py::compute_greeks`. | Still builds its own `build_bsm_process` → `ql.PlainVanillaPayoff` → `ql.VanillaOption`/`AnalyticEuropeanEngine` pipeline line-for-line instead of calling `services/quant/options.py::price_european_bs`. Unchanged. | holds (unchanged known-open) |

Raw output: `raw/set-29/UI-082.txt`, `UI-084.txt`, `UI-086.txt`, `UI-088.txt`,
`CODE-PLATFORM-034.txt`, `CODE-PLATFORM-036.txt`, `CODE-PLATFORM-038.txt`,
`CODE-PLATFORM-040.txt`, `CODE-PLATFORM-042.txt`.
