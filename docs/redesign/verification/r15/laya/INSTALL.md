# laya-mlx scratch install and smoke test

Scratch-only verification: install + local smoke run of `laya-mlx` in an
isolated venv/cache outside the repo. No product code changed; no Laya
integration exists in this release.

## Environment

- Venv: `uv venv --python ~/.local/bin/python3.12` (Python 3.12.13, first
  candidate in the verified package facts; met `laya-mlx` requires-python
  >=3.11, no fallback to 3.13 needed).
- Venv location: scratch dir only, never the repo
  (`.../scratchpad/laya-venv`).
- HF cache: `HF_HOME=.../scratchpad/laya-hf` (scratch only, never
  `~/.cache/huggingface`).
- Machine: macOS 26.3, Apple Silicon (arm64), matches the laya-mlx/mlx
  wheel's `macosx_14_0_arm64` tag requirement.

## Install

Command:

```
uv venv <scratch>/laya-venv --python ~/.local/bin/python3.12
uv pip install --python <scratch>/laya-venv/bin/python "laya-mlx==0.2.0"
```

Result: succeeded, 20 packages installed (`uv pip freeze --python <scratch>/laya-venv/bin/python`):

```
anyio==4.15.1
certifi==2026.7.22
click==8.5.0
filelock==4.0.3
fsspec==2026.9.0
h11==0.16.0
hf-xet==1.6.0
httpcore==1.0.9
httpx==0.28.1
huggingface-hub==1.33.0
idna==3.20
laya-mlx==0.2.0
mlx==0.32.2
mlx-metal==0.32.2
numpy==2.5.3
packaging==26.3
pyyaml==6.0.3
tokenizers==0.23.2
tqdm==4.70.1
typing-extensions==4.16.0
```

Matches the verified package facts: `laya-mlx==0.2.0`, `mlx` pinned inside
`>=0.32.2,<0.33` (got 0.32.2), `numpy>=1.26` (got 2.5.3), `tokenizers>=0.21,<1`
(got 0.23.2), `huggingface-hub>=0.34,<2` (got 1.33.0). `import laya_mlx;
laya_mlx.__version__` reports `0.2.0`. No wheel sha256 was independently
verified — `uv` resolved and installed from PyPI directly; no mismatch or
install error was raised.

## Weights

Source: `convaiinnovations/laya` on the Hugging Face Hub, revision
`c5d78730f3493e4fe16d61507ef4b78eef7318cf`, fetched into the scratch
`HF_HOME` cache (never the repo, never `~/.cache`).

Files fetched (5), sizes on disk in the scratch cache:

| file | bytes |
|---|---|
| `model.safetensors` | 842,609,210 (~803.6 MB) |
| `tokenizer/tokenizer.json` | 3,583,228 |
| `tokenizer/tokenizer_config.json` | 308 |
| `encoder/config.json` | 2,083 |
| `rl_agent_config.json` | 745 |

Download took ~46s (unauthenticated HF Hub request, xet transfer backend).

## Smoke test

Script: `<scratch>/laya-smoke/smoke.py` (scratch only, never in the repo).
Loads the agent once (`laya_mlx.load("convaiinnovations/laya",
revision="c5d78730f3493e4fe16d61507ef4b78eef7318cf", dtype="float16",
batch_size=16)`), runs 20 items pulled from the repo dataset covering all
three task types, then exits (unloading the model). Run under
`/usr/bin/time -l`, detached, polled.

Item mix (20 total, first N rows of each dataset file, question type
override applied per the verified API summary):

- `composer_intent.jsonl` — 7 items, question type `choice` over the fixed
  `["read","edit","build","research"]` options (unchanged from the dataset).
- `entity_match.jsonl` — 7 items, question type overridden to `noul`
  (yes/no instructions kept, `criteria` dropped).
- `holding_relevance.jsonl` — 6 items, question type overridden to `noul`
  (same treatment).

Command:

```
HF_HOME=<scratch>/laya-hf /usr/bin/time -l <scratch>/laya-venv/bin/python <scratch>/laya-smoke/smoke.py
```

Wall time (`time -l` `real`): **51.43s** (includes the one-time ~46s weight
download + ~48.24s model load reported by the script — the load happens
concurrently with/just after the download inside that same 51.43s wall
clock per the process's own timestamps; the script's internal
`model loaded in 48.24s` timer starts before the HF download call returns).

Peak RSS (`time -l` "maximum resident set size"): **993,984,512 bytes ≈
947.9 MB**. (For reference, `time -l` "peak memory footprint" — a
different, Apple-specific metric — reported 3,324,055,744 bytes ≈ 3170 MB;
the task asks for maximum resident set size specifically, reported above.)

One non-fatal warning surfaced during model load, reproduced verbatim
(no secret material):

```
RuntimeWarning: laya-mlx: this checkpoint ships temperatures outside
[0.5, 5] which would distort confidence; clamping choice:11+=0.1006.
Treat confidence from the affected buckets as uncalibrated.
```

### Per-item latency

All 20 items completed. `predict()` call latency per item, milliseconds:

| id | workflow | gold | predicted | latency_ms |
|---|---|---|---|---|
| composer-1 | composer_intent | read | research | 1593.10 |
| composer-2 | composer_intent | read | research | 38.44 |
| composer-3 | composer_intent | edit | edit | 41.58 |
| composer-4 | composer_intent | edit | edit | 42.21 |
| composer-5 | composer_intent | build | research | 214.75 |
| composer-6 | composer_intent | build | edit | 34.47 |
| composer-7 | composer_intent | build | build | 43.65 |
| research-1 | entity_match | yes | noul=0.9255 | 67.30 |
| research-2 | entity_match | yes | noul=0.8147 | 172.80 |
| research-3 | entity_match | yes | noul=0.9072 | 105.89 |
| research-4 | entity_match | yes | noul=0.8372 | 65.87 |
| research-5 | entity_match | yes | noul=0.8950 | 48.84 |
| research-6 | entity_match | yes | noul=0.8618 | 63.28 |
| research-7 | entity_match | yes | noul=0.8794 | 57.14 |
| news-1 | holding_relevance | yes | noul=0.7996 | 46.25 |
| news-2 | holding_relevance | yes | noul=0.7574 | 44.88 |
| news-3 | holding_relevance | yes | noul=0.7910 | 47.44 |
| news-4 | holding_relevance | yes | noul=0.8043 | 46.47 |
| news-5 | holding_relevance | yes | noul=0.9469 | 38.24 |
| news-6 | holding_relevance | yes | noul=0.8084 | 35.25 |

p50 latency (median of the 20 `predict()` calls above): **47.44 ms**
(`composer-1`'s 1593.10 ms is the first-call MLX graph-compile/warm-up cost;
every subsequent call is sub-250 ms). Full per-item `answers` payloads
(probabilities, confidence, `action.act_probability`) are in
`smoke.log`/`results.json`, not reproduced in full here — the table above
gives the decision-relevant field per item (`choice` for composer_intent,
`noul` for entity_match/holding_relevance).

Raw outputs and the run log were produced only in the scratch dir
(`<scratch>/laya-smoke/smoke.log`, `<scratch>/laya-smoke/results.json`) —
not copied into the repo, per write-scope.

## Verdict

**FEASIBLE.** Install, weight fetch, and a 20-item smoke run covering all
three task types (`composer_intent` choice, `entity_match` noul,
`holding_relevance` noul) all completed successfully on this Mac
(Python 3.12.13, macOS 26.3 arm64) with no errors. Peak RSS ~948 MB,
p50 predict latency ~47 ms after the one-time model-load/compile warm-up.
