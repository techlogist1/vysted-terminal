# Set: batch-2/W3-research-integrity (set-2.md) - rc1-battery-15 at ace7dd76

Probes ran in-process with the candidate venv (sidecar cwd) against the candidate source; the live OpenAI/Ollama research runs the originals used were replaced by in-process replicas on the same code paths (no spend, no Ollama lane). Raw: battery/raw/set-2/<id>.txt

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-002 | _parse_verdict on the 3 original UNVERIFIED strings + controls | all 3 + '**UNVERIFIED**: ...' -> unverified; DISAGREE/AGREE parse correctly | holds |
| R15-RESEARCH-034 | reflect_says_complete('Price action is not covered yet') | False; 'COMPLETE' True; 'no gaps' True | holds |
| R15-RESEARCH-004 | cross_check with claim lines starting with figures (40.5%, -0.4%, 67.13953, numbered) | claims intact in rows ('40.5% revenue growth', '-0.4% ...', '67.13953 P/E'); no '5%'/'4%'/'13953' mangling | holds |
| R15-RESEARCH-015 | dual-channel cross_check, one domain via both lanes | unverified, corroborated=False, 'only 1 independent source(s)'; distinct-lane control agree/corroborated True | holds |
| R15-RESEARCH-001 | gate_news over the ORIGINAL 129-item BDL feed (Sterling and Wilson Rs 985 cr present) + live /news?symbol=BDL | original: 129 in, 1 kept, Sterling/985 dropped; live: 50 in, 0 kept with honest note | holds |
| R15-RESEARCH-003 | iter loop: round-1 marker minted, round 2 adds PRIMARY sec.gov source | marker [1] still resolves to the round-1 url; primary source appended | holds |
| R15-RESEARCH-029 | strip_model_bibliography over original r3-ultra-kaynes published markdown | before: 19 '[n]' literals + Merged Sources + References; after: removed 9, 0 literals, no bibliography | holds |
| R15-RESEARCH-037 | priority_note on an unranked list | 'primary record ...: [2]; tier-1 press: [3]' real numbers | holds |

COVERAGE: 8/8 ids raw; no raw: none
