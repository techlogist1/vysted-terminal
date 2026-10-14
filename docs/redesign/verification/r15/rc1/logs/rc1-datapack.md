# rc1-datapack working log

Candidate sha 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2.

- Found stale DATAPACK.md/datapack.json on disk from an earlier RC1 candidate (4097dac4,
  gate round 1). Confirmed sha mismatch against rc1-cand's actual HEAD; redid the drive
  fresh for this candidate rather than trusting the stale artifacts.
- Own sidecar: rc1-cand/sidecar on a fresh copy of rc1-seed-data, port 52313, detached
  (`sleep 86400 | ./.venv/bin/python3 main.py ...`), polled /health, confirmed healthy.
- 42 fixed register entries touch 10 battery symbols by word-boundary match (AMAL, DAL,
  SIFY, DHANBANK, SMR, JNPR, ELCIDIN, SUMAX, VIYASH, CREST) — narrower than a naive
  substring match, which over-counts on common words (SAFE, ICON, CSL, CHTR, TTC, JUMBO).
- Ran scripts/r15/collect_battery.py --port 52313 --force from a minimal copy tree
  (scratchpad/rc1-pack) so census baseline was never touched. Collector was slow
  (~13 minutes for 24 slots) due to its own concurrent fundamentals_warm cache job hitting
  Yahoo's rate limit and briefly opening the circuit breaker (56s park during P15 SUMAX) —
  same environment noise class the prior round documented. Monitored via the Monitor tool
  rather than foreground polling.
- While the collector ran, live-curled the rc1 sidecar directly for the 20 highest-value
  fixed entries (the numeric/data-correctness ones) using each entry's own stated repro,
  reading field_meta status/reason rather than just the raw value (several fixes are
  cross-check gates that keep the raw wrong number but flag it — DATA-013's DAL pe_ratio
  and DATA-005's VERTEX shares_outstanding both looked like regressions at first glance
  until field_meta.reason was read).
- 2 confirmed regressions: R15-DATA-008 (SIFY currency mislabel — exact original numbers
  still served under currency:USD with no reason) and R15-DATA-058 (Sify (ADR) resolve —
  SIFY included now but still ranked last despite the highest score).
- 1 environment finding: BSE shareholding index 403s for every BSE-only symbol this run
  (AMAL, SMR, CSL alike), blocking direct re-verification of DATA-003/DATA-022.
- After collection finished (24/24), ran a generic field-path re-diff (scratchpad/rc1-pack/
  redo_diff.py) against the census diffs for a broad sanity scan across all 24 slots.
  13 slots flagged; all 13 inspected by hand and explained as mapper artifacts (crore vs
  raw-rupee scale, percent vs decimal scale, sector-label wording) — zero additional
  regressions from the broad pass.
- Copied 24 collected JSONs to r15/rc1/battery/collected/, wrote DATAPACK.md, datapack.json,
  rediff_out.json, findings/rc1-datapack.json.
- Stopped own sidecar (killed both the detached sleep wrapper and the main.py process;
  confirmed :52313 no longer answers /health).
