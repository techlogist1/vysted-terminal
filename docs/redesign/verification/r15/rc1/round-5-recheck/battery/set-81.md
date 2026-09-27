# batch-29/W1-opus — shard rc1-battery-12

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-001 | Live external news fetch (own sidecar :52352) for register's IN target (BDL, 0 items) and batch-29 fresh case (AI/C3.ai, 30 raw items); then in-process `relevance.gate_news` exactly as `deep.py:918-928` wires it before extraction | 30 raw AI items (alias-tagged but off-entity: Air India crash, bond-market roundups, OpenAI news) -> gate_news drops 10 off-entity items, keeps 20 C3.ai/AI-peer items; BDL still 0 raw (pre-existing data gap, unrelated) | holds |

COVERAGE: 1/1 ids raw; no raw: none.
