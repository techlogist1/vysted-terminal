# laya-mlx measurement verdict — R15 scope change 2 (Laya groundwork)

Verification evidence only. No Laya code or integration exists in this release;
nothing here ships. All commands ran against the scratch venv/cache named below,
never the repo's `sidecar/.venv`. `docs/redesign/verification/r15/laya/measurements/`
holds one JSON file per step; this file is the roll-up.

## Setup

- Model: `laya.load("convaiinnovations/laya", revision="c5d78730f3493e4fe16d61507ef4b78eef7318cf", dtype="float16", batch_size=16)` — per `../INSTALL.md`/`../PACKAGE_VERIFICATION.md`.
- Env: `HF_HOME=<scratch>/laya-hf`, python = `<scratch>/laya-venv/bin/python` (3.12.13).
- Lane at launch (`measurements/lane.json`): load1 4.95/8 cpu, free 6.34 GB, 3 sidecars up
  on ports 52152-52154, no heavy jobs, ollama idle — clear.
- Dataset: `../dataset/{entity_match,composer_intent,holding_relevance}.jsonl` (199/53/87
  rows), per `../DATASET.md`.

## Split (`measurements/split.json`)

`python random.Random(918).shuffle` over each task's sorted ids, first half = A
(temperature-fit set), rest = B (eval set):

| task | n | A | B |
|---|---|---|---|
| entity_match | 199 | 99 | 100 |
| composer_intent | 53 | 26 | 27 |
| holding_relevance | 87 | 43 | 44 |

## (1) Zero-shot inference (`measurements/predictions.json`)

Every item run through `agent.predict(state, {qid: qdef})`, `state = json.loads(row["state"])`
passed as the dict `state` arg. Question type overridden per the smoke test in
`../INSTALL.md`: `entity_match`/`holding_relevance` → `noul` (instructions kept,
`criteria` dropped); `composer_intent` → `choice` (criteria = the 4 fixed options,
unchanged). Command: `<scratch>/laya-measure/run_zeroshot.py`, run detached under
`/usr/bin/time -l`, HF_HOME=`<scratch>/laya-hf`.

## (3) noul metrics on B (`measurements/noul_metrics.json`)

Threshold sweep 0.05 → 0.95 step 0.05. Gate = lowest threshold with precision ≥ 0.90
on B if one exists, else the max-F1 point; both reported.

| task | majority rate (B) | gate thr | gate P | gate R | gate F1 | max-F1 thr | max-F1 P | max-F1 R | max-F1 |
|---|---|---|---|---|---|---|---|---|---|
| entity_match | 0.71 | 0.95 | 1.00 | 0.056 | 0.107 | 0.10 | 0.773 | 0.958 | 0.855 |
| holding_relevance | 0.886 | 0.95 | 1.00 | 0.026 | 0.050 | 0.05 | 0.886 | 1.00 | 0.940 |

For both tasks the ≥0.90-precision gate exists but at ruinous recall (only the
most extreme `noul` scores clear it — the model is rarely near-certain). The
max-F1 operating point is the only one worth reading as a working threshold, and
for `holding_relevance` it is **identical in accuracy to always predicting the
majority label** — see verdict below.

## (2) composer_intent accuracy + confusion on B (`measurements/composer_metrics.json`)

Accuracy **0.630** (17/27) vs majority-rate baseline **0.333**. Confusion matrix
(gold rows, predicted columns) is in the JSON file in full.

## (4) Calibration (`measurements/calibration.json`)

Temperature fit on A by grid search (0.05→5.00, step 0.01) minimising mean NLL
over `z = log(p)` from laya-mlx's own already-softmaxed output probabilities,
rescaled `z/T`, re-softmaxed (laya-mlx applies its own internal calibration
before returning `probabilities`/`noul` — see the clamp warning in `../INSTALL.md`
— so this is a *second*, post-hoc temperature fit on top of that). ECE = 10
equal-width confidence bins, reported before (T=1.0) / after (fitted T), on B.

| task | T (fit on A) | ECE before (B) | ECE after (B) |
|---|---|---|---|
| entity_match | 4.06 | 0.066 | 0.167 |
| holding_relevance | 1.09 | 0.113 | 0.142 |
| composer_intent | 0.79 | 0.191 | 0.177 |

**The post-hoc fit makes calibration WORSE for both noul tasks** and only
marginally better for composer_intent. Full reliability tables in
`measurements/calibration.json`. The T was fit to minimise NLL, not ECE: on
entity_match it cuts NLL on A from 0.854 to 0.647 but raises ECE on A itself
(0.110 → 0.172), and on B it worsens NLL too (0.536 → 0.581); on
holding_relevance NLL on B is flat (0.408 → 0.407) while ECE rises
(critic fields in `measurements/calibration.json`). So a single NLL-fitted
temperature does not fix calibration on this data. Why is not established here.
(`../PACKAGE_VERIFICATION.md` claim #15 says the checkpoints are *over-confident
as shipped* and that domain temperature fitting improved ECE upstream, 0.213 →
0.081; the load-time clamp warning names only the `choice:11+` bucket.)

## (5) Latency + memory (`measurements/latency.json`)

| metric | value |
|---|---|
| single p50 | 42.2 ms |
| single p99 | 350.5 ms |
| single p50 (excl. first-call MLX compile warm-up) | 41.6 ms |
| batched p50 (batch=16, package's own `prepare`/`collate_items`/`forward`), amortized = batch wall / batch size | 38.5 ms/item |
| batched p99, amortized | 141.0 ms/item |
| single throughput | 16.9 items/s |
| batched throughput | 18.1 items/s |
| peak RSS (`/usr/bin/time -l`, whole run incl. model load) | 980,615,168 B ≈ 935.2 MB |
| steady RSS (`ps -o rss=`, sampled mid-run at item 169/339) | 886,640 KB ≈ 865.9 MB |
| peak memory footprint (`/usr/bin/time -l`, `<scratch>/laya-measure/time_wrapper.log`) | 12,180,033,728 B ≈ 11.3 GiB (host RAM 16 GiB, `sysctl -n hw.memsize`) |
| sidecars up during the run (from lane.json) | ports 52152 (Python), 52153 (vysted-op…), 52154 (vysted-se…) |

`system_one`/`predict()` only batches multiple *questions* on one shared
`state` — it has no public entry point for batching multiple *items* (each with
its own state), so "batched" here reuses the package's own `agent.prepare()` +
`laya_mlx.agent.collate_items()` + `agent.forward()` directly, batch_size=16
(the `load()`-time value). The batched p50/p99 are amortized cost, not the latency
one item sees: `run_zeroshot.py` records batch wall / batch size for every item, and
an item in a 16-item batch waits the whole batch (~16 × 38.5 ≈ 616 ms at the p50
batch). On amortized cost, batching buys ~9% p50 and ~7% throughput; the p99 ratio
(350.5 vs 141.0, ~2.5x) compares a per-call tail with a batch-averaged one and is not
a like-for-like tail gain. Why the gain is small was not measured.

## (6) Current path (`measurements/current_path.json`)

- **composer_intent**: `services.planner.classify_intent(text)` (keyless regex
  heuristic, `sidecar/services/planner.py:185`), run on the sidecar's own
  `.venv` (read-only import, `PYTHONPATH=sidecar`), same B items, same text.
  **Accuracy 0.815** (22/27) — beats laya zero-shot's 0.630 by 18.5 points,
  and beats it while running as a pure regex table ($0 per `../BASELINE.json`
  `cost_usd`; its latency is unknown: `latency_note` says "classify_intent is never
  timed"). The production path is "heuristic; paid planner pre-pass on compound
  turns only" (`../BASELINE.json`): 3 of the 27 B items are compound (composer-11,
  -42, -51 per `current_path.json`). On a planner provider they would also make one
  paid `decompose()` call. That call was not run; it does not change the intent label
  scored here.
- **entity_match**: `services.research.relevance.entity_match()`
  (`sidecar/services/research/relevance.py:522`) is a **shape mismatch** —
  it scores a web-search-result row (`title`/`url`/`excerpt`/`host`), not a
  markdown passage. Best-effort adaptation used: `row={"title": passage,
  "excerpt": "", "url": ""}`, target built from `context.symbol`/`context.entity`
  when a symbol is present (`MATCH_FLOOR`=0.34), else `target=None` with
  `query=entity` (`RELAXED_FLOOR`=0.2) — both constants read from the module,
  not guessed. **Accuracy 0.74** (74/100) on this adapted input — close to
  laya's max-F1 accuracy of 0.77, but the adaptation means this number is weak
  evidence in either direction; it is not a replay of the heuristic's real
  production input.
- **holding_relevance**: not run. `../BASELINE.json` states `path_today: "none
  (not implemented)"` — no call site exists in the sidecar for this decision
  today (the closest code, `gate_news`, matches news to the bound research
  target, not to a portfolio holding).

## Exact commands

```
uv venv <scratch>/laya-venv --python ~/.local/bin/python3.12   # (INSTALL.md, already done)
uv pip install --python <scratch>/laya-venv/bin/python "laya-mlx==0.2.0"  # (INSTALL.md, already done)

<scratch>/laya-venv/bin/python <scratch>/laya-measure/split_lib.py <repo>/.../measurements/split.json

HF_HOME=<scratch>/laya-hf nohup /usr/bin/time -l <scratch>/laya-venv/bin/python \
  <scratch>/laya-measure/run_zeroshot.py > <scratch>/laya-measure/time_wrapper.log 2>&1 &

<scratch>/laya-venv/bin/python <scratch>/laya-measure/metrics.py

PYTHONPATH=<repo>/sidecar <repo>/sidecar/.venv/bin/python <scratch>/laya-measure/run_current_path.py
```

## Verdict

**Not worth fine-tuning for this release, and the case for later is mixed.**
Zero-shot `laya-mlx` clears the majority-class floor on `composer_intent`
(0.630 vs 0.333) but loses outright to the sidecar's existing $0 (untimed)
regex heuristic (0.815) — the exact task PACKAGE_VERIFICATION.md's own
benchmark says needs fine-tuning to be worth using zero-shot (claim #13/#14: base
checkpoints sit below majority on the published benchmark; fine-tuned jumps to
0.766). On `holding_relevance` the model's best operating point is
statistically indistinguishable from always answering "yes" (0.886 accuracy,
exactly the majority rate, recall 1.0) — it isn't discriminating at all
zero-shot. `entity_match` is the one bright spot (max-F1 0.855, meaningfully
above the 0.71 majority baseline) but even there the current heuristic, run
on an admittedly unfair adapted input, is competitive (0.74 vs laya's 0.77
accuracy at the same operating point). Layer on top: a temperature refit made
calibration *worse*, not better, on both noul tasks; latency is ~40ms/item p50,
~935 MB peak RSS and a ~11.3 GiB peak memory footprint, against a $0 heuristic; and composer_intent — the
one task with a real, fast, working heuristic today — is the task laya is
worst at replacing. If Laya is revisited, `entity_match` is the only one of
the three worth a fine-tuning spend, and only after the shape mismatch here
is resolved with a real training set built from actual web-row inputs, not
markdown passages.

## Critic corrections (laya-verdict-critic)

Reproduction: `<scratch>/laya-critic/rerun.py` re-ran the single-item `predict` pass
with the same `load()` args and the same `to_question` override (imported from
`laya-measure`) over all 339 items (199/53/87, so at least 50 per task; composer_intent
has only 53). Outputs are **bit-identical** to `measurements/predictions.json`: max
|noul diff| 0.0 and 0 choice flips. `<scratch>/laya-critic/check.py` independently
recomputed the seed-918 split (it matches `split.json`, A∩B = ∅, and A∪B covers every
id), the gold labels, the threshold sweep, the gate rule, max-F1, composer accuracy
17/27, the majority rates, the T fits and ECE (10 bins) before and after. Every value
matches the JSON files. The current-path runs used exactly the B ids. Record:
`measurements/critic_rerun.json`. Single p50 reproduces (41.6 ms). p99 rests on about 3
of 339 samples and came out noisy (466.9 vs 350.5 ms).

Corrected in place above:

1. **Calibration explanation.** The old text said a second temperature "fights" an
   already-calibrated output and cited PACKAGE_VERIFICATION claim #15 as support. Claim
   #15 says the opposite: the checkpoints are over-confident as shipped, and temperature
   fitting helped upstream. The clamp warning names only `choice:11+`. The fitted T also
   worsens ECE on the fit set A itself. The rise comes from fitting T for NLL rather than
   ECE, not from A→B overfitting. The cause is not established.
2. **Batched latency is amortized.** It is batch wall / batch size, not per-item
   latency. An item in a batch waits about 616 ms. The "~2x p99 tail" claim was
   withdrawn (the ratio is 2.5x and not like-for-like). The unsourced "CPU/metal-bound
   per-token" explanation was removed.
3. **Memory was understated.** `/usr/bin/time -l` reports a peak memory footprint of
   12,180,033,728 B (measurer's `time_wrapper.log`), and 12,177,887,232 B in the critic
   re-run, on a 16 GiB host. The earlier text gave only the ~935 MB RSS. What makes up
   the footprint was not verified.
4. **"Effectively sub-millisecond" had no source.** BASELINE.json says classify_intent
   is never timed, so its latency is now marked unknown.
5. **The current-path comparison left out the paid pre-pass.** It now says the
   production composer path includes a paid planner pre-pass on compound turns. 3 of the
   27 B items are compound. Nothing paid was run, and the intent label scored is
   unaffected.

Checked and left unchanged: the gate is correctly the lowest threshold with P ≥ 0.90
(entity_match 0.85 → P 0.884, holding_relevance 0.80–0.90 → P < 0.90), but it rests on 4
and 1 positive predictions. entity_match's best accuracy on the sweep is 0.79 (thr
0.55/0.65), against the 0.77 quoted at the max-F1 point. The heuristic comparison is on
the same B items. The line references planner.py:185, relevance.py:522 and
MATCH_FLOOR/RELAXED_FLOOR 0.34/0.2 match source.
