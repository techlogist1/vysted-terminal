# unplanned-9

Candidate 4097dac4. Own sidecar :52346. Raw output: `raw/set-54/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-059 | `curl :52346/resolve?q=BeiGene` and `curl :52346/resolve?q=Toss%20the%20Coin%20Private%20Limited` (the register's own certified-closure repro, not the raw ticker lookup) | BeiGene: disambiguates to ONC and BEIGF, both `former_name: "BeiGene, Ltd."`. Toss the Coin Private Limited: resolves to TTC (BSE) with `isin: "INE0XAY01012"`, `board: "SME"`, `face_value: 10.0` — matches the register's own batch-11 closure note exactly | holds |

Summary: 1 hold. No regressions. Note: a direct `q=ONC`/`q=SIFY` ticker lookup still returns `isin`/`former_name`/`board: null` for US names — this matches the register's own closure note, which lists US-ticker-direct lookups (Facebook/Zomato/Adani/Square) as "fresh cases the fix was not written against"; the fix's certified scope is former-name-query resolution + Indian ISIN/board backfill, not blanket US ISIN/board backfill.
