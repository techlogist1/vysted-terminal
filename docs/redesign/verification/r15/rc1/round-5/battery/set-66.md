# batch-18/W2-sonnet (set-66)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52352

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-034 | in-process correctness_gate.symbols_match('INSPIRE','INSPIRE-SM.NS') etc.; curl /fundamentals/INSPIRE; grep sidecar boot log for SM.NS/mismatch | symbols_match now True for all 3 Emerge -SM.NS cases (was False/mismatch before the fix), unrelated symbols still correctly rejected; live 404 on INSPIRE is a provider-data-availability gap, not a correctness-gate symbol-mismatch (no mismatch/SM.NS trace anywhere in the boot log) | holds |

COVERAGE: 1/1 ids raw; no raw: none.
