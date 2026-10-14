# rc1-verifier:2 (tie R15-AGENT-090) — ratio guard releases a whitespace-terminated fragment mid-sentence

Auditor: refutation audit round 4, group agent-inproc. HEAD 1a8ff356 (docs-only after 33586c21; code tree =
01015033). `git diff 1006c6da 01015033 -- sidecar/services/agent_runtime.py` changes only the research auto-brief block in
_dispatch_round (rc1-scenarios:1), so the ratio guard, _seg_at and _release_point are byte-identical to the candidate the
verifier ran. Own sidecar :52410 (pgid 77341, scratch data dir), llama3.1:8b under /tmp/vysted-r15-ollama.lock.

## Verdict: partial on R15-AGENT-090 (severity high, raised from the verifier's medium)

## 1. Tied entry
R15-AGENT-090, defect_class hallucinated-field-no-plausibility-check: the model states an ADR ratio no tool result carries.
fix_shape: surface a real adr_ratio where known, or refuse/hedge on facts not in tool output. The closure (batch 16, d64640d2)
= bounded adr_ratio lookup (grounding) + the deterministic guard _guard_ratio_claims, applied per released unit in
_consume_round. Every batch verdict judged it on "0 untraced ratio claims reach the stream", fresh phrasings included.
Baseline: no 'certification failures so far' clause in the note; not_certified in batch-12, 13, 14, 15 VERDICTS.json = 4;
no regression/partial verdict in refutation-audit REFUTATION_AUDIT.json or round-2.

## 2. Root cause (code read at HEAD)
sidecar/services/agent_runtime.py:1962 `_SENTENCE = re.compile(r".*?(?:[.!?]\s+|\n\s*|\Z)", re.DOTALL)` matches an unterminated
fragment up to \Z, and :2197
```
    return _Seg(pos, body_end, end, "sentence", bool(sentence) and sentence[-1].isspace())
```
marks it CLOSED whenever the held text merely ends in whitespace. _release_point (:2262) then releases it and
_guard_ratio_claims judges the half-sentence alone. llama3.1:8b streams a bare ' ' token before every number (live frames:
' ', '20', '-F' / ' ', '6', ':' / ' ', '1'), so every ratio sentence is cut right before its count. The one-hop
turn.ratio_context (:2853) rescues the next fragment only when it contains "share(s)"; a count fragment without that word
("1:6.", "5 or ", "1 to ", "1 underlying equity.") passes as not-a-claim, and the hop is lost after it.

## 3. The verifier's refutation re-run at HEAD
Its own sim (`sidecar/.venv/bin/python scratchpad/rc1-verifier-r4/ratio_sim.py`) at HEAD:
```
WHOLE (one delta):       "The ADR-to-ordinary-share ratio is not available from this session's sources."
SPLIT after 'equals ':   "The ADR-to-ordinary-share ratio is not available from this session's sources. 6 ordinary shares, per the 20-F."
SPLIT token-like:        "The ADR-to-ordinary-share ratio is not available from this session's sources. 6 ordinary shares, per the 20-F."
_seg_at('One ADR of SIFY equals ',0).closed = True
```
The mechanism claim (_seg_at closed = True on 'One ADR of SIFY equals ') holds. But the sim calls _guard_ratio_claims with a
fixed ctx=False and never threads turn.ratio_context as _consume_round does, so its example's output is NOT what the runtime
produces. Through the REAL invoke_agent (scripted provider, round 1 fundamentals -> bare SIFY result with no depositary
field, round 2 the deltas; `cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/ratio_rt.py all`):
```
== rc1-verifier:2, verifier's own cases, REAL runtime (context threaded), bare fundamentals (no ratio source)
WHOLE
   deltas=['One ADR of SIFY equals 6 ordinary shares, per the 20-F.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
SPLIT after 'equals '
   deltas=['One ADR of SIFY equals ', '6 ordinary shares, per the 20-F.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources. The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
TOKEN-LIKE (verifier's list)
   deltas=15 llama-style tokens
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources. The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
```
The verifier's exact case double-replaces; nothing leaks. So its stated example is a sim artefact. The class claim holds
on other wordings (section 4) and live on the entry's own prompt (section 5).

## 4. Fresh fabrications through the real runtime (no ratio source; whole-sentence control vs llama-style chunking)
```
== fresh fabrications (bare fundamentals, no ratio source): whole-sentence control vs llama-style chunking
WHOLE  The ADR ratio for SIFY is 1:6.
   deltas=['The ADR ratio for SIFY is 1:6.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  The ADR ratio for SIFY is 1:6.
   deltas=11 llama-style tokens
   OUT='The ADR ratio for SIFY is 1:6.'
   replaced=False  figure-left-outside-replacement=True
WHOLE  Each SIFY ADR represents 5 or 6 ordinary shares.
   deltas=['Each SIFY ADR represents 5 or 6 ordinary shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  Each SIFY ADR represents 5 or 6 ordinary shares.
   deltas=12 llama-style tokens
   OUT='Each SIFY ADR represents 5 or 6 ordinary shares.'
   replaced=False  figure-left-outside-replacement=True
WHOLE  SIFY's ADR-to-share ratio is 1 to 6.
   deltas=["SIFY's ADR-to-share ratio is 1 to 6."]
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  SIFY's ADR-to-share ratio is 1 to 6.
   deltas=14 llama-style tokens
   OUT="SIFY's ADR-to-share ratio is 1 to 6."
   replaced=False  figure-left-outside-replacement=True
WHOLE  Each ADS of Sify is backed by 4 to 5 equity shares.
   deltas=['Each ADS of Sify is backed by 4 to 5 equity shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  Each ADS of Sify is backed by 4 to 5 equity shares.
   deltas=15 llama-style tokens
   OUT='Each ADS of Sify is backed by 4 to 5 equity shares.'
   replaced=False  figure-left-outside-replacement=True
WHOLE  One SIFY ADS equals 6 ordinary shares.
   deltas=['One SIFY ADS equals 6 ordinary shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  One SIFY ADS equals 6 ordinary shares.
   deltas=9 llama-style tokens
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources. The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
```
4 of 5 fresh fabrications are replaced when they arrive as one delta and stream COMPLETELY UNGUARDED under llama chunking.
Same mechanism on a TRUE, sourced ratio (ads_ratio 6 in the result; `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/ratio_extra.py`):
```
== TRUE sourced ratio (ads_ratio 6), no date: whole vs llama-chunked (the live sk-sify-local-t1 shape)
WHOLE  One SIFY ADR represents 6 ordinary shares.
   deltas=['One SIFY ADR represents 6 ordinary shares.']
   OUT='One SIFY ADR represents 6 ordinary shares.'
   replaced=False  figure-left-outside-replacement=True
LLAMA  One SIFY ADR represents 6 ordinary shares.
   deltas=9 llama-style tokens
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources. 6 ordinary shares."
   replaced=True  figure-left-outside-replacement=True
== _seg_at closed flags at HEAD
'One ADR of SIFY equals ' closed = True | release_point = 23
'Each SIFY ADR represents ' closed = True | release_point = 25
'5 or ' closed = True | release_point = 5
'Each ADR represents 6 shares. ' closed = True | release_point = 30
'Each ADR represents 6 shares.' closed = False | release_point = 0
```
The llama-chunked true sentence becomes "... not available from this session's sources. 6 ordinary shares.": byte-for-byte
the round-4 live transcript scenarios/sk-sify-local-t1 at the candidate.

## 5. Live at HEAD, llama3.1:8b, the ENTRY'S OWN prompt (autonomy ask)
`python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/inv.py "How many ordinary shares does one SIFY ADR represent, and what is SIFY's TTM revenue in USD?" a090-own-1.jsonl ask`
```
{"kind": "tool_use", "name": "financial_statements", "input": {"period": "quarterly", "statement": "income", "symbol": "SIFY.US"}}
{"kind": "tool_result", "name": "financial_statements", "ok": false, "error": "provider error: yfinance income statement failed for 'SIFY.US': $SIFY-US: possibly delisted; no price data found  (period=5d) (Yahoo error = \"No data found, symbol may be delisted\")"}
deltas[:8] = ["The ADR-to-ordinary-share ratio is not available from this session's sources. ", '1', ' underlying', ' equity', '.\n\n', 'As', ' for', ' the']
TEXT: The ADR-to-ordinary-share ratio is not available from this session's sources. 1 underlying equity.

As for the TTM revenue in USD, the terminal's data does not include it due to a provider error. I'm unable to fetch the latest information on SIFY's income statement.
secs 36.1
sidecar log: 2026-09-27 06:59:40,242 INFO services.agent_runtime: ratio guard replaced an untraced claim: 'For SIFY ADR, one ordinary share represents'
```
No tool result carries a ratio (only financial_statements ran, and it errored), yet "1 underlying equity." — the entry's
original 1:1 fabrication — reaches the user right after the replacement, because the claim sentence was released at the
bare ' ' before '1' and the count fragment has no "share" word. The same mid-sentence splice shows on the hosted lane at the
candidate (scenarios/sk-sify-hosted-t2: "... sources. 5 or The ADR-to-ordinary-share ratio ...").
Other live runs at HEAD (for balance): own-2 and fresh-1 ("Give me SIFY's depositary ratio written as 1:N ...") called
fundamentals, got ads_ratio, and stated the TRUE six (kept, correct); fresh-2 (TSM '1 to N') stated no ratio.
Two further adversarial phrasings at HEAD stated no ratio (fresh-3 BABA '1:N': fundamentals BABA.A errored, answer 'couldn't
retrieve'; fresh-4 Infosys 'N or M': fundamentals INFY.OQ errored, the hedge sentence was replaced). The live leak is therefore
shown once in 9 local llama3.1:8b runs at HEAD (own-1); the mechanism is deterministic for any count fragment without a 'share' word (section 4).
With the fix applied in memory (scratch plugin /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/plug/segfix_plugin.py) every row of section 3/4 is replaced whole
(/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/ratio_rt_fixed.out), and tests/test_agent_runtime.py + tests/test_b5_runtime_notices.py stay green (274 passed, same as
unpatched).

## 6. Classification
The residual IS AGENT-090's class: an untraced depositary ratio reaches the stream on the local default model, including on
the entry's own prompt. The guard is the certified defence for a grounding miss, and it judges half-sentences. So the tie is
reopened as partial (the grounding half and the whole-sentence guard hold; the streamed-release path does not). Severity
high, raised from the verifier's medium: a fabricated ratio is shown as an answer, the entry's own severity.

Root cause: sidecar/services/agent_runtime.py:2197 (_seg_at marks a sentence closed when the held text ends in whitespace;
_SENTENCE :1962 matches to \Z), so _release_point releases, and _guard_ratio_claims judges, a half-sentence.
Fix shape: a "sentence" segment is closed only when its match ended on a real terminator: replace
`bool(sentence) and sentence[-1].isspace()` with `bool(re.search(r"(?:[.!?]\s+|\n\s*)\Z", sentence))` (a precompiled
pattern). A sentence is then judged whole, as the guard assumes; held prose still flushes at the terminator, at any
non-delta event and at stream end.
Acceptance: sidecar/tests/test_agent_runtime.py new parametrized test (via _scripted_answer and a llama-style chunker that
emits a bare ' ' before each digit run): against _SIFY_FUNDAMENTALS, "The ADR ratio for SIFY is 1:6.", "Each SIFY ADR
represents 5 or 6 ordinary shares.", "SIFY's ADR-to-share ratio is 1 to 6." and "For SIFY ADR, one ordinary share represents 1
underlying equity." each give exactly RATIO_UNAVAILABLE (no digit outside it); against _SIFY_FUNDAMENTALS_WITH_DEPOSITARY,
"One SIFY ADR represents 6 ordinary shares." streams unchanged; and `_seg_at("One ADR of SIFY equals ", 0).closed is False`.
Live: `cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/ratio_rt.py fresh` shows every LLAMA row replaced, and the entry's own prompt on
llama3.1:8b shows no digit outside a RATIO_UNAVAILABLE sentence unless a tool result carries it.

Certification-failure count (lands on R15-AGENT-090): baseline 4 (batch-12, 13, 14, 15 not_certified) + 1 = 5.

Observed, not classified here: own-2's "SIFY's TTM revenue is ₹4,651 crores (4,651 million INR)" answers a USD question in
INR without saying so and mislabels the crore figure (4,651 crore = 46,510 million INR). The batch-13 note folded the
INR-without-conversion half into this entry.
