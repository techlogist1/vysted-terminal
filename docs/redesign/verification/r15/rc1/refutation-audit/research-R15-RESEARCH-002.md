# Refutation audit: R15-RESEARCH-002 (group research)

- **Verdict:** partial
- **HEAD:** confirmed `6741387b` at start. During the run, HEAD moved to `91dac548`, which adds two docs-only commits (`5e7fc47e`, `91dac548`). `git diff 6741387b HEAD` over `sidecar/services/research/{verify,deep,finance}.py`, `sec_filings_provider.py`, `routers/sec_filings.py`, `agent_tools/sec_tools.py` and `src/store/sec.ts` is empty, so the audited code is byte-identical.
- **Certified by:** stage-c batch-2 `VERDICTS.md:112`. The three proven UNVERIFIED strings plus `**UNVERIFIED**: sources confirm nothing` parse as unverified.
- **Refuted by:** `rc1-verifier:1` (`inproc-refutations.txt`). Verdicts wrapped in a label (`Verdict: UNVERIFIED ...`, `**Verdict:** UNVERIFIED`, `Answer: UNVERIFIED`, `[UNVERIFIED]`, `The claim is UNVERIFIED; ...`) parse as `agree`.

## Commands

The scratch scripts are `r002.py` (the entry repro plus the verifier strings, in-process) and `ollama002.py` (a live llama3.1:8b run of the real `_verdict_for` prompt, under the ollama lock).

```
cd sidecar && PYTHONPATH=. .venv/bin/python $SCRATCH/refaudit-research/r002.py
## entry repro
'UNVERIFIED - no source confirms the 23% operating margin.' -> unverified
'UNVERIFIED - evidence does not support the figure' -> unverified
'UNVERIFIED - no matching figure' -> unverified
'**UNVERIFIED**: sources confirm nothing' -> unverified
'DISAGREE - reuters says 21%' -> disagree
'AGREE - reuters and bse confirm' -> agree
## verifier refutation
'Verdict: UNVERIFIED - no source confirms the 23% operating margin.' -> agree
'**Verdict:** UNVERIFIED - no source confirms it.' -> agree
'Answer: UNVERIFIED - evidence does not support the figure.' -> agree
'[UNVERIFIED] the sources do not confirm this.' -> agree
'The claim is UNVERIFIED; nothing I found confirms the 23% margin.' -> agree
'Verdict: DISAGREE - sources agree on 21% not 23%' -> disagree
'Verdict: AGREE - reuters confirms' -> agree
'- UNVERIFIED - no source confirms' -> unverified
'1. UNVERIFIED - no source confirms' -> agree
'UNVERIFIED. No source confirms it' -> unverified
'Unverified — no source confirms the figure' -> unverified
```

Live llama3.1:8b, the real `verify._verdict_for` prompt, 6 samples. The claim is a 23% operating margin that the evidence never states.

```
(claim: 'str', rows: 'list[dict[str, Any]]', domains: 'set[str]', llm_call: 'LLMCall', *, native_text: 'str' = '') -> 'tuple[str, str]'
   RAW: 'UNVERIFIED - Evidence does not contain the figure.'
0 ('unverified', 'UNVERIFIED - Evidence does not contain the figure.')
   RAW: 'DISAGREE - MoneyControl mentions net profit (Rs 60 crore) but no operating margin figure is found in the snippet. Reuters does not contain this figure either.'
1 ('disagree', 'DISAGREE - MoneyControl mentions net profit (Rs 60 crore) but no operating margin figure is found in the snippet. Reuters does not contain this figure either.')
   RAW: 'DISAGREE - moneycontrol.com (order book figure) and reuters.com (revenue growth rate).'
2 ('disagree', 'DISAGREE - moneycontrol.com (order book figure) and reuters.com (revenue growth rate).')
   RAW: 'DISAGREE - Reuters states Kaynes Q2 revenue rose to Rs 572 crore (as-of 2026-09-25) and Moneycontrol mentions net profit of Rs 60 crore.'
3 ('disagree', 'DISAGREE - Reuters states Kaynes Q2 revenue rose to Rs 572 crore (as-of 2026-09-25) and Moneycontrol mentions net profit of Rs 60 crore.')
   RAW: "DISAGREE - moneycontrol.com and reuters.com do not contain the figure 23% for Kaynes Technology's operating margin."
4 ('disagree', "DISAGREE - moneycontrol.com and reuters.com do not contain the figure 23% for Kaynes Technology's operating margin.")
   RAW: 'DISAGREE - No specific information about operating margin is provided on moneycontrol.com and reuters.com. \n\n(Note: The data provided does not contain the figure for operating margin as requested.)'
5 ('disagree', 'DISAGREE - No specific information about operating margin is provided on moneycontrol.com and reuters.com.')
lock released
```

## Reasoning

**The entry's own repro holds at HEAD.** All three proven strings plus the markdown variant return `unverified`. DISAGREE and AGREE still parse correctly. This matches the fix shape: `verify.py:120-141` `_parse_verdict` uses `deep.leading_token`, defined at `deep.py:348-362`.

**The verifier's strings reproduce exactly at HEAD.** Every reply that carries the literal verdict word UNVERIFIED, but not as the first token, is read as `agree`. The same is true of a numbered `1. UNVERIFIED - ...`. The mechanism is `verify.py:134-140`. When the head is not a verdict token, the fallback marker scan runs over the whole line. The reason clause ("confirms" / "support") then matches `_AGREE_MARKERS` (`verify.py:109`), even though the line names UNVERIFIED as a standalone word.

**This is the entry's own defect class, not a new one.** The class is `llm-output-marker-scan`: a claim that the model reported UNVERIFIED is rendered AGREE because a substring scan reads the reason's wording. It also breaks the parser's own docstring contract: "a verification round must never upgrade a claim it could not actually check".

**The fix is partial, not a regression.** The fix shape itself kept the marker fallback "only when the head is not a verdict token". That means the fix holds for the stated repro but not for the labelled forms of the same defect.

**Severity context.** No live model has been observed emitting a labelled verdict: llama3.1:8b led with the bare word in 6 of 6 samples. Separately, llama said DISAGREE where UNVERIFIED was right. That is model quality, not the parser. The residual risk is providers or models that preface the verdict with a label.

## Root cause

`sidecar/services/research/verify.py:134-140`. When `leading_token` does not match, the fallback runs `_DISAGREE_MARKERS` / `_AGREE_MARKERS` substring scans before it looks for a standalone verdict word elsewhere in the first line. `sidecar/services/research/deep.py:359-361` peels only `*:-#>` punctuation, so a `Verdict:` label, `[ ]` brackets or `1.` numbering hide the token.

## Acceptance test

Add `test_parse_verdict_reads_a_labelled_verdict_word` to `sidecar/tests/test_research_verify.py`:

- Each of these must parse as `_parse_verdict(s)[0] == "unverified"`:
  - `'Verdict: UNVERIFIED - no source confirms the 23% operating margin.'`
  - `'**Verdict:** UNVERIFIED - no source confirms it.'`
  - `'Answer: UNVERIFIED - evidence does not support the figure.'`
  - `'[UNVERIFIED] the sources do not confirm this.'`
  - `'The claim is UNVERIFIED; nothing I found confirms the 23% margin.'`
  - `'1. UNVERIFIED - no source confirms'`
- `'Verdict: DISAGREE - sources agree on 21% not 23%'` must parse as `disagree`.
- `'Verdict: AGREE - reuters confirms'` must parse as `agree`.
- The existing `test_parse_verdict_is_conservative` and `..._reads_the_leading_verdict_word_not_the_reason` must stay green.

**Fix direction:** before the marker scan, take the first standalone upper-case `\b(UNVERIFIED|DISAGREE|AGREE)\b` in the first line, checking UNVERIFIED and DISAGREE before AGREE.
