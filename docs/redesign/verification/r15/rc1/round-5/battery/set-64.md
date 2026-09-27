# Regression battery — batch-17/W1-one (set-64)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. In-process call of the real
`services.agent_runtime` module (candidate's own sidecar venv).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-031 | in-process `_release_point(text)` / `_units(text)` from `sidecar/services/agent_runtime.py` on a reconstruction of the batch-15 sify-1 shape: a benign guarded sentence immediately followed (no separator) by a leaked text-form tool-call JSON fragment (`'The ADR-to-ordinary-share ratio is 4:1.\n\n{"name": "price_data", "parameters": {"symbol'`) | `_release_point` cuts at 41, exactly before the JSON fragment; `_units` reports the fragment as its own **unclosed** unit (`closed=False`) distinct from the closed sentence unit — the guard releases only the closed sentence and holds the fragment back, so it can never be spliced onto guarded text with no separator (the defect's exact mechanism) | holds |

Raw output: `battery/raw/set-64/R15-LEAD-031.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
