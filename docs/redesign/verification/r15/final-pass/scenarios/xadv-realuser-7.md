# xadv-realuser-7 — the US side of a collision, typed by its legal name ("IDEX Corporation")

Lens: an Indian investor who owns US stocks types the company's legal name the way it appears on its filings and on screener-style sites.
Found while probing the IEX collision (xadv-realuser-2). Own stack :52910, region IN (default). Raw: `xadv-realuser-raw/` s2b-us-suffix.txt, r-idex.json.

## Outside truth

The legal names are "IDEX Corporation", "Danaher Corporation", "Amphenol Corporation", "Newmont Corporation", "Bank of America Corporation" (the
product's own yfinance lane names IEX "IDEX Corporation": `/fundamentals/IEX` with `X-Vysted-Region: US` -> name "IDEX Corporation", s2-collisions.txt).
The bundled US master stores the SEC EDGAR ticker-file spelling: `IEX "IDEX CORP /DE/"`, `DHR "DANAHER CORP /DE/"`, `APH "AMPHENOL CORP /DE/"`,
`NEM "NEWMONT Corp /DE/"`, `BAC "BANK OF AMERICA CORP /DE/"` (sidecar/services/resolver_masters/us_instruments.json); 784 of 10,365 US rows end in a
slash suffix (`/DE/`, `/NEW`, `/NY`, `/ADR`, `/UK` ...).

## Results (GET /resolve)

```
IDEX Corporation   -> needs_disambiguation: KEYCORP Key Corporation Ltd BSE, KACL Kaiser Corporation Ltd BSE, RANDER, MEGACOR, MPILCORPL, IEHC IEH Corp US
Danaher Corporation-> RANDER, KACL, SANBLUE, PARSHWANA, KEYCORP (all BSE "... Corporation Ltd"), AES CORP US
Amphenol Corporation-> MPILCORPL, EMROCK, KEYCORP, KACL, RANDER, AES CORP US
Newmont Corporation-> EMROCK, NEUEON, KEMISTAR, STEP2COR, KEYCORP, GERON CORP US
Bank of America Corporation -> 5 BSE "... Corporation Ltd" rows, BAC last (the R15-DATA-058 reserved cross-region slot)
IDEX Corp          -> bound IEX "IDEX CORP /DE/" (works when the user types the abbreviated suffix)
TJX Companies      -> bound TJX
```

Research `{"query":"IDEX Corporation"}` returns `needs_disambiguation` with the same Indian shells; IDEX is not among the candidates (r-idex.json).

Root cause (source at the sha): `symbol_resolver._canonical_name` / `_strip_corporate_suffix` (symbol_resolver.py:907-930) pop trailing
`_CORP_SUFFIXES` only while the LAST token is a suffix; the master's last token is `/de/` (`_EDGE_PUNCT` at :209 has no `/`), not a suffix.
Run in the candidate's venv: `_canonical_name('danaher corp /de/') -> 'danaher corp /de/'`, `_canonical_name('danaher corporation') -> 'danaher'`, so
the master name never canonicalizes to "danaher" while the query "danaher corporation" does; the exact-modulo-suffix band misses and the fuzzy
band is dominated by the generic token "corporation", which every BSE "X Corporation Ltd" shares.

## R1-R3

R1: reproducible on the running sidecar (commands above). R2: the company's own legal name never finds a large US company and offers five
unrelated Indian micro-caps instead — a core search flow silently degrading for any US name typed in full -> medium. R3: R15-DATA-058 (fixed:
IN rows outrank a better US fuzzy row; fix reserved one cross-region slot — that slot holds, SIFY and BAC appear last) is a different mechanism
(ranking) from this one (the state-suffix token defeats the suffix strip); R15-DATA-059 (blocked_tier4, former names / US identity) differs.
No register entry names `/DE/` or the SEC state suffix. New.

VERDICT xadv-realuser-7: finding realuser:4
