# batch-12/W1-w1 (set-56)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-56/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-028 | Live: `GET /quotes/506597.BO`, `GET /quotes/544774.BO`, `GET /history/506597.BO?range=1y` | 506597.BO -> AMAL 673.05 INR via `bse` (200, not 404); 544774.BO -> SMR 94.0 INR via `bse` (200); history -> `provider:bse`, 256 bars. A numeric BSE scrip code resolves exactly like the cert's own cases (506597.BO/544774.BO -> AMAL/SMR via bse). | holds |
| R15-DATA-115 | Live: `GET /history/AMAL.BO?range=1y`, `RELIANCE.BO?range=1y` (class pin), `AMAL.NS?range=1y` (control) | AMAL.BO -> `provider:bse`, 256 bars (was 28 nse_direct bars pre-fix). RELIANCE.BO -> `provider:bse`, 256 bars. Control AMAL.NS -> `provider:nse_direct`, 29 bars (unaffected — the `.NS` suffix still correctly routes to NSE). | holds |
| R15-DATA-059 | Live: `GET /resolve?q=ONC`, `?q=SIFY`, `?q=META&region=US`, `?q=TCI&region=US` | ONC -> `former_name:"BeiGene, Ltd."`. SIFY -> `former_name:"SIFY LTD"`. META (region=US) -> `name:"Meta Platforms, Inc."`, `former_name:"Facebook Inc"`. TCI (region=US) -> `name:"TRANSCONTINENTAL REALTY INVESTORS INC"`, `isin:null`, `bse_code:null` (no Indian identity leaks into the US resolution). All four match batch-12's cert exactly once the region param is supplied the way the cert used it (an unqualified default-IN-session query for an ambiguous ticker like TCI/META correctly disambiguates to the Indian listing instead — a separate, correct behavior, not a defect). | holds |

Summary: 3 holds, 0 regressions. First-pass probes for TCI/META omitted the `region=US` disambiguation param the cert used and initially looked like a mismatch (both resolved to their Indian same-ticker listings); re-run with `region=US` reproduced the cert's exact figures, so this was a test-setup gap on my part, not a candidate defect — corrected in the raw evidence file.
