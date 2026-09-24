# Laya groundwork dataset — R15 scope change 2

Base checkout: `b3f7f284`. Verification evidence only — no Laya code
ships in this release, no release document (README/CHANGELOG/runbooks/
briefings/docs/*.md/DECISIONS*.md) references Laya.

## Counts per task

| task | rows |
|---|---|
| entity_match | 199 |
| composer_intent | 53 |
| holding_relevance | 87 |
| dropped (all families) | 27 |

## Class balance per task

- **entity_match**: {'yes': 143, 'no': 56}
- **composer_intent**: {'read': 11, 'edit': 17, 'build': 13, 'research': 12}
- **holding_relevance**: {'yes': 77, 'no': 10}

## Majority-class rate per task

- **entity_match**: 0.7186
- **composer_intent**: 0.3208
- **holding_relevance**: 0.8851

## Provenance summary by source family

| family | task | agreed items written |
|---|---|---|
| research | entity_match | 105 |
| collision | entity_match | 94 |
| composer | composer_intent | 53 |
| news | holding_relevance | 87 |

## Cross-family duplicates

None found.

## Two-labeller protocol

Two Opus labellers per shard of 80 candidates, identical prompts apart from
the role name, each blind to the other's answer. Agreed = same answer and
neither labeller returned `skip`. Disagreements (including any `skip`) are
dropped — no third labeller, no retry on disagreement. `DROPPED.jsonl` carries
`{id, task, a, b}` for every dropped item (the two raw answers).

## Agreement rate per family

| family | agreed | total | agreement rate |
|---|---|---|---|
| research | 105 | 106 | 0.9906 |
| collision | 94 | 118 | 0.7966 |
| composer | 53 | 55 | 0.9636 |
| news | 87 | 87 | 1.0 |

## Row format

Dataset rows follow the fine-tune format documented in `PACKAGE_VERIFICATION.md`
(laya-mlx is inference-only; the format is Upstream's notebook-documented
`typed-decisions` shape, dataset `LocalLLaMA/typed-decisions`, config `all`):
`id`, `workflow`, `state` (JSON string), `questions` (JSON string
`{qid: {"type", "instructions", "criteria"}}`), `gold` (JSON string
`{qid: {"label", "probabilities": {option: p}}}`). Binary tasks (`entity_match`,
`holding_relevance`) use `criteria: ["yes", "no"]` and probabilities keyed
`"true"`/`"false"`. `composer_intent` uses the four composer options as criteria
and probability keys. Each row also carries `provenance` (source file + locator +
base sha `b3f7f284`) from the candidate line.

