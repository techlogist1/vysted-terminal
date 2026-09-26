# Refutation audit round 2: R15-RESEARCH-015 (group surface, key rc1-verifier:12) at 4c6dfe8c (code tree; HEAD a3275f64, docs-only diff)

Verdict: **partial**. Audited 18:15-18:21 IST.

## Certification
- batch-2 VERDICTS.json: certified. VERDICTS.md:122: "one domain reached by both lanes → unverified ... corroborated False; control distinct lane domains → agree, corroborated True".
- Fix commit 88dc0ead. sidecar/services/research/verify.py:341 is now `independence = len(domains) + (1 if native_text and not native_rows else 0)`, which is the entry's fix_shape verbatim. verify.py:344 is `distinct_lanes = not native_rows or not native_domains <= searxng_domains`, which gates `corroborated` at :361-366.
- This id is absent from round-1 REFUTATION_AUDIT.json.

## Entry's own repro at the candidate
The entry's repro: a dual-channel ULTRA claim whose only evidence is one domain d, reached by both SearXNG and native, renders AGREE (corroborated) under a "2 independent sources" promise.
I drove it in-process with the real `verify.cross_check`, using the fakes from sidecar/tests/test_research_verify.py (a scratch driver, not a repo edit):
`cd sidecar && ./.venv/bin/python <scratch>/refaudit2-surface/r015.py`
Output (case A is the entry's literal repro; case B is the control):
```
_row_domains: ['nsearchives.nseindia.com', 'nseindia.com']
A entry repro: one host, both lanes: verdict=unverified domains=['blog.example'] corroborated=False verdict_llm_calls=0 rendered_corroborated=False
B control: distinct registrable domains: verdict=agree domains=['blog.example', 'other.example'] corroborated=True verdict_llm_calls=1 rendered_corroborated=True
C verifier: www.nseindia.com (searxng) + nsearchives.nseindia.com (native): verdict=agree domains=['nsearchives.nseindia.com', 'nseindia.com'] corroborated=True verdict_llm_calls=1 rendered_corroborated=True
D searxng-only: two subdomains of nseindia.com, no native: verdict=agree domains=['nsearchives.nseindia.com', 'nseindia.com'] corroborated=None verdict_llm_calls=1 rendered_corroborated=False
E entry repro, registrable-domain variant: same subdomain pair across lanes both ways: verdict=agree domains=['nsearchives.nseindia.com', 'nseindia.com'] corroborated=False verdict_llm_calls=1 rendered_corroborated=False
```
The certified pin test still passes: `./.venv/bin/python -m pytest -q tests/test_research_verify.py -k "one_domain_reached_by_both_lanes or distinct"` gives `1 passed`.

Case A: the literal repro, with one identical host string reaching both lanes, is **fixed**. It is unverified, no verdict LLM call is made, and nothing is rendered as corroborated.

## Verifier's refutation, re-run
The verifier's evidence is verifier/g2/spot-research015.txt, which showed `_row_domains` over www.nseindia.com and nsearchives.nseindia.com returning `['nsearchives.nseindia.com', 'nseindia.com']`, count 2. My re-run gives the same result (first line above). Root cause: `finance.domain_of` (sidecar/services/research/finance.py:139-150) strips only a leading `www.`. Its own docstring says "registrable-ish ... without a public-suffix dependency".

The verifier recorded only the helper output. I drove the full path:
- **Case C**: SearXNG reaches www.nseindia.com and native cites nsearchives.nseindia.com. The claim goes to the verdict LLM (independence 2 ≥ min_domains 2). The result is `agree`, `corroborated=True`, and it renders "AGREE (corroborated across channels)" under the "(2 independent sources required per claim)" header. Both hosts belong to one registrable domain, one publisher (NSE). This is the entry's title symptom verbatim ("a claim resting on one domain reached by both lanes is rendered 'AGREE (corroborated across channels)' under a '2 independent sources' promise"), reached through two hosts of that domain.
- **Case D** (SearXNG only, no native lane): two NSE subdomains also pass the independence floor and reach a verdict. This half lies outside the entry's native-lane scope. It is the same root cause and should ride the same fix.
- NSE hosts both hosts in real briefs: nsearchives.nseindia.com appears in r15/surface/research-briefs/r3-ultra-kaynes.jsonl, r2-deep-cgpower.jsonl and 11-deep-bdl-llama.jsonl. This is the common Indian-filings shape, not a contrived pair.

## Why partial
The verifier is not wrong: its pair reproduces the entry's exact user-visible defect end to end. It is not a regression either: the +1 double count is gone, and case A holds. The entry's fix_shape says "gate 'corroborated' on the two channels resting on different domains". The fix's own code comments (verify.py:338 "distinct registrable domains", :171 "registrable hosts") promise registrable domains, but `domain_of` delivers hosts. So a stated part of the same defect (one domain in both lanes reads as corroborated) still holds. The collator may instead register case D separately as an adjacent finding. Its root cause is the same.

## Root cause
sidecar/services/research/finance.py:150 (`return host.removeprefix("www.")`) is used by verify.py:170-177 `_row_domains`. Independence (verify.py:341) and the corroborated gate (verify.py:344) therefore count hosts, not registrable domains.

## Fix shape
In verify.py `_row_domains`, count a registrable domain instead of the host. Add a small `_registrable(host)` that keeps the last two labels, or the last three when the second-to-last label is in a short set of second-level public suffixes (co.in, co.uk, com.au, net.in, org.in, gov.in, ac.in, nic.in). Add a `# ponytail:` note that tldextract/PSL is the upgrade if coverage matters. Keep `finance.domain_of` unchanged, because its tier table keys on hosts. Both independence and distinct_lanes derive from `_row_domains`, so this one change covers cases C and D.

## Acceptance test
sidecar/tests/test_research_verify.py `test_two_hosts_of_one_registrable_domain_are_not_independent`. SearXNG `_web_tool(["https://www.nseindia.com/q"])` and native citations `[{"url":"https://nsearchives.nseindia.com/x.pdf"}]` with min_domains=2 must give `verdict == "unverified"`, `corroborated is False`, `llm.verdict_prompts == []`, and no "corroborated across channels" in the markdown. Also assert `_row_domains` over those two URLs == {"nseindia.com"}, and that `blog.example` + `other.example` still give `agree`/corroborated True.

Live re-proof: rerun the scratch driver. Case C must print `verdict=unverified ... corroborated=False`, and case D must print `verdict=unverified`.

## Certification-failure count
Batch not_certified lists: 0. Round-1 audit: 0. This gate: 1 (partial). **Total 1.**
