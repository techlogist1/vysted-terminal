# XADV triage — keyless + realuser adversaries @ d38b5d1a

Triage: fresh context, judgement tier (Opus 5.5). This agent neither found nor will fix these findings. Rubric R1-R5 per
`docs/redesign/verification/r15/tooling/final-pass.js`. Register at
`git show d38b5d1a:docs/redesign/verification/vysted-r15-register.json` (the working tree adds LIFECYCLE-001 fixed and
LEAD-125/126 open, so the next free id is R15-LEAD-127). Reproduced at sha `d38b5d1a2487bd52fe8a7e741a3a5266e3206611`:
the scratch worktree `final-cand` HEAD equals it, and its `sidecar/services/research/fast.py` is byte-identical to `git show d38b5d1a:...`.

## Rulings

| key | ruling | id | sev (R2) | one line |
|---|---|---|---|---|
| realuser:3 | admit | R15-LEAD-127 | critical | Research binds the US instrument, then runs price + fundamentals on the bare ticker under the session region, so the brief shows the Indian namesake's money figures as true |
| realuser:5 | attach | R15-LEAD-127 | (critical) | The same seam on the copilot surface: `price_data`/`fundamentals` take only a symbol, so a bare collision ticker always binds the session region. One item, both keys (R3) |
| keyless:4 | admit | R15-LEAD-128 | medium | `price_data` fetches 6 months of history before the quote. The research brief's 6 s price box therefore drops a quote that answers in 0.25 s whenever nse_direct history is slow |
| keyless:3 | admit | R15-LEAD-129 | medium | README keyless section keeps the false promises R15-UI-052 removed from the app (keyless web research, "fully offline"), and its BYOK list omits OpenRouter |
| realuser:1 | admit | R15-LEAD-130 | medium | Autocomplete (palette + watchlist) cannot find a company by its former name or its BSE scrip code, though /resolve binds both |
| realuser:2 | admit | R15-LEAD-131 | medium | The identity cross-check flags the correct company (`&` vs `and`) as a possible mis-resolution in /fundamentals and the brief. The raw `-$` BSE name suffix is shown on 310 scrips |
| keyless:1 | admit | R15-LEAD-132 | low | The NSE EOD warm stamps a holiday (2 Oct) as the trade date on 1 Oct's rows |
| keyless:2 | admit | R15-LEAD-133 | low | When Ollama was never installed, the user is told to "start Ollama" and the guided setup with the install link never opens |
| keyless:5 | admit | R15-LEAD-134 | low | The 8 s FAST web-round box is shorter than the keyless chain's 6 s per-engine deadlines, so Mojeek is never reached and the trace says "no web backend" for a timeout |
| realuser:4 | attach | R15-LEAD-057 | (open low; recommend medium) | The SEC slash listing suffix (`/DE/`, `/NEW/`) survives the symbol_resolver suffix strip |
| realuser:6 | attach | R15-LEAD-053 | (open low) | Retired ticker typed into /quotes or price_data gets a 404 with no rename hint (IBULHSGFIN, ANGELBRKG) |
| keyless:A1 | attach | R15-DOCS-003 | (blocked_tier4) | README.md:26-27 still says Next.js. README is in DOCS-003's files |
| keyless:A2 | attach | R15-RELEASE-002 | (blocked_tier4) | README.md:87-90 sends users to an empty Releases page. README is in RELEASE-002's repro |

None of these are known_limitation, needs_gui or refute. On known_limitation for realuser:5, see its section below.

## THE DECIDING QUESTION — realuser:3 + realuser:5 vs R15-DATA-002

### What I checked

**DATA-002 at the sha:** critical, `blocked_tier4`.
- Files: `src/lib/sidecar-client.ts`, `src/modules/equity-overview/{api.ts,EquityOverviewPanel.tsx}`, `sidecar/routers/quotes.py`, `sidecar/routers/fundamentals.py`, `sidecar/services/resolution_policy.py`.
- root_cause: "the frontend sends only the global settings region ... loadEquityOverview fans out on the bare symbol, dropping the region/yahoo_symbol of the /resolve candidate the user actually picked. The sidecar honours a per-call X-Vysted-Region header, but nothing supplies it per instrument."
- fix_shape: entirely frontend (carry the picked instrument and send a per-call region header).
- note: rc1 audit round 1 failed on the chart leg; gate round 2 on the watchlist leg; the batch-26 third failure was the agent `add_to_watchlist` leg. Stopped under DECISIONS 4.15.

**Every DATA-002 commit up to d38b5d1a** (`git log d38b5d1a --grep=DATA-002`, code files only):

| commit | what | files |
|---|---|---|
| `8f8f5f34` | EO leg | host-actions.ts, sidecar-client.ts(+test), equity-overview/api.ts, store/equity-command.ts |
| `102da1c4` | test mock | panel-context-publishers.test.tsx |
| `f053f472`, `60fdc925` | chart leg (batch 12) | CommandPalette.tsx, host-actions.ts, sidecar-client.ts, ChartPanel.tsx, chart/api.ts, chart-command.ts |
| `b91ddef3` | batch-25 WIP, base `ef102fa5`, never merged | sidecar-client.ts, workspace.test.ts, WatchlistPanel.tsx(+test), watchlist/api.ts, store/symbols.ts |
| `4d7bc887` | batch-26, merged `e90728f4`/`76a3b4dc` | the WIP plus CommandPalette.tsx, host-actions.ts(+test), store/command-palette.ts |

`1f05bc5e` matched the grep only through CODE-DATA-002 (resolver memo) and is unrelated. **No DATA-002 commit touches any
sidecar file.** Specifically, none touches `sidecar/services/research/fast.py`, `snapshot_structured`, the
`ResearchTarget.region` threading, `sidecar/services/agent_tools/price_data.py`, the fundamentals handler, or the
`price_data`/`fundamentals` capabilities in `catalog.py`.

**Plans and verdicts naming DATA-002:**
- stage-c `batch-2/PLAN.md:254-269`: EO only. "The sidecar half is covered by the DATA-001 US/IN cases."
- `batch-12/PLAN.md:108,125`: chart only. "W7 needs no sidecar change for DATA-002."
- `batch-25`/`batch-26` VERDICTS: watchlist, palette and agent-add.
- `batch-28/PLAN.md:7`: excluded. `batch-29/PLAN.md:345`: a mention only.
- rc1 `refutation-audit/data-R15-DATA-002.md` and `round-2/...`: chart and watchlist.

A grep of those files for `fast.py|snapshot_structured|price_data|research` near DATA-002 finds nothing. Research shows up
only in DATA-002's `operator_areas` tag.

**DECISIONS:**
- 4.15 lists the agent-add leg as the residual: `add_to_watchlist` takes only a symbol (`catalog.py:1368-1377`, `host-actions.ts:1005-1011`).
- 5.12 is the count ruling.
- Neither mentions research or the quote/fundamentals tools.

The research path's only ticker-collision fix is **R15-DATA-003** (fixed, batch-2/28). It gated the ownership lane in the
same fan-out on the bound region. The price and fundamentals legs were never part of it.

### The mechanism at the sha (code + in-process probe)

`fast.py:580` `target = await resolve_target(...)` binds the right instrument and records `target.region`. Then:
- `fast.py:624` `symbol = target.symbol`.
- `fast.py:654-656` `snapshot_structured(tool_call, symbol, region=region, ...)`. Here `region` is the **session** region, and it is used only by `derive_semantics`.
- `fast.py:351-359` calls `price_data`/`fundamentals` with `{"symbol": symbol}` only.
- The witnesses at `:375-428` run on that bare listing too.
- `target.region` never reaches a leg.

`price_data.py:48-56` and the fundamentals handler resolve the bare ticker through `config.get_region()`.
Their catalog schemas (`catalog.py:248-343`) accept no `region`.

I ran an in-process probe at the sha in `final-cand/sidecar` (`seam_probe.py`). It registers the real `resolve_symbol`,
stubs every other tool, and records what reaches it, with session region IN:

```
QUERY Halliburton  resolved {symbol HAL,  name HALLIBURTON CO,  exchange US, region US}
  LEG ('price_data',   {'symbol': 'HAL'}, 'IN')   LEG ('fundamentals', {'symbol': 'HAL'}, 'IN')
QUERY SailPoint    resolved {symbol SAIL, name SailPoint, Inc., exchange US, region US}
  LEG ('price_data',   {'symbol': 'SAIL'}, 'IN')  LEG ('fundamentals', {'symbol': 'SAIL'}, 'IN')
fresh pairs, not used by the finder:
QUERY Ferrari      resolved RACE / US  -> legs {'symbol':'RACE'} under 'IN'
QUERY Carnival     resolved CCL  / US  -> legs {'symbol':'CCL'}  under 'IN'
QUERY PTC Inc      resolved PTC  / US  -> legs {'symbol':'PTC'}  under 'IN'
```

GET-only control on the shared read-only sidecar :52800:
- `/quotes/HAL` under `X-Vysted-Region: IN` gives 4601.0 INR (Hindustan Aeronautics). Under `US` it gives 31.85 USD (Halliburton).
- `/fundamentals/RACE` under IN gives "Race Eco Chain Limited", RACE.NS, with `identity_note` null.
- `/quotes/RACE` under US gives 388.33 USD.

So once the region is supplied, the sidecar serves the right company. The research seam simply never supplies it.

### Ruling

The research seam and the copilot quote/fundamentals tools were **never in any DATA-002 attempt's scope**, and no attempt
there has failed. By the rule I was given, this is admitted as a new entry, not attached to DATA-002.

- **realuser:3 → admit R15-LEAD-127 (critical, R2):** wrong money-relevant data (price, P/E, market cap) shown as true on the brief's metric cards, with `derived.conflicts` empty.
- **realuser:5 → attach to R15-LEAD-127.** Same mechanism on a second surface (R3): a bare collision ticker reaches `price_data`/`fundamentals` without the region of the instrument meant, and those handlers have no per-call region channel. One fix at that shared seam covers both surfaces.

Honest caveat on realuser:5's chat instance (Run A): llama3.1:8b passed `HAL.NS` itself, so the region bind was not what
broke that turn. The model narrating Hindustan Aeronautics' figures as Halliburton's is local-model attribution, adjacent
to the signed-off R4 class (DECISIONS 4.9-4.12), and no writer touches the figure guard on its account. What realuser:5
contributes is the tool-level probe: MCP `fundamentals {symbol:'HAL'}` returns Hindustan Aeronautics
(`xadv-realuser-raw/t-fund-HAL.json`) and `price_data {symbol:'HAL'}` returns an INR series (`t-price-HAL.json`). That is
the same missing region channel. The acceptance for the copilot side is therefore the tool contract, not llama's prose.

## R15-LEAD-127 — full entry draft (critical)

- **title:** Research binds the instrument the user named, then fills the brief with the session-region namesake's price and fundamentals. 'Halliburton' binds HAL/US, yet the metric cards show Hindustan Aeronautics' INR 4,601, P/E 33.0 and mcap INR 3.08T with no conflict. The copilot's `price_data`/`fundamentals` tools have no region channel, so a bare collision ticker always serves the session region's company.
- **severity:** critical. **area:** research-search (+ agent-chat). **defect_class:** wrong-entity-ticker-collision. **status:** open.
- **keys:** realuser:3, realuser:5.
- **repro:**
  1. Session region IN. MCP `research {query:'Halliburton', depth:'quick'}`. You get `resolved {HAL, HALLIBURTON CO, US, US}`, `structured.price` from nse_direct at 4601.0 INR, and `structured.fundamentals` for HAL.NS with pe 33.003 and mcap 3,077,033,689,088. `derived.conflicts` is `[]`. 'SailPoint' gives Steel Authority of India in the same way.
  2. In-process at d38b5d1a: `gather_fast('Ferrari', region='IN', tool_call=<recorder>)` binds RACE/US, but `price_data` and `fundamentals` receive `{'symbol':'RACE'}` under ambient region IN.
  3. MCP `fundamentals {symbol:'HAL'}` under IN returns 'Hindustan Aeronautics Limited'. No argument can ask for the US listing.
- **evidence:** `final-pass/scenarios/xadv-realuser-2.md`, `xadv-realuser-6.md`, `xadv-realuser-raw/{r-hal.json,r-sail.json,t-fund-HAL.json,t-price-HAL.json}`; this file's probe section; `fast.py:351-359,580,624,654-656`; `price_data.py:48-56`; `catalog.py:248-343`. Outside: https://www.screener.in/company/HAL/consolidated/ 'Current Price: ₹4,601', 'Stock P/E: 33.0'.
- **root_cause:** `ResearchTarget.region` (the bound listing's region) is dropped at the `snapshot_structured` seam. Every leg (price, fundamentals and the witnesses) re-resolves the bare ticker through the ambient `config.get_region()`. The `price_data`/`fundamentals` read handlers expose no per-call region, so the copilot has no way to ask for the other listing either.
- **files (writer owns):**
  - `sidecar/services/research/fast.py` (snapshot_structured + gather_fast caller)
  - `sidecar/services/research/iter.py` (callers :401, :1016)
  - `sidecar/services/agent_tools/deep_research.py` (caller :837)
  - `sidecar/services/agent_tools/price_data.py`
  - `sidecar/services/agent_tools/fundamentals.py` (the fundamentals handler)
  - `sidecar/services/agent_tools/catalog.py` (two schemas)
  - tests: `sidecar/tests/test_research_fast*.py` or the nearest research-snapshot test, `sidecar/tests/test_agent_tools*.py`
- **fix_shape (narrow, one shared seam):**
  1. `snapshot_structured` gains `listing_region: str | None`. When it is set, the whole fan-out (price, fundamentals and every witness) runs inside `tok = config.set_request_region(listing_region)` … `finally: config.reset_request_region(tok)`. Set it before the `asyncio.gather`: tasks and `to_thread` copy the context, so every leg sees it. All three callers pass `target.region`.
  2. `price_data` and `fundamentals` accept an optional `region` (`enum US/IN/GLOBAL`, described as "pass the region resolve_symbol returned when it differs from the session's"), scoped the same way. These are `read_handler` capabilities, so `TOOL_SCHEMAS`, the allow-list and the MCP surface follow from the catalog, and the parity tests stay green.
  3. Do not touch the figure guard, `_judge_clause`, `_NO_TOOL_CUE`, resolution_policy, or any frontend file. This is not DATA-002's fix and does not reopen it.
- **acceptance (fails at d38b5d1a, passes after):**
  - (a) Research-snapshot test. With session region IN and a recording `tool_call` (real `resolve_symbol`), `gather_fast('Halliburton')` makes its `price_data` and `fundamentals` calls with `config.get_region()=='US'` inside the stub (or `args['region']=='US'`). A control `gather_fast('Hindustan Aeronautics')` still runs them under IN.
  - (b) Tool test. `fundamentals {symbol:'HAL', region:'US'}` resolves the US listing under session IN, with the provider monkeypatched to record the region. The same call without `region` keeps today's behaviour.
  - (c) Fresh case of the class, not used by the finder: 'Ferrari' (RACE: Ferrari N.V. vs Race Eco Chain), plus 'Carnival' (CCL) or 'PTC Inc' (PTC: PTC Inc vs PTC India).
  - (d) Live certification on an own sidecar. `research {query:'Ferrari'}` under IN shows a USD price near the US quote (~388 USD at triage time) and Ferrari's fundamentals name, never Race Eco Chain.
- **note:** "Same class as R15-DATA-002 (blocked_tier4, frontend legs) and R15-DATA-003 (fixed, ownership lane only). Distinct seam: no DATA-002 attempt touched the research fetch path or the quote/fundamentals tools (commits listed in XADV_TRIAGE.md). Not a regression."

## Other admitted entries (fix shapes in brief)

- **R15-LEAD-128 (medium, research-search), keyless:4.**
  - Mechanism: `price_data.py:48-56` awaits `get_history` (6mo), then `get_quote`, one after the other. `fast.py:351-359` boxes the whole call at 6 s, and `_structured_value(price_res,'quote')` keeps only the quote.
  - Repro: `xadv-keyless-7.md`. KITEX.NS research reports "price timed out after 6s — dropped" while `/quotes/KITEX.NS` answers in milliseconds.
  - Fix: the research price leg calls the quote alone (or `price_data` runs quote and history concurrently and returns a quote-only partial on a history timeout).
  - Test: a stub history that sleeps longer than the box still yields `structured.price.ok`.
  - Files: `fast.py`, `price_data.py`.
  - The writer of LEAD-127 owns the same files, so batch them in one lane.
- **R15-LEAD-129 (medium, docs), keyless:3.**
  - The claims are at README.md:60-62 ("web research (keyless, via DuckDuckGo) all run out of the box") and :70-73 ("fully offline"). README.md:41-42 lists 7 providers without OpenRouter.
  - R15-UI-052 fixed the app copy only, and README was never in its files, so this is new, not a regression.
  - Fix: mirror the OnboardingFlow wording. Pin with a grep test in the existing docs check or a vitest copy check.
- **R15-LEAD-130 (medium, research-search), realuser:1.**
  - Probe at :52800 (IN): `autocomplete zomato` gives ETERNAL with former ZOMATO, so R15-DATA-018's pinned case holds. But `Zomato Ltd`, `indiabulls housing`, `cadila` and `513353` all give `[]`, while /resolve binds them.
  - This is a sibling of DATA-018 and UI-039 (both fixed). Their repros still pass, so it is not a regression.
  - Fix: `symbol_resolver.autocomplete` consults the same former-name index (`former_names.json`) and the BSE scrip-code index that `resolve()` uses.
  - Fresh case: `Zomato Ltd`.
  - File: `symbol_resolver.py`.
- **R15-LEAD-131 (medium, data-smallcaps), realuser:2.**
  - `identity_crosscheck.py` tokenizes `[a-z0-9]+` without `symbol_resolver._NAME_CANON_MAP` (`&`→`and`), so COCHINM scores 0.40. A false "may be a mis-resolution" note appears on /fundamentals and as a brief conflict.
  - Fix: apply the shared canon map (and strip the BSE `-$` artefact) in the cross-check tokenizer and in the displayed name.
  - Test: COCHINM gives no identity_note. A fresh `&` name gets the same result. A true mismatch still flags.
- **R15-LEAD-132 (low, data-smallcaps), keyless:1.** `fetch_latest` stamps the requested date, not the rows' `DATE1`. Fix: take the trade date from `DATE1` and skip dates in the holiday table. File: `nse_bhavcopy.py`.
- **R15-LEAD-133 (low, agent-chat), keyless:2.** `unreachable` covers both "never installed" and "not running". Fix: return a distinct reason (e.g. probe the default port and check whether the binary exists, or always include the install link). ChatSidebar opens setup on it. Sibling of AGENT-028 (fixed), not a regression.
- **R15-LEAD-134 (low, research-search), keyless:5.** `_WEB_ROUND_TIMEOUT_S = 8.0` (`fast.py:120,693`) is shorter than the chain's two 6 s engine deadlines (`keyless.py:263`). Fix: size the round to cover the chain, or shrink the per-engine deadline under FAST, and report "timed out" instead of "no web backend". Distinct from LEAD-065 (the web-only branch box).

## Attachments

- **realuser:4 → R15-LEAD-057 (open low).**
  - LEAD-057's root_cause: `symbol_resolver._strip_corporate_suffix` leaves SEC registry slash suffixes (`keycorp /new/`).
  - realuser:4 is the same artefact defeating the sibling `_canonical_name` (`symbol_resolver.py:918-930`; `_EDGE_PUNCT` has no `/`). So 'Danaher Corporation' can never canonicalize to `danaher corp /de/`.
  - Same file, same mechanism, so it is attached. The new consequence is that a large-cap cannot be resolved by its legal name (784/10,365 US rows affected), which exceeds low. I recommend the lead re-grade LEAD-057 to medium and widen its fix to one slash-suffix strip shared by both helpers.
  - Evidence: `xadv-realuser-7.md`.
- **realuser:6 → R15-LEAD-053 (open low).** Same direct-lookup-without-former-name fallback; new instances IBULHSGFIN.NS and ANGELBRKG.NS. Evidence: `xadv-realuser-6.md`.
- **keyless:A1 → R15-DOCS-003 (blocked_tier4).** README.md:27 is in its evidence/files. Evidence: `xadv-keyless-6.md`.
- **keyless:A2 → R15-RELEASE-002 (blocked_tier4).** README.md:88-90 is in its repro. Evidence: `xadv-keyless-6.md`.

## rc2 consequence

Under R6, every admitted critical or medium must be FIXED or ADJUDICATED before the tag.
- R15-LEAD-127 is critical, has a narrow root cause, has never been attempted, and is not Tier-4. It needs one bounded fix round, so **r15-rc2 waits for that round.**
- LEAD-128..131 are small and in disjoint files, except that 128 shares files with 127. They fit the same round:
  - lane A: 127 + 128 (`fast.py`, `iter.py`, `deep_research.py`, `price_data.py`, `fundamentals.py`, `catalog.py`)
  - lane B: 130 + 131 + the LEAD-057 widening (`symbol_resolver.py`, `identity_crosscheck.py`)
  - lane C: 129 (`README.md`)
- The lows (132-134) are counted backlog unless writers have room.

## Suggested cross-reference for DECISIONS 4.15 (no attach; for blast-radius visibility only)

> Sibling, not attached (XADV triage @ d38b5d1a): the same wrong-entity class reaches two sidecar surfaces that no DATA-002
> attempt touched. (1) Research binds the named US instrument but fetches price and fundamentals on the bare ticker under
> the session region ('Halliburton' → Hindustan Aeronautics' price, P/E and mcap on the brief). (2) The copilot's
> price_data and fundamentals tools carry no region. Both are filed as R15-LEAD-127 (critical) with a sidecar-only fix
> that needs no frontend change. Option (a) of this item (a region argument on add_to_watchlist) is the same pattern and
> could ride the same lane if you authorise it.
