# R15 Stage C batch 13: plan (RC1 round 2, last C/H/M batch)

- **Base:** `004-r4-experience-rebuild` @ `ba951d233d07f0502fdaf1a24cc330c665195561`.
- **Queue:** 4 open C/H/M entries in the register: AGENT-090 (high), RESEARCH-007 (high), CODE-AGENT-033 (medium), DOCS-017 (medium). All four are selected. Lows are not planned.
- **Sets:** the lead note says "four sets" but assigns the four entries to three writers (AGENT-090 and CODE-AGENT-033 share `agent_runtime.py`). The plan follows the file ownership: **3 writers**, no file shared.
- **Routing:**
  - W1 is Opus. Its fix sits in the agent runtime's streaming state machine: it rewrites prose deltas mid-stream and adds a new event kind on the wire. That is agent-chat and §6.5-adjacent.
  - W2 and W3 are Sonnet. Each has a written acceptance test.

| id | sev | disposition | writer |
|---|---|---|---|
| R15-AGENT-090 | high | fix (deterministic guard) | W1 |
| R15-CODE-AGENT-033 | medium | fix | W1 |
| R15-RESEARCH-007 | high | fix (PSL class fix) | W2 |
| R15-DOCS-017 | medium | fix | W3 |

---

## W1 (opus): runtime ratio guard + tool_result event

**Owned files:**
- `sidecar/services/agent_runtime.py`
- `sidecar/models/llm.py`
- `sidecar/services/llm/base.py` (the `LLMStreamEvent` union)
- `types/ai.ts`
- `src/modules/chat/streaming.ts`
- `src/modules/chat/streaming.test.ts`
- `scripts/agent_eval/grader.py`
- `sidecar/tests/test_agent_runtime.py`
- `sidecar/tests/test_agent_eval.py`

### R15-AGENT-090: fabricated ADR ratio

**Mechanism.** I confirmed this against the batch-12 verifier note, not the raw claim.
- No tool result carries an ADR/ADS ratio. `grep -rniw adr` over `sidecar/services` finds no ratio field.
- Batch 12 shipped only a preamble rule (`agent_runtime.py:175-184`, which carries the `ponytail:` ceiling note). llama3.1:8b still states a ratio in 3 of 5 runs:
  - "10 ordinary shares"
  - "1 ordinary share"
  - "approximately 144869230 ordinary shares", reasoned from the fundamentals `shares_outstanding` field
- Prose reaches the SSE consumer as raw `LLMDeltaEvent`s relayed in `_consume_round` (`agent_runtime.py:~1989-2085`). Nothing checks a delta against what the tools returned.

**Fix: a deterministic guard in the runtime, the one place every lane goes through.** This covers the chat SSE, Delegate runs via `run_manager` and the MCP invoke path.

1. **Collect tool results.** `_TurnState` collects every tool `result_str` of the run (`tool_results: list[str]`). Append it in `_dispatch_round` next to the existing `on_tool_result` call.
2. **Buffer prose by sentence in `_consume_round`.**
   - Hold `LLMDeltaEvent` text in a per-round buffer. Release it at each sentence boundary (`.`, `!`, `?` followed by whitespace, or a newline).
   - Flush the remainder before yielding any non-delta event (tool_use, error, done/finish) and when the stream closes unterminated.
   - Streaming stays live at sentence granularity.
   - Set `rnd.streamed_text` / `turn.turn_text` on the text actually yielded.
3. **Check each released sentence for a depositary/conversion-ratio claim.** A sentence is a claim when it names `ADRs?|ADSs?|American Depositary|depositary|conversion ratio` (word-bounded, case-insensitive) AND carries a number that is either:
   - a numeral or number-word (one through twelve) adjacent to `(ordinary|equity|underlying|common) shares?`, or
   - an `N:M` / `N-for-M` / `N to M` ratio.
4. **Test whether the claim is traceable.** It is traceable when some collected tool result both names a depositary term (`ADR|ADS|American Depositary|depositary|Repr`, word-bounded) and contains every claimed number. Normalise number-words to digits on both sides.
   - Example: the web_search hit "Sify Technologies Ltd ADS (Each Repr 6 Ords)" traces a claim of "6 ordinary shares".
   - The fundamentals result carries `144869230` but no depositary term, so run 4's claim is replaced.
5. **Replace an untraceable claim sentence** with one fixed statement, for example: "The ADR-to-ordinary-share ratio is not available from this session's sources." Keep the sentence's trailing whitespace.
6. **Update the preamble rule.** Keep the batch-12 rule, and replace the `ponytail:` "no deterministic guard" comment with a pointer to the guard.
7. **Scope limits.** No other claim types. Thinking events are untouched.

**Test (scripted provider, `test_agent_runtime.py`).**
- **Fabricated claim is replaced.** A provider emits a `fundamentals` tool_use. A stub tool returns a dict without an ADR field, including `shares_outstanding: 144869230`. The provider's final round streams "One SIFY ADR represents 1 ordinary share, per fundamentals data. Revenue was ₹4,651 cr." across several deltas, with the claim split mid-number.
  - Assert the joined answer contains the fixed unavailable statement.
  - Assert it matches neither `represents 1 ordinary share` nor `fundamentals data`.
  - Assert the revenue sentence passes through unchanged.
- **Class case the fix was not written against: shares-outstanding reasoning.** The same setup with the claim "each ADS equals approximately 144869230 ordinary shares" is also replaced.
- **Traceable claim passes.** A stub `web_search` result "Sify Technologies Ltd ADS (Each Repr 6 Ords)" followed by "Each ADS represents six ordinary shares." is **kept**.

**Live repro (writer's note).** Run the original repro prompt 5 times on llama3.1:8b / ollama with autonomy ask. Use `scripts/r15/vy.py invoke` against an isolated R15 sidecar started detached.
- Record each run's final text in the writer note.
- **Bar: 0/5 answers state an untraced ratio.** Unavailable-statement runs and correctly sourced "6" runs both count as pass.
- If ollama is unreachable, record could-not with the error. Do not claim the bar.

**Folded note (batch-12 VERDICTS item 3, INR revenue).** llama answered "TTM revenue in USD" in ₹ without converting. That output is currency-labelled, not fabricated, and outside a ratio guard. W1 does not change it. The planner flags it for verifier concurrence (see notes). W1 must confirm in its note that the fundamentals result carries the reporting currency (`agent_tools/fundamentals.py:242`).

### R15-CODE-AGENT-033: grader blind to tool errors

**Mechanism.**
- `models/llm.py` stream kinds are delta, tool_use, research_step, agent_plan, thinking, heartbeat, done and error. There is no tool-result kind.
- `_dispatch_round` appends the result only to the model's messages. `vy.py` writes every SSE frame raw to `--out` (`vy.py:~190`), so it needs no change once the runtime emits the event.
- `grader.grade` sees only `tool_use` inputs. A trial whose call errored (option_chain `nearest` returned 422) with an empty expectation set therefore passes.

**Fix.**
1. **New event model in `models/llm.py`.** Add `LLMToolResultEvent(kind="tool_result", tool_call_id, name, ok: bool, error: str | None)` and add it to the `LLMStreamEvent` union in `services/llm/base.py`.
2. **Emit it from `_dispatch_round`** right after `result_str` is known, for every dispatched call, including the web-search-cap synthetic result and invalid-args results.
   - `ok` is False when the parsed result is a dict with `ok is False` or a truthy top-level `error`.
   - `error` is the `error` (else `message`) string, truncated to about 200 chars. It carries no payload data.
3. **Mirror in `types/ai.ts`.** Add the variant to the `LLMStreamEvent` union and map it in `streaming.ts` `normalizeEvent` (snake to camel).
   - Tier-3 decision: the SSE union's TS mirror is `types/ai.ts`. `types/data.ts` carries no stream events, so the lead note's "types/data.ts" means this file.
   - ChatSidebar needs no branch: its if/else chain ignores the kind, and `produced` was already set by the preceding tool_use.
4. **Grader.** Fail a trial when, for any tool name, the **last** `tool_result` of that name has `ok: false`, reported as `"<name> errored: <error>"`. A model that recovers with a later successful call of the same tool passes.
   - Skip `__autobrief` ids.
   - Streams recorded before this change have no tool_result frames and grade as before.

**Tests.**
- `test_agent_runtime.py`: a scripted tool_use whose stub tool returns `{"ok": false, "error": "422 ..."}` yields a `tool_result` event with `ok False` after its tool_use, keyed on the same `tool_call_id`. A successful tool yields `ok True`.
- `test_agent_eval.py`:
  - a trial whose only matched call has a later `tool_result ok:false` fails with "errored";
  - an errored call followed by a successful retry of the same tool passes;
  - a stream without tool_result frames still passes (backward compatible).
- `streaming.test.ts`:
  - an SSE body carrying an unknown kind (`{"kind":"future_kind"}`) between a delta and done is ignored: no onEvent for it, no throw, the delta and done still delivered;
  - a `tool_result` frame normalises to the camelCase shape.

**Coordination.** Commit the models/llm.py, base.py, types/ai.ts and streaming.ts changes in ONE commit (the mirror rule).
**Gates.** `ruff format` + `ruff check` on changed Python; the focused pytest files, run in the background; `pnpm vitest run src/modules/chat/streaming.test.ts`; `pnpm typecheck`.

---

## W2 (sonnet): RESEARCH-007, a Public Suffix List registrable-domain check

**Owned files:**
- `sidecar/services/research/finance.py`
- new `sidecar/services/research/psl/public_suffix_list.dat`
- `scripts/sidecar-specs.mjs` (`MAIN_ADD_DATA`)
- `scripts/sidecar-specs.test.mjs`
- `sidecar/tests/test_research_finance.py`

**Mechanism** (`finance.py:146-158`, confirmed).
- `_looks_like_ir` treats `ir.`/`investor(s).` as a subdomain whenever the host has 3 or more labels. It also keeps a 16-entry platform denylist.
- So PSL private suffixes that are not on the denylist, like `ir.firebaseapp.com` and `ir.herokuapp.com`, still rank TIER_PRIMARY.
- ccSLD registrable domains (`investors.co.uk`, `ir.co.in`, `investors.com.au`) pass the label count and rank TIER_PRIMARY too.
- No PSL package is installed: `tldextract`/`publicsuffix2` are absent from `sidecar/.venv`. I checked.

**Fix.**
1. **Vendor the full upstream PSL** once, at writer time: `curl -fsSL https://publicsuffix.org/list/public_suffix_list.dat`.
   - Save it to `services/research/psl/`, keeping its own MPL-2.0 header.
   - Add a first-line comment with the fetch date and source URL.
   - Never fetch at import or runtime.
   - I chose the full list, not a hand-picked subset, because a subset recreates the enumerate-the-platforms class the verifier rejected. About 250 KB is noise against the 120 MB budget.
2. **Parse it once** (`functools.cache`), covering both ICANN and PRIVATE sections: normal, `*.` wildcard and `!` exception rules. Add `_registrable_domain(host)` using the standard algorithm: longest matching rule, exceptions win, default rule `*`.
3. **`_looks_like_ir(host)`** is True only when:
   - the first label is `ir`/`investor`/`investors`;
   - `host` has more labels than `_registrable_domain(host)`, so the IR label is a true subdomain; and
   - the host is not denylisted.
4. **Shrink the denylist** to the platforms that are NOT PSL suffixes, for example medium.com, substack.com, seekingalpha.com, reddit.com, linkedin.com and hubpages.com. Check each current entry against the vendored list and delete the ones the PSL now covers. Delete the blogspot special case if the PSL lists `blogspot.*`.
5. **Verifier cases.** If any verifier fresh case is not a PSL suffix, keep it on the denylist and say so in the note.

**PyInstaller data audit** (CLAUDE.md gotcha (c)).
- The file is loaded via `Path(__file__).parent`, so add `[join(SIDECAR_DIR,"services","research","psl"), "services/research/psl"]` to `MAIN_ADD_DATA`.
- Update the expected flags in `sidecar-specs.test.mjs`.
- Build the main sidecar detached (`pnpm sidecars:build`, then poll). Confirm the file is inside the binary with `sidecar/.venv/bin/pyi-archive_viewer -l <binary> | grep public_suffix` or an equivalent listing. Record the output.

**Acceptance test** (`test_research_finance.py`, one parametrised test plus controls):
- `domain_tier(u) != TIER_PRIMARY` for:
  - `https://ir.firebaseapp.com/x`, `https://investors.web.app/x`, `https://ir.azurewebsites.net/x`
  - `https://ir.onrender.com/x`, `https://ir.fly.dev/x`, `https://ir.glitch.me/x`
  - `https://investors.notion.site/x`, `https://ir.webflow.io/x`, `https://ir.herokuapp.com/x`
  - `https://www.investors.co.uk/news/x`, `https://ir.co.in/x`, `https://investors.com.au/x`
- Controls that must stay TIER_PRIMARY: `https://investors.apple.com/`, `https://ir.tesla.com/`, plus the existing `ir.nvidia.com`, `investors.infosys.com`, `investor.apple.com` and `ir.tatamotors.com`.
- Class pin on hosts the fix was not written against: `https://ir.pythonanywhere.com/x` (PSL private) and `https://investors.org.uk/x` (ccSLD) must not be primary, and `https://investors.bhp.com.au/x` must be primary. The last one proves the ccSLD handling promotes a real company IR host.
- The existing batch-3 and batch-12 tests stay green, unedited.

**Gates.** `ruff format` + `ruff check` on the changed files; `pytest sidecar/tests/test_research_finance.py`; `node --test scripts/sidecar-specs.test.mjs` (or the repo's runner for it); `pnpm format:check`.

---

## W3 (sonnet): DOCS-017, India universe counts

**Owned files:**
- `docs/CURRENT_STATE.md` (section 3.3 screener bullet only)
- `sidecar/services/screener_universe_india.py` (module docstring only)
- `sidecar/models/screener.py` (the `:34` comment only)
- `sidecar/tests/test_current_state_doc.py`

**Mechanism** (confirmed live at base). `CURRENT_STATE.md:370-371` says nse-all is "EQ+ETF, ~2,675". The code disagrees:
- `load_india_universe('nse-all')` returns **3,506** (EQ 2,584 + ETF 351 + SM 571; SM is the NSE Emerge rows from R15-DATA-017).
- `bse-all` is **5,042** and `india-all` is **5,891**. The doc gives no count for either.
- The source of the stale count is the module docstring `screener_universe_india.py:6` ("EQ + ETF … ~2,675").
- The same class sits at `models/screener.py:34` ("~2.7k … / 4.9k"). It is taken here so the class is not split.

**Fix.**
1. Rewrite the nse-all/bse-all/india-all clause of the section 3.3 bullet with the loader's exact counts, as of the candidate:
   - nse-all with its EQ/ETF/SM breakdown (SM = NSE Emerge);
   - bse-all's count;
   - india-all's count.
   Use a fixed parseable form, e.g. ``` `nse-all` (3,506 symbols: EQ 2,584 + ETF 351 + SM 571, as `SYMBOL.NS`) ```.
2. In the docstring and the models comment, **drop the numbers** and name the row types (EQ + ETF + SM/NSE Emerge). Code comments do not carry counts that rot; the doc's counts are pinned by the test below.
3. Re-derive the numbers at write time from the loader. Do not copy them from this plan.

**Test** (`test_current_state_doc.py`, one new test, no network: the loader reads the bundled `services/resolver_masters` JSON):
- Parse section 3.3 for the nse-all total, its EQ/ETF/SM figures, and the bse-all and india-all totals. Strip thousands commas.
- Assert each equals `len(load_india_universe(id).symbols)` and the per-type counts of the NSE rows.
- bse-all and india-all are the cases the stale docstring never stated.
- Also assert the section no longer contains `2,675`.

**Gates.** `ruff format` + `ruff check`; `pytest sidecar/tests/test_current_state_doc.py`; `pnpm format:check` (Prettier covers docs/*.md).

---

## Coordination and run order (integrator)

1. **Merge order: W3, W2, W1.**
   - The sets are disjoint and none depends on another.
   - W1 is last because it is the largest diff, and its frontend and mirror changes need the full vitest + typecheck.
2. **Mirror rule:** W1's `models/llm.py` + `services/llm/base.py` + `types/ai.ts` + `streaming.ts` must arrive in one commit. Check with `git show --stat`.
3. **Build-recipe change:** W2 edits `scripts/sidecar-specs.mjs`, and editing a recipe invalidates every binary. After merging, run `pnpm sidecars:build` detached, then `node scripts/smoke-test-sidecars.mjs`, both before the verifier.
4. **After all three merges:** run `pnpm ci-local` detached and poll it.
5. **Verifier (one fresh-context pass).** For each entry, certify the claim, not only the repro:
   - **AGENT-090:** re-run 5 live llama3.1:8b trials itself. It must also concur or not on the INR-half disposition (notes).
   - **CODE-AGENT-033:** re-grade a recorded option_chain `nearest` stream with a synthetic `tool_result ok:false` appended. It must now fail.
   - **RESEARCH-007:** fresh hosts beyond the acceptance list, e.g. `ir.repl.co` and `investors.co.nz`.
   - **DOCS-017:** re-derive the counts from the loader.

## Deferred

None.

## Proposed not-a-defect

None.
