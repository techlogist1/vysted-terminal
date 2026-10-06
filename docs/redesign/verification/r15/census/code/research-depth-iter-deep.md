# Code census — `research-depth-iter-deep`

**Subsystem:** Research Engine: Depth / Iteration / Deep (`CODE_PARTITION.json` → `research-depth-iter-deep`)
**Responsibility:** the two-tier depth ladder (FAST vs full/deep) and its iteration loop — target binding, self-verification pass, hosted-deep-research routing — behind the `research` / `deep_research` agent-tool entry points.
**Files read in full:** `sidecar/services/research/{depth,iter,deep,fast,target,verify}.py`, `sidecar/services/agent_tools/{deep_research,research}.py` (5,116 LOC).
**Method:** `aposd-critique` skill, loaded and followed. Sub-agents unavailable (this session IS a subagent) → **Assessment independence: degraded (sequential)**; Assessment A (Strategic Thinker, 18 principles) was completed and recorded before Assessment B (Tactical Tornado red-flag scan) ran. Snapshot persistence to `.aposd/critique/` **skipped deliberately** — this run is read-only on the repo outside its two output files.
**Model:** `claude-opus-5[1m]`.

---

## Tactical Tornado verdict

**Risk: LOW-MEDIUM — unusually low for 5k LOC of agent-loop code.** This is not tornado code. Every module opens with the defect it was written to kill, failure is soft-landed at four separate seams (`_safe_tool` / `_safe_llm` / `_safe_visit` / `_safe_native`), and `target.py` is a textbook root-cause fix rather than a symptom patch.

What the red-flag scan found instead is the *other* failure mode — **a strategic codebase whose second copies have started to drift**, plus one verification path whose honesty guarantees are asserted in prose rather than held by structure:

- one **provable parser bug** that flips `UNVERIFIED` to `AGREE` on the ULTRA cross-check (§P0),
- one **pass-through `budget` parameter** that makes ULTRA's 90 s verification reserve decorative (§P1),
- **three second copies** of numbers the code claims have no second copy, two of which have already drifted in opposite directions,
- **information leakage at scale**: `iter.py` imports **11 private names** from `deep.py`, `verify.py` imports **4 more** — the underscore prefix in `deep.py` is now a lie.

---

## Design principles score

| # | Principle | Verdict | Evidence | Consequence |
|---|-----------|---------|----------|-------------|
| 1 | Strategic over tactical | at-risk | `target.py:1-28` (root-cause fix, not a symptom patch), `depth.py:112-161` (one knob table) vs `deep.py:986-1295` (a whole second round loop kept "just in case") | The strategic investment is real, but the unreachable second loop is tactical residue that now diverges (row 14). |
| 2 | Deep modules | pass | `target.resolve_target` `target.py:238-280` — one call hides the policy verdict, the `SYMBOL_SHAPE` gate, the 4→3→2→1 prefix ladder and curated-disambiguation precedence | Callers ask one question and get one answer; the R8 symbol-truth defects cannot recur through this door. |
| 3 | Information hiding | violate | `iter.py:40-67` imports `_ROUND_MODEL, _WEB_ONLY_FLOOR_NOTE, _emit, _Findings, _record_structured, _record_web, _reflect_says_complete, _round_wall_limit, _run_researcher, _safe_llm, _split_subquestions, _synthesize_brief` from `deep.py`; `verify.py:56-64` imports 4 more | No edit inside `deep.py` is local. The `_` prefix tells the next maintainer these are private when 15 call sites in two modules depend on them. |
| 4 | Information leakage | violate | `deep_research.py:74` `_MIN_HEAVY_ANGLES = 2` vs `iter.py:89` `_MIN_ANGLES = 2` ("Kept in lockstep with…"); `deep_research.py:463-467` + `:478-483` hold a SECOND per-depth table each, against `depth.py:29-30` "no second copy of these numbers exists anywhere" | Three places know the same fact; one comment asks a human to keep them equal. Row 10 shows this has already failed. |
| 5 | General-purpose is deeper | at-risk | `deep.py:705-717` keyword→tool ladder picks `sec_filings_list` for any "filing/sec/insider" sub-question, region-blind — while `fast.py:428` routes the identical decision by `is_india_target` | A special-purpose dispatcher that the sibling path already generalised; Indian names burn a guaranteed-failing SEC leg (F11). |
| 6 | Different layer, different abstraction | pass | `research.py:136-218` (tool boundary: depth floor, run id, execution record) → `deep_research.py:189-296` (engine/backend selection) → `iter.py:278-682` (loop) → `target.py` (binding) | Each layer speaks its own vocabulary; `_stamp_execution` (`research.py:99-133`) is a genuine boundary translation, not a pass-through. |
| 7 | Pull complexity downward | at-risk | `fast.py:377-385` gathers 7 cross-check coroutines with no `return_exceptions`; the "never raises" promise (`fast.py:273-274`) is held by 7 *other* modules each having its own `except` (`dividend_history.py:147`, `market_cap_witness.py:151`, `range_check.py:208`, …) | The obligation is pushed outward to every future contributor instead of held at the one gather that owns it (F6). |
| 8 | Better together or apart | violate | `verify.py:56-64` needs `_emit/_safe_llm/_safe_tool/_split_subquestions` from a module whose *public* function (`run_deep_research`) it never calls | The split is in the wrong place: the helpers want to be together in a shared loop module, the two loops want to be one. |
| 9 | Define errors out of existence | pass | `deep.py:146-176` `_safe_tool`/`_safe_llm` (incl. a 60 s per-call `wait_for`), `deep.py:639-646` `_safe_visit`, `verify.py:233-242` `_safe_native`, `target.py:216-226` "never raises" | The loops genuinely have no error case for a dead tool/LLM/page — the single best design decision in the subsystem. |
| 10 | Design it twice | at-risk | `verify.py:199-207` mandates "a single line starting with exactly one verdict word", then `verify.py:102-116` parses by substring-scanning the whole line | The obvious second design (read the first token) was never considered; it is also the fix for the P0 bug. |
| 11 | Comments describe the non-obvious | at-risk | Outstanding overall (`depth.py:134-140`, `deep.py:76-79`, `iter.py:428-438` all explain *why* with live-run evidence) — but `verify.py:37-41` ("metered by the SAME BudgetGuard as the run"), `depth.py:29-30` ("no second copy") and `fast.py:273-274` ("never raises") assert invariants the structure does not hold | A comment that states a false invariant is worse than none: it stops the next reader from checking (F2, F6, F9). |
| 12 | Comments first | pass | Every module leads with the defect it exists to fix — `target.py:1-28`, `deep.py:1-30`, `iter.py:1-28`, `verify.py:1-45` | A new maintainer can reconstruct the design intent without archaeology. |
| 13 | Choosing names | pass | `coverage_floor_met`, `structured_feeds_available`, `web_only_floor_note`, `NO_INSTRUMENT_NOTE`, `wants_disclosures_floor` | Names carry the contract. (Minor: `_Findings.findings` `deep.py:344` — the field and its container share a name.) |
| 14 | Modifying existing code | at-risk | R13 adaptive slice applied at `iter.py:611,628` but NOT at `deep.py:1241,1255` (`_round_wall_limit(budget)`, no `observed_latency`); region routing applied at `fast.py:413-442` but not at `deep.py:708-710` | Both fixes landed in one of two copies. The comment at `deep.py:90-95` now documents behaviour that module does not have. |
| 15 | Consistency | violate | `deep_research.py:281-283` wraps the DEEP call in `try/except`; the ULTRA branch `:259-280` has none. `iter.py:357-363` records exchange-filing rows as citations; the heavy panel `iter.py:918-929` never does | Same operation, two behaviours, chosen by depth — the strictest tier gets the weaker treatment in both cases (F4, F5). |
| 16 | Code should be obvious | at-risk | `verify.py:365` unions native citation domains into `domains`, then `:373` adds `+1` for the same channel; `iter.py:350` `structured.get("disclosures") is None` silently gates a second, unrelated action (`_record_web`) | Both read correct and are not. A reviewer has to hold two lines apart in their head to see the double count (F3). |
| 17 | Design for the future | pass | `deep.py:51-61` injected `ToolCall`/`LLMCall`/`OnStep`/`VisitCall` seams; `DepthProfile` (`depth.py:84-110`) is additive — a new knob is one field plus three table rows | Loops carry zero import-time coupling to a provider and stay unit-testable with fakes. |
| 18 | Performance as design | at-risk | Parallel where it counts (`iter.py:490-504`, `iter.py:820`, `verify.py:342-354`) — but the 5 verdict LLM calls run **sequentially** at `verify.py:357-394`, each capped at 60 s, inside a 90 s reserve | The one place a serial fan-out breaks the stated budget is the verification round (F2). |

**Summary: 6 pass, 8 at risk, 4 violate (6/18 pass).**

First run for this target — no trend. (Snapshot persistence skipped by run policy; see header.)

---

## Overall impression

This subsystem is **built, not typed**. The honesty engineering is the best thing in it: `finalize_markdown`, `web_only_floor_note`, `_LEG_REASONS`, `NO_INSTRUMENT_NOTE`, the `structured_line` framing at `deep.py:804-812` that stops a model converting a feed outage into "the company has no fundamentals" — these are designed, not defaulted.

The single biggest opportunity is not a refactor. It is that **`verify.py` — the module whose entire job is telling the user which numbers were confirmed — is the one module whose guarantees live in prose instead of in code**: a substring parser that can print AGREE over an UNVERIFIED verdict, an independence count that reaches 2 on one domain, and a `budget` parameter that is read once and then ignored. ULTRA's cross-check is the product's proof-of-work; today it can over-claim.

Second-biggest: `deep.py` is doing three jobs (shared helpers, an unreachable fallback loop, the legacy entry point) and the seam between them has already leaked into two other modules.

## What's working

1. **`target.py` is the model for how to fix a class of defect.** Instead of hardening each layer's re-resolution, it removes re-resolution: one call, one frozen binding, a regex shape gate (`target.py:44`) that makes "Saksoft Limited — focus: Analyze revenue growth…" *structurally* unable to become a symbol again, and `bound=True` threading (`iter.py:984-985`) so heavy explorers physically cannot re-resolve their focus-augmented task text. Unknown unknowns removed, not policed.
2. **Failure is defined out of the loop's existence.** `_safe_tool`/`_safe_llm`/`_safe_visit`/`_safe_native` plus the abort→synthesize invariant mean the loops have no error path at all: a dead LLM, a dark web backend and a breached budget all end in a brief. `_safe_llm`'s `asyncio.wait_for` (`deep.py:173`) closes the one hole the adapters left open.
3. **`DepthProfile` is a genuinely deep interface.** `profile_for(value)` (`depth.py:164-166`) turns any legacy spelling into a 10-field knob set; callers thread fields and never branch on depth. That the drift (row 4) happened *outside* this table is evidence the table itself works.

---

## Priority issues

### [P0] The cross-check verdict parser reports UNVERIFIED claims as AGREE

- **Principle:** 10 (design it twice) / 16 (obviousness)
- **Complexity symptom:** unknown unknowns — nothing in the section output reveals the mislabel
- **Evidence:** `verify.py:102-116` scans the whole first line for markers; `_AGREE_MARKERS` contains `confirm`, `support`, `consistent`, `match`. The system prompt (`verify.py:199-207`) asks for `"<VERDICT> — <reason naming the source domains>"`, so the reason routinely contains those words.

  Proven against the shipped function:

  ```
  'UNVERIFIED — no source confirms the 23% operating margin.'      -> ('agree', ...)
  'UNVERIFIED - the evidence does not support the figure'          -> ('agree', ...)
  'UNVERIFIED — could not match the figure to any source'          -> ('agree', ...)
  ```

- **Why it matters:** `_render_section` prints `- **AGREE** — <the numeric claim> (<domains>)` (`verify.py:268`), and `verify.py:273` suppresses `detail` when the verdict is AGREE — so the literal words "no source confirms" are *dropped from the output*. A price/margin/valuation figure the verifier explicitly could not verify is published to the user as cross-checked. `disagreements` (`verify.py:396`) and `brief.note` are unaffected, so nothing else flags it. `tests/test_research_verify.py:191-197` covers `"cannot tell from the evidence"` but no UNVERIFIED reply containing an agree-word, so CI is green.
- **Fix:** parse the first WORD, not the line: `head = first_line.split()[0].strip('*:—-').lower()`; `UNVERIFIED`/`DISAGREE`/`AGREE` exact-match first, fall back to the existing marker scan only when the head is not a verdict token. Add the three strings above to `test_parse_verdict_is_conservative`.

### [P1] The ULTRA cross-check's budget is a pass-through parameter; its 90 s reserve is decorative

- **Principle:** 11 (comments that state false invariants) / 18 (performance as design)
- **Complexity symptom:** change amplification — the wall-budget invariant every other loop enforces is silently absent here
- **Evidence:** `verify.py:304` checks `budget.breach()` once at entry, `verify.py:319` records once; after that the round runs 1 extract call + N parallel searches + N native calls + **N sequential verdict LLM calls** (`verify.py:357-394`) with no further `breach()` check and no `asyncio.timeout`. `_safe_llm` caps each call at 60 s (`deep.py:165`), so 5 claims can legitimately take ≈ 60 + 5×60 ≈ 360 s against the `BudgetGuard(max_steps=6, max_wall_seconds=90)` handed in at `deep_research.py:272` and the `_CROSS_CHECK_RESERVE_SECS = 90` carved out at `deep_research.py:78,231-236`.
- **Why it matters:** the whole R13/R8 wall-guard apparatus (`_PER_ROUND_WALL_SECS`, `MIN_ROUND_WALL_SECS`, the per-round `asyncio.timeout`, the adaptive slice) exists to kill the "8-minutes-unfinished" bug — and the last stage of the most expensive depth opts out of all of it. A 360 s ULTRA can run ~270 s of panel plus ~400 s of verification. Worse, `verify.py:37-41` tells the reader the round "is metered by the SAME `BudgetGuard` as the run"; it is neither the same guard (a fresh one is constructed at `deep_research.py:272`) nor metered.
- **Fix:** wrap the claim loop in `async with asyncio.timeout(budget.max_wall_seconds)` and re-check `budget.breach()` before each `_verdict_for`, degrading the remaining claims to UNVERIFIED with the honest reason already used at `verify.py:375-378`. Then correct the docstring.

### [P1] ULTRA's independence floor double-counts the native channel

- **Principle:** 16 (obviousness)
- **Complexity symptom:** cognitive load → a false guarantee printed to the user
- **Evidence:** `verify.py:365` `domains = _row_domains(rows) | _row_domains(native_rows)` already folds the native lane's citation domains in; `verify.py:373` then adds `+ (1 if native_text else 0)` for the same lane. A claim whose *only* evidence is one domain reached by both lanes scores `independence == 2`, clears `min_domains=2` (`deep_research.py:274`), gets a real LLM verdict, and — because `channels == ["searxng","native"]` — can render **"AGREE (corroborated across channels)"** (`verify.py:265-266`, `:391-393`) under a heading that promises "at least 2 independent sources required per claim" (`verify.py:250-255`).
- **Why it matters:** independence, not volume, is the stated point of ULTRA (`depth.py:102-104`). One domain wearing a corroboration badge is exactly the failure this round was built to prevent.
- **Fix:** count the native lane only when it contributed no domain of its own — `independence = len(domains) + (1 if native_text and not native_rows else 0)` — and gate `corroborated` on the two channels resting on *different* domains.

### [P2] ULTRA silently loses the R13 exchange-filings citations that DEEP gets

- **Principle:** 15 (consistency)
- **Complexity symptom:** change amplification — one `is None` guard controls two unrelated actions
- **Evidence:** `iter.py:350` gates **both** the floor pull **and** the `_record_web` of `floor["rows"]` (`iter.py:357-363`) on `structured.get("disclosures") is None`. The heavy panel pre-seeds `snapshot["disclosures"]` at `iter.py:923-929`, so every explorer's condition is False and the whole block is skipped; `run_heavy_research` never records the rows itself (the only other `gather_floor` call site, `iter.py:924`, only stores them).
- **Why it matters:** for a thin-web Indian name — the exact case the R13 floor exists for (`disclosures.py:127-137`) — DEEP publishes dated exchange announcements as `[n]` sources and ULTRA does not. Those rows also feed `findings.coverage["web"]` and `distinct_web_domains`, so their absence makes ULTRA's stricter `min_web_domains=2` floor *harder* to meet at the depth that demands it.
- **Fix:** split the guard — pull only when absent, record always: keep `if … is None: floor = await gather_floor(...)` but move the `_record_web` call outside it, reading `structured["disclosures"]["rows"]`.

### [P2] The ULTRA branch has no exception guard while its DEEP sibling does

- **Principle:** 15 (consistency) / 9 (define errors out of existence)
- **Complexity symptom:** unknown unknowns
- **Evidence:** `deep_research.py:281-296` wraps `run_iter_research` in `try/except Exception` and degrades to the single-pass fallback with an honest note; the heavy branch at `:259-280` calls `run_heavy_research` bare. Reachable raise: `snapshot_structured` at `iter.py:915` sits outside any `try`, and its "never raises" contract is held only by 7 independent helper `except` blocks (`fast.py:377-385`).
- **Why it matters:** the same failure degrades gracefully at DEEP and surfaces as a raw tool error at ULTRA — the tier the user paid the most wall-clock for.
- **Fix:** one line — give the heavy branch the same `try/except`. Structurally better and also one line: `return_exceptions=True` on the `fast.py:377` gather with a `None` coercion, so the contract is held where it is made.

---

## Minor observations

- `fast.py:377-385` — the 7-way cross-check gather has no `return_exceptions`; an 8th cross-check added without its own `except` silently takes down every research path (F6).
- `deep.py:986-1295` — `run_deep_research` (~310 LOC) is reachable only from the `except` at `deep_research.py:283` guarding a loop documented as never raising; it is a second copy of the round loop that has already drifted (`deep.py:1241,1255` vs `iter.py:611,628`).
- `deep_research.py:404-405` documents deep/ultra walls as "120 / 240"; `depth.py:141,157` are 180 / 360. The clamp at `deep_research.py:426` (`[30,300]`) cannot even express ULTRA's own default — `None` keeps 360 (`_clamp` returns `default` before clamping, `:98-102`) while passing 360 explicitly cuts it to 300.
- `deep.py:708-710` — an Indian target with a "filing"-shaped sub-question still calls `sec_filings_list`; the leg always fails and `deep.py:806-812` then tells the model the miss is "a feed outage, NOT evidence the data does not exist" about a jurisdiction that never indexed the company.
- `iter.py:1001-1002` — a raised explorer is dropped with no step, no note and no count; `structured["panel"]` (`:1134-1136`) lists survivors only, so a 3-angle ULTRA badge can sit over a 2-angle brief.
- `deep.py:308-323` — `_reflect_says_complete` has the same whole-text scan weakness as the verdict parser: "price is not covered" contains `covered`, no gap marker → True. Only the coverage floor stops it.
- `iter.py:112-114` — `_Report.render()` tail-truncates, so an over-cap report loses `## Facts established` (the cited-fact section the distill prompt demands at `:173-180`) while keeping `## Planned next`.
- `research.py:186,200` — `api_key` is read straight from the model's tool args on both the tier-B and deep paths, while the adjacent comment (`:183-185`) explains why `model` deliberately is not.

---

## Persona walkthrough

**Tactical Tornado.** A tornado would not have written `target.py` — they would have added a fifth `if isinstance(symbol, str) and len(symbol) < 20` guard at each call site. Where this codebase *does* show tornado pressure is the release-cadence seams: `deep_research.py:74` `_MIN_HEAVY_ANGLES = 2` with the comment "Kept in lockstep with `iter._MIN_ANGLES`" is the tornado's signature move — copy the constant, promise to remember. Likewise `_RESEARCH_MODEL_WALL_SECONDS` (`:463-467`) and `_RESEARCH_MODEL_COST_BANDS` (`:478-483`): a second and third per-depth table added beside a module that says in its docstring that no second copy exists. Left alone, tier B's walls and tier A's walls will state different truths about "ultra" within two releases — exactly as `deep.py:1241` and `iter.py:611` already state different truths about the round slice.

**Strategic Thinker.** The redesign is three moves, none large. (1) Split `deep.py`: `research/_loop.py` owns the shared round helpers (`_Findings`, `_run_researcher`, `_safe_*`, `_split_subquestions`, `_round_wall_limit`) as *public* names, `iter.py` owns the one loop, and `run_deep_research` is deleted — its fallback role is already covered by iter's abort→synthesize, which is why the `except` at `deep_research.py:283` has never fired. That removes the 11-name private import, the second loop, and both drift sites at once. (2) Give `DepthProfile` the three fields currently living outside it (`tier_b_wall_seconds`, `cost_band`, and the `angles >= 2` panel threshold as a `profile.is_panel` property), restoring the "no second copy" claim to truth. (3) Make `verify.py` hold its own guarantees: first-token verdict parsing, independence counted once per source, and the claim loop inside `asyncio.timeout(budget.max_wall_seconds)` with a `breach()` check per claim. After (3), `verify.py`'s docstring becomes accurate without editing a word of it.

---

## Questions to consider

- `run_deep_research` exists to catch an exception from a loop documented as never raising, and `deep_research.py:283`'s `except` has no recorded firing. What is the evidence that keeping it is cheaper than the drift it is now causing?
- If `verify.cross_check` took `remaining_wall: float` instead of a `BudgetGuard` it only reads twice, would the missing timeout have been obvious at the call site?
- The coverage floor, the independence floor and the cross-check's `min_domains` are three expressions of "how many independent sources count as enough". Should they be one function on `DepthProfile` rather than three call-site arguments?
