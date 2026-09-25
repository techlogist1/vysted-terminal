# batch-23 W1 — R15-LEAD-035 writer evidence

Branch `worktree-agent-batch-23-W1`, base `014bb7f1`. Owned: `sidecar/services/planner.py`,
`sidecar/tests/test_b3_runtime_intent_gate.py`.

## Offline

- `red-014bb7f1.out`: the new pins on base behaviour (the base `_NO_TOOL_CUE` wrapped as `_no_tool_cue` only so
  the gate-off monkeypatch has a target): **13 failed, 47 passed**. Red: 3 keep-surface pins ("No tools except
  price_data", "No tools other than a price lookup", "No tools for the arithmetic; use the tools ...") and 10
  no-tool pins. The six batch-22 regression controls are green on base by design (they pin against W2's
  over-match).
- `focused.out`: `test_b3_runtime_intent_gate.py test_planner.py test_agent_runtime.py` on the fix: **353 passed**.
- `l035-surface.out`: `batch-22/verifier-evidence/b22v_035.py` on the fix: **24/24 OK, BAD 0** ("Skip the tools"
  and "Do NOT use external data" included).
- ruff format + `ruff format --check sidecar` + `ruff check sidecar`: clean.

## Live bar (`b23w_live.py` -> `live.out`, `live2.out`, `live/<tag>.*`)

Source sidecar from this tree on 127.0.0.1:52350, fresh data dir, llama3.1:8b via ollama, agent mode, autonomy
ask. Truth from the same sidecar: `/quotes/TCS.NS` 2082.0, `/quotes/INFY.NS` 1000.2. `/portfolio/positions`
was `[]` before the run and after every case.

| tag | calls | stated | verdict |
|---|---|---|---|
| k-dont-forget | price_data TCS.NS ok | "₹2082.0" | PASS (= /quotes) |
| k-do-not-answer-without | price_data TCS.NS ok | "₹2082.0" | PASS |
| k-why-not-q | price_data TCS.NS ok | "₹2082.0" | PASS |
| k-just-from-market | price_data (list arg, invalid) then TCS.NS ok, INFY.NS ok | "₹2082.0 and ₹1000.2" | PASS |
| k-only-price-data | price_data TCS.NS ok | "₹2082.0" | PASS on the price; it also lists an OHLC "last trade" (close ₹2073.1) from an older bar of the same payload (see issues) |
| k-why-not-bare (turn 2 after k-why-not-bare-t1) | none | no figure | model skipped a call; see run 2 below |
| n-dont-use-add-infy | none | no figure, nothing staged | PASS |
| c-add-tcs | portfolio_add_position staged | "for review ... accept or reject" | PASS (positions stayed `[]`) |
| x-named-exclusion | price_data TCS.NS ok | "₹2082.0" | PASS |

**Re-run (`B23_RUN=-r2`, `live2.out`), the one case that skipped a call.** k-why-not-bare-t1-r2: price_data
TCS.NS (one timeout, one ok), "₹2082.0". k-why-not-bare-r2 (same two-turn shape): read_notes + price_data TCS.NS
ok, "The current price of TCS.NS is ₹2082.0." PASS. Run 1 made no call and stated no figure (nothing fabricated);
the surface it was sent is the full 42-tool read surface (pinned in
`test_data_request_mentioning_tools_keeps_its_surface[Why did you not use the tools]`), so the run-1 skip is
model behaviour, not the gate.

**Tally.** Six keep-surface prompts: 6/6 called price_data and stated the /quotes price (the bare second turn on
the re-run; run 1 skipped with the full surface sent). No-tool add: no call, nothing staged, positions `[]`.
Portfolio add: staged behind review, not applied. Named exclusion: price_data called, ₹2082.0. Fabricated prices
stated: 0. Sidecar (pid 22654) and its stdin sleep (22653) killed after the run.

## Tier-3 decisions (for the verifier)

- **"external data" is an OBJECT** beside SPEC 2's list: PLAN's acceptance requires `b22v_035.py` BAD 0 on all 24
  lines, and "Do NOT use external data. ..." is an expect-no-tools line.
- **`make` takes only `tool/function call(s)`**, never a bare "call": "Don't make a call on it, get TCS price" is a
  judgment call, not a tool instruction.
- **Verb-less forms (`no`/`zero`/`without` + object) take only plural `lookups`/`searches`** (singular `tool`
  kept): "No search results last time; get SIFY price" keeps the surface.
- **Passive form** requires the object to open its clause (only the/any/your/all before it), so "Web search should
  not be used" (a named tool) keeps the surface.
- **Clause ends** also include a spaced ASCII hyphen (" - "); "." and "," end a clause only before whitespace, so
  "TCS.NS" and "3,100" stay whole.
- Everything else follows the PLAN's rules 1-9 as written (lead-in list for from-given, snake_case id rule,
  double negative on every form, named exclusion == gate-off surface).

