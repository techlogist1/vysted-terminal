# Census — Code sweep: `agent-tools-catalog-ledger`

**Subsystem:** Agent Tools + Capability Catalog + Ack Ledger (`CODE_PARTITION.json`)
**Responsibility (as partitioned):** `catalog.py` is the single source of truth every tool
schema, allow-list and MCP projection derives from (Constitution Principle II). Bundles the
cross-domain read-only agent tools, plus `action_ledger.py` backing the confirm-before-place gate.
**Owning files:** 15 (3155 LOC partitioned; 5197 LOC in the package as it stands today)
**Method:** `aposd-critique` skill invoked and followed. **Assessment independence: degraded
(sequential — both personas run in one head, no sub-agents).** Every verdict carries file:line.
**Mode:** read-only on the repo. No process started/stopped. No GUI. No POST to the live app.

---

## Tactical Tornado verdict

**Risk: MEDIUM-HIGH.** This is not tornado code — it is careful, well-commented, tested code with
a genuinely good central idea (one catalog, projected). The damage is subtler and worse for it:
**the catalog's configurability is theatre.** Five of the `Capability` dataclass's knobs
(`internal`, `mcp`, `aliases`, `default_grant`, and the `mcp_endpoint` kind) have never once been
set to a non-default value across all 50 entries, and one of them (`mcp`) is *unconditionally
overwritten* 1300 lines after it is declared. Four differently-named projection functions return
the identical list. The next maintainer will read `agent_selectable_tool_ids()` as an allow-list,
reason about it, and be wrong — it is the identity function.

Eleven flags found. The most damning is not a dead flag, it is **`run_custom_backtest` advertising
`readOnlyHint=true` on the external MCP surface while writing to `backtest_store`**
(`catalog.py:905` → `mcp_server.py:153` → `run_custom_backtest.py:116`): a declared safety hint
that is false.

The second-most damning is a one-line honesty divergence: **`market_overview` turns a total
news-feed outage into `headlines: []` with `ok: True`** (`market_overview.py:90-91`) while its
sibling `news_tool` returns `ok: False` for the identical raise. In a product whose stated moat is
data trust, one of the two is lying to the user.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **pass** | `catalog.py:1-25` — one declaration, five consumers; `test_capability_catalog.py` + `test_mcp_catalog_parity.py` lock the projections | The central bet is right; it is the follow-through that slipped |
| 2 | Deep modules | **at-risk** | `__init__.py:121-134` `register_v0_6_0_tools()` calls `registry_v0_6_0.register_v0_6_0_tools()` — same name, same signature, zero added value; `catalog.py:109-135` `_cap()` forwards 10 params verbatim | Two pass-through layers the reader must walk through to find the real code |
| 3 | Information hiding | **at-risk** | `catalog.py:1471-1474` rewrites `CAPABILITY_CATALOG` after construction, so the `mcp=` a reader sees at each entry is not the value that ships | The module's own declared inputs are not its outputs |
| 4 | Information leakage | **violate** | `catalog.py:1557-1560` (prose: "the runtime computes its outer guard") ⟷ `agent_runtime.py:615-616` (`if event.name == "research"`). Also `__init__.py:74-87` + `:103` encode "backtest_summary is the only import-time tool" in three places | Setting `timeout_seconds=` on the `research` entry is silently ignored; a second import-time registration is silently dropped by `reset_for_tests` |
| 5 | General-purpose is deeper | **violate** | `agent_runtime.py:615-616` hardcodes one tool id inside the general catalog-driven timeout mechanism | Special-general mixture: the general path has a name-matched exception |
| 6 | Different layer, different abstraction | **at-risk** | `schemas.py:36-39` and `catalog.py:1486-1493` are both "filter by `internal`" — and `internal` is never False (verified: `internal_tool_ids()` returns all 50) | A layer that exists to narrow, narrows nothing |
| 7 | Pull complexity downward | **violate** | The `{"ok": False, "error": …}` envelope + arg validation is hand-copied in ~20 handlers: `analyst_tools.py:37-42`(×3), `earnings_tools.py:48-51`(×3), `macro_tools.py:46-49`, `sec_tools.py:66-69`(×3), `price_data.py:54-57`, `news_tool.py:47-50` — while `invoke_tool` (`__init__.py:62-67`) stays a bare `await handler(args)` | Every new tool re-derives the envelope and gets it slightly different |
| 8 | Better together or apart | **pass** | Per-domain handler files with a `register()` each (`sec_tools.py:155`, `macro_tools.py:87`, …) genuinely removed merge contention; the aggregator ordering comment (`registry_v0_6_0.py:5-7`) is honest about why |  |
| 9 | Define errors out of existence | **violate** | `domain_of`/`is_read_only`/`timeout_for` (`catalog.py:1543-1563`) each return `X \| None` where `None` conflates "unknown tool" with "no value". `is_read_only` is saved only by the caller writing `is True` (`agent_runtime.py:1303`) | A tri-state on a safety-adjacent read; the next caller who writes `if not is_read_only(t)` inherits a different meaning |
| 10 | Design it twice | **at-risk** | `catalog.py:1469` `_MCP_INTERNAL_ONLY = {"backtest_summary"}` — one hand-kept exclusion carrying an axis ("session-local") that the rule at `:1472` cannot express | The rule projects `run_custom_backtest` (the *writer* of the session-local run_id) while excluding `backtest_summary` (its *reader*) |
| 11 | Comments describe non-obvious | **pass** | `action_ledger.py:32-37` explains the two-thread race the lock exists for — exactly the comment the code cannot express |  |
| 12 | Comments first | **at-risk** | `catalog.py:94-95` documents `aliases` as "lets the MCP projection keep a familiar name" — repo-wide grep finds zero readers of `.aliases` | A comment describing a feature that does not exist |
| 13 | Choosing names | **at-risk** | `internal_tool_ids()`, `agent_selectable_tool_ids()`, `default_grant_tool_ids()` (`catalog.py:1491,1520,1531`) are three names for one value (verified identical) | Names promise three distinctions; there is one set |
| 14 | Modifying existing code | **violate** | `registry_v0_6_5.py:1-27` — a 27-line no-op module whose docstring (`:4-8`) states it exists to keep a §6.5 grep returning zero matches; still called from `app.py:214` and `main.py:68` | Special-casing to satisfy a test, kept alive across phases |
| 15 | Consistency | **violate** | Four `limit` conventions in one package: `news_tool.py:37` `max(1,min(100,…))`, `macro_tools.py:72` `max(1,min(50,…))`, `analyst_tools.py:29` `[:60]`, `earnings_tools.py:75` `[:12]`, and `sec_tools.py:49-52,126-130` **no clamp at all**. Four error prefixes for one failure class: `"provider error: "`, `"unexpected error: "`, `"news fetch failed: "` (`news_tool.py:50`), `"tool {name!r} raised: "` (`agent_runtime.py:670`) | The model sees four spellings of the same event and cannot pattern-match recovery |
| 16 | Code should be obvious | **violate** | `catalog.py:118` declares `mcp: bool = False` as a settable parameter; `catalog.py:1472` discards whatever it was set to. Nothing at the declaration site warns the reader | A parameter that looks live and is not |
| 17 | Design for the future | **at-risk** | `ToolKind` declares `mcp_endpoint` (`catalog.py:59-61`) with zero uses repo-wide, and the projection rule at `:1472` keys on `read_handler` only — so a future `mcp_endpoint` entry would get `mcp=False`, the exact opposite of its documented meaning | Latent: speculative generality that is also wired backwards |
| 18 | Performance as design | **pass** | `action_ledger._prune_locked` (`:40-45`) prunes on every access so the dict is bounded by TTL; `analyst_tools.py:26-29` caps rows for the prompt budget with a stated reason |  |

**Summary: 5 pass, 7 at risk, 6 violate — 5/18 pass.**
First run for this target; no trend. (Snapshot not persisted — this census writes to the R15 tree.)

---

## What's working

- **The central bet is correct and enforced.** One catalog → adapters (`schemas.py:36-39`), MCP
  (`mcp_server.py:141-153`), the custom-agent allow-list (`models/custom_agent.py`). Two audits
  lock the parity (`test_capability_catalog.py`, `test_mcp_catalog_parity.py`). Most projects
  would have three drifting lists; this one has one list and a rewrite rule.
- **Failure isolation in the fan-out tools is real, not claimed.** `compare_symbols._compare_one`
  (`:43-61`) and `market_overview._quote_one` (`:55-66`) each return a per-symbol `error` field so
  `asyncio.gather` never aborts a batch on one bad ticker.
- **`action_ledger` is the best-designed file in the subsystem.** 95 lines, one lock, a
  comment that names the exact race it defends (`:32-37`), TTL pruning on every access, and an
  explicit "no secrets ever ride this ledger" (`:13`). Nothing to cut.
- **The timeout hint mechanism** (`catalog.py:1566-1589`) ends a timed-out turn with a per-domain
  next step instead of a shrug — a small piece of product thinking inside a plumbing file.

---

## Priority findings

### [P0] `run_custom_backtest` advertises `readOnlyHint=true` on the external MCP surface while it writes
- **Principle:** 9 (define errors out of existence) / 16 (obviousness) — a declared safety hint that is false.
- **Evidence:** `catalog.py:905` `read_only=True` → `mcp_server.py:153`
  `annotations=ToolAnnotations(readOnlyHint=capability.read_only)` → `run_custom_backtest.py:116`
  `backtest_store.put(result)`. `catalog.py:14-17` states `read_only` "is the single declaration
  that drives BOTH the internal mutation gate and the external MCP `readOnlyHint`".
- **Complexity symptom:** Unknown unknowns.
- **Why it matters:** MCP clients use `readOnlyHint` to decide what to run without prompting the
  user. A tool flagged read-only that persists a run into the shared backtest store gets
  auto-approved. `read_only` is currently conflating "places no order" with "has no side effects";
  one field cannot carry both, and the §6.5 story depends on it carrying the first honestly.
- **Fix:** Set `read_only=False` on the `run_custom_backtest` entry (it is a write), or split the
  field into `no_order_path` (the §6.5 gate) and `no_side_effects` (the MCP hint).

### [P1] `market_overview` turns a total news-feed failure into a silent empty list
- **Principle:** 15 (consistency) / 9 (define errors out of existence).
- **Evidence:** `market_overview.py:87-92` — `except (ProviderError, Exception): return []`, and
  the caller at `:127-132` returns `ok: True` with `headlines: []` and no failure field.
  `news_provider.py:384` genuinely raises `ProviderError("all news sources failed")`. The sibling
  `news_tool.py:44-50` returns `{"ok": False, "error": …}` for that same raise.
- **Complexity symptom:** Unknown unknowns.
- **Why it matters:** The model receives "the market has no headlines today" and says so. Two tools
  in one package, one provider, opposite honesty policies — and the honest one is not the one on
  the "how's the market today" path, which is the single most-used broad query.
- **Fix:** Return `{"headlines": [], "headlines_error": str(exc)}` from `_headlines` and pass it
  through at `:127-132`. Four lines.

### [P1] `compare_symbols` ranks returns computed over different windows and hides it
- **Principle:** 4 (information leakage) / 16 (obviousness).
- **Evidence:** `compare_symbols.py:28-40` `_return_pct_window` = `(bars[-1]/bars[0]-1)*100` with
  no length/start check; `:156-160` ranks `best`/`worst` directly off it; the returned per-symbol
  dict (`:87-110`) carries `return_pct_window` as a bare float with **no window start and no bar
  count**.
- **Repro (proven):** a symbol with 2 bars since listing at +30% outranks a symbol with a full 6-month
  window at +5%; `best = NEWLY_LISTED`. Verified numerically against the function's own arithmetic.
- **Complexity symptom:** Change amplification (every consumer must re-derive the caveat) + wrong
  money-relevant output.
- **Why it matters:** `compare_symbols` is the tool the catalog tells the model to reach for on
  "NVDA vs AMD" (`catalog.py:199-204`). Indian mid-caps and recent listings are exactly the case
  where the windows diverge, and the payload gives the model no way to notice.
- **Fix:** Add `bars` and `window_start` to each symbol dict, and rank only across symbols sharing
  a common start (else return `relative: {best: null, worst: null, note: "windows not comparable"}`).

### [P1] The catalog's configurability is dead — five knobs, zero uses, one silently clobbered
- **Principle:** 16 (obviousness) / 13 (naming) / 17 (design for the future).
- **Evidence (all verified by running the projections):**
  - `internal` (`catalog.py:91`) and `default_grant` (`:101`) are never `False` in any of the 50
    entries → `internal_capabilities()`, `internal_tool_ids()` (`:1491`),
    `agent_selectable_tool_ids()` (`:1520`) and `default_grant_tool_ids()` (`:1531`) all return
    the same 50 ids.
  - `aliases` (`:96`) has zero readers repo-wide.
  - `mcp` (`:93`, settable at `:118`) is unconditionally overwritten at `:1471-1474`.
  - `_cap()` (`:109-135`) re-declares every one of `Capability`'s defaults, so changing a default
    on the dataclass silently has no effect on the catalog.
- **Complexity symptom:** Cognitive load + unknown unknowns.
- **Why it matters:** `agent_selectable_tool_ids()` reads as the Custom Agent Builder's *allow-list*
  and is documented as such (`catalog.py:10-12`); it is the identity function, so every custom
  agent is offered `propose_order`, `portfolio_delete_position` and `set_region`. The next
  maintainer who sets `internal=False` on an entry to hide it will find the flag works — and will
  not know it is the first caller ever to exercise that path.
- **Fix:** Delete `_cap` and build `{c.id: c for c in [Capability(...), ...]}` (removes 27 lines and
  the duplicated defaults); delete `aliases` and the `mcp` field; collapse the four projections to
  one until a second real value exists for `internal`/`default_grant`.

### [P2] `mcp_endpoint` is declared, documented backwards, and unreachable
- **Principle:** 17 (design for the future) / 12 (comments first).
- **Evidence:** `catalog.py:59-60` documents `mcp_endpoint` as "projected **only** to the external
  MCP surface"; `catalog.py:1472` sets `mcp=(cap.kind == "read_handler" and …)`, so an
  `mcp_endpoint` entry would get `mcp=False` and be projected **nowhere**. Zero uses repo-wide.
- **Complexity symptom:** Unknown unknowns — the trap only springs when someone finally uses it.
- **Fix:** Delete the `mcp_endpoint` member, or change the rule to
  `kind in ("read_handler", "mcp_endpoint")`. One line either way; pick deletion until there is a caller.

### [P2] `research`'s timeout contract is split between a prose comment and a hardcoded tool name
- **Principle:** 4 (information leakage) / 5 (general-purpose is deeper).
- **Evidence:** `catalog.py:1557-1560` — "`research` declares no budget here: the runtime computes
  its outer guard" — paired with `agent_runtime.py:615-616` `if event.name == "research": return
  _research_guard_seconds(...)`. Nothing links them mechanically.
- **Complexity symptom:** Change amplification.
- **Why it matters:** `research` is the only tool in the catalog with `timeout_seconds` omitted, and
  a maintainer adding one there gets no error and no effect. The general mechanism has a
  name-matched special case inside it.
- **Fix:** Add `timeout_from_args: bool = False` to `Capability`, set it on the `research` entry,
  and have `_tool_timeout_seconds` branch on the flag rather than on a string literal.

### [P2] The error envelope is copy-pasted ~20 times in four incompatible spellings
- **Principle:** 7 (pull complexity downward) / 15 (consistency).
- **Evidence:** `analyst_tools.py:37-42` (×3, identical), `earnings_tools.py:48-51` (×3),
  `macro_tools.py:46-49` + `:77-80`, `sec_tools.py:66-69` (×3), `price_data.py:54-57`,
  `news_tool.py:47-50`, against a bare `return await handler(args)` in `invoke_tool`
  (`__init__.py:62-67`). Prefixes: `"provider error: "`, `"unexpected error: "`,
  `"news fetch failed: "`, and the runtime's own `"tool {name!r} raised: "` (`agent_runtime.py:670`).
- **Complexity symptom:** Change amplification — the 21st tool re-derives it and gets a fifth spelling.
- **Fix:** Move the `try/except ProviderError/except Exception → {"ok": False, "error": …}` wrapper
  into `invoke_tool` and delete it from the handlers. The registry is the one place every tool
  already routes through.

### [P2] `sec_tools` is the one tool family with no `limit` clamp
- **Principle:** 15 (consistency).
- **Evidence:** `sec_tools.py:49-52` and `:126-130` parse `limit` and fall back to a default on a
  bad parse, but never clamp — `limit: 100000` and `limit: -1` pass straight to
  `sec_filings_provider.list_filings` / `list_insider_transactions`. Every sibling clamps:
  `news_tool.py:37`, `macro_tools.py:72`, `analyst_tools.py:29`, `earnings_tools.py:75`.
- **Complexity symptom:** Cognitive load — four conventions to learn in one package.
- **Fix:** One `_clamp_limit(args, key, default, maximum)` in `agent_tools/__init__.py`, called by
  all five families.

---

## Minor observations

- `earnings_upcoming` is the only handler whose `int()` parse is unguarded: `earnings_tools.py:31`
  `days = int(args.get("days", 7) or 7)`. `days: "seven"` raises `ValueError` out of the handler
  (verified) and the model gets the runtime's generic `"tool 'earnings_upcoming' raised: invalid
  literal for int()"` instead of the tool's own `"days must be in [1, 60]"`. Siblings all guard
  (`macro_tools.py:71-74`, `news_tool.py:36-39`, `sec_tools.py:49-52`).
- `market_overview` returns `region: "GLOBAL"` with the **US** index set and no note.
  `market_overview.py:32-34` explains the fallback in a source comment; `:51-52` applies it;
  `:127-132` ships the payload without it. The invariant is held by a comment the model never
  reads. One `"note"` key fixes it.
- `_MCP_INTERNAL_ONLY` (`catalog.py:1469`) has no axis for account-scoped or credit-spending reads:
  `broker_portfolio` (the user's real positions/equity/buying power), `web_search` and `research`
  (which spend the user's BYOK Exa/Perplexity credits) are all auto-projected to MCP purely because
  they are `read_handler`. Blast radius is bounded by the loopback-only bind
  (`mcp_server.py:381`), which is why this is a note and not a finding — but the rule cannot
  express the distinction, and finding P1 deletes the very field (`mcp`) that could.
- `compare_symbols.py:69` and `:84` write `except (ProviderError, Exception)` — `ProviderError`
  is already an `Exception`, so the tuple is noise that reads as a deliberate distinction.
  More consequentially, the attribute reads at `:97-104` sit **outside** that guard, so a
  fundamentals object missing a field raises out of `_compare_one` and aborts the whole
  `gather` — contradicting the module docstring's failure-isolation promise at `:9-12`.
- `registry_v0_6_5.py` (27 lines) exists, per its own docstring at `:4-8`, to keep a §6.5 grep
  returning zero matches. Called from `app.py:214` and `main.py:68` to log one debug line.
- `action_ledger.KNOWN_STATUSES` (`:28`) is exported and documented as the permitted set but is
  never compared against anywhere in the repo; `record()` stores any spelling verbatim (`:55-57`).
  Harmless by design, but the constant reads as validation that does not happen.
- `reset_for_tests` (`__init__.py:70-87`) hardcodes "backtest_summary is the only import-time
  tool" in three places. True today (only `backtest_summary.py:71` registers at import). A second
  one would be silently dropped after every reset, producing order-dependent test flake.

---

## Persona walkthrough

**Tactical Tornado.** A tornado would not have written `catalog.py` — but a tornado is exactly who
grows it from here. The path of least resistance for tool #51 is to copy the nearest `_cap(...)`
block, copy the nearest handler's `try/except ProviderError/except Exception` envelope, and pick
whichever `limit` convention the neighbour used. That is precisely how the package reached four
clamp conventions and four error prefixes. The tornado also leaves `registry_v0_6_5.py` in place
forever (`:1-27`) because deleting it means touching `app.py:214` and `main.py:68` and re-running
the §6.5 grep, and it *works*. And the tornado never notices `catalog.py:1472` silently discarding
the `mcp=` they just set, because nothing errors.

**Strategic Thinker.** The redesign is small and mostly subtractive. Delete `_cap` and inline
`Capability(...)` into a list keyed by `.id` — 27 lines and one duplicated-defaults trap gone.
Delete `aliases`, `mcp`, and `mcp_endpoint` (zero users, one wired backwards). Collapse the four
identical projections into `catalog_tool_ids()` until a second value for `internal`/`default_grant`
actually exists — and if the Custom Agent Builder genuinely should not offer
`portfolio_delete_position`, make `internal=False` real on those entries instead of naming a
function after a filter it does not apply. Pull the error envelope down into `invoke_tool` so the
handlers become what they claim to be: thin domain adapters. Then split `read_only` into
`no_order_path` and `no_side_effects`, which is the one change that turns the P0 from a false
safety hint into a true one. Net: fewer lines, one honest flag, and the projections finally mean
what their names say.

---

## Questions to consider

- If `internal` and `default_grant` have never been `False` in 50 entries, is the right move to
  delete them — or is the real finding that nobody has yet asked whether a custom agent should be
  able to select `propose_order` and `portfolio_delete_position`?
- `read_only` is asked to mean "places no order" (§6.5) and "has no side effects" (MCP
  `readOnlyHint`) at once. Which one does the safety model actually depend on, and what breaks if
  they are split?
- Every handler decides independently whether a provider failure is `ok: False` or a silent empty.
  Should that be a per-tool judgement at all, or a property of the registry?
