# Package verification: laya and laya-mlx

Role: package verifier (laya-verify). Checked 2026-09-25 on this Mac (macOS 26.3 build 25D125, arm64; `sw_vers`, `uname -m`).
This is verification evidence only. Nothing was installed or imported, and no package code was executed. The two wheels were fetched with curl from the PyPI file URLs (they are the same files `pip download --no-deps --only-binary=:all:` would fetch), their sha256 was checked against the PyPI JSON, and they were unzipped and read.

Scratch evidence directory (S): `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/laya-verify/`

## Verdict

**VERIFIED, with one named deviation.** Both packages are Apache-2.0, both are pure-Python `py3-none-any` wheels with no install-time hooks and no import-time network or code execution, and both trace byte for byte to public GitHub source. laya-mlx supports this Mac with either Python 3.12.13 or 3.13.13.

**Deviation:** `laya-mlx` is **not** published by the Laya owner. It is an independent community port by GitHub user `mizorewww` (repo `mizorewww/laya-mlx`). Its README says: "This is an independent MLX port, not an official Convai Innovations release." It is not a typosquat. The port names its upstream (`project_urls.Upstream = https://github.com/NandhaKishorM/laya`), ships a NOTICE that attributes Convai Innovations, and has all 22 of its wheel `.py` files byte-identical to `mizorewww/laya-mlx@0a859518`. The upstream maintainer also calls it "community-maintained" in upstream issue #50. However, laya-mlx has no PyPI provenance attestation, and the PyPI uploader account could not be read.

## Claims: confirmed, refuted or unverifiable

| # | Claim | Status | Source |
|---|---|---|---|
| 1 | Open decision model from Convai Innovations | Confirmed. PyPI `author = Convai Innovations`. The HF org is `convaiinnovations` and the README says "Developed by Convai Innovations". The GitHub owner is the personal account `NandhaKishorM` (type User), and the PyPI maintainer is user `nandakishor`. | S/pypi-laya.json; `gh api repos/NandhaKishorM/laya`; S/page-laya.html; S/desc-laya.md l.1040 |
| 2 | Repo github.com/NandhaKishorM/laya | Confirmed. Created 2026-09-18T04:46:33Z, not a fork, default branch main, HEAD `970dc8c5` (2026-09-24T17:22:50Z). | `gh api repos/NandhaKishorM/laya`, `.../commits/main` |
| 3 | Apache-2.0 | Confirmed. The GitHub licence API reports `Apache-2.0`. `LICENSE` from GitHub is byte-identical to the wheel's `laya-0.3.20.dist-info/licenses/LICENSE` (plain Apache 2.0 text with no appendix copyright line). There is no NOTICE file upstream. laya-mlx has the identical LICENSE plus its own NOTICE. | S/gh-laya-LICENSE; S/x-laya/...; S/x-mlx/laya_mlx-0.2.0.dist-info/licenses/ |
| 4 | Released 18 Sep 2026 | Confirmed. PyPI laya 0.1.0 was uploaded 2026-09-18T04:38:51Z, the GitHub repo was created 2026-09-18T04:46:33Z and HF `convaiinnovations/laya` was created 2026-09-18T05:05:55Z. The earliest GitHub tag is v0.2.0 (there are no v0.1.x tags). | S/pypi-laya.json; gh api; S/hf-convaiinnovations_laya.json |
| 5 | 421M ModernBERT encoder, not a language model | Confirmed as documented. The README table lists `laya` as ModernBERT-large, 421M, 512 context. The architecture is "state + typed question -> bidirectional encoder -> decision heads -> probabilities". Parameter count not independently measured. | S/desc-laya.md l.115-119; S/desc-laya-mlx.md l.67-69, 83 |
| 6 | One forward pass. `choice` over a fixed option set with probabilities, `score` on an ordered rubric, `noul` as P(true) | Confirmed by code. `Agent.system_one` does one forward call per batch chunk. It returns `choice` + `probabilities`, `score` (expected zero-based level) + `legend` + `probabilities`, or `noul` = p[1]. | S/x-mlx/laya_mlx/agent.py `system_one` (read in full) |
| 7 | Generates nothing | Confirmed. The result carries `"usage": {..., "output_tokens": 0}` and there is no decoding loop. | S/x-mlx/laya_mlx/agent.py |
| 8 | PyPI `laya` (PyTorch) | Confirmed. Latest is 0.3.20 (uploaded 2026-09-24T05:41:06Z). It requires `torch>=2.0.0, transformers>=4.48.0, safetensors>=0.4.0, huggingface_hub>=0.20.0, numpy>=1.20.0`, with `requires_python >=3.10`. | S/pypi-laya.json |
| 9 | PyPI `laya-mlx` (Apple Silicon) | Confirmed, but it is a third-party port (see Deviation). Latest is 0.2.0 (uploaded 2026-09-22T06:02:20Z). Earlier: 0.1.0 (2026-09-19T16:36:24Z). | S/pypi-laya-mlx.json |
| 10 | laya-mlx: macOS 14+ | Confirmed as documented, but not in the package metadata. The README says "Apple Silicon, Python 3.11+, macOS 14+". The package metadata only has classifier `Operating System :: MacOS`. The mlx 0.32.2 wheels start at `macosx_14_0_arm64`. Only macOS 27.2 was tested by the port author. | S/desc-laya-mlx.md l.36; S/pypi-mlx.json |
| 11 | laya-mlx: Python 3.11+ | Confirmed. `requires_python >=3.11` (PyPI JSON and pyproject at 0a859518). | S/pypi-laya-mlx.json; S/gh-mlx/pyproject.toml l.18 |
| 12 | laya-mlx: under 1 GB resident | Unverifiable (not measured). The port's README reports **943.6 MiB peak MLX allocation** for one short question (421M model, FP16, M3 Max). That is an MLX allocator figure, not process RSS. `model.safetensors` alone is 842,609,225 bytes. | S/desc-laya-mlx.md l.57; S/hf-aac6fef-manifest.json |
| 13 | Zero-shot accuracy below the majority-class baseline | Confirmed. "The base checkpoints sit below the majority-class baseline (0.362 and 0.352 against 0.461)" on the typed-decisions benchmark (random = 0.318). | S/desc-laya.md l.842, 886-889 |
| 14 | A base to fine-tune | Confirmed. The fine-tuned `laya-typed-decisions` scores 0.766 against 0.362 for the base checkpoint. The README says "Treat Laya as a fast base to specialise, not as a zero-shot decision engine". | S/desc-laya.md l.85, 1005-1009 |
| 15 | Over-confident until a temperature is fitted | Confirmed. "Both checkpoints are over-confident as shipped." Raw ECE is 0.213, and 0.081 after domain temperature fitting. Load clamps temperatures to [0.5, 5.0], and the shipped `choice:11+` bucket of 0.1006 is clamped. | S/desc-laya.md l.815, 872-882; S/desc-laya-mlx.md l.144 |
| 16 | Weak past ~20 options | Confirmed. The README lists "High-cardinality label spaces (>20 options at default settings)" as a weakness: Banking77 scores 0.425 with 77 labels because the options share a `head_max_len` token budget. | S/desc-laya.md l.813, 897 |
| 17 | Weak on ordinal scores | Confirmed. "Ordinal `score` questions are the weakest primitive (SST-5 0.372)." | S/desc-laya.md l.930 |
| 18 | Context of a few hundred tokens | Confirmed for English `laya`: 512 context, `head_max_len` 192, "~320 tokens for state". `laya-multilingual` and `laya-typed-decisions` default to 1,024 (multilingual up to 8,192 with `max_len=8192`). | S/desc-laya.md l.117-119, 895-896 |

## Artefact inspection

| | laya 0.3.20 | laya-mlx 0.2.0 |
|---|---|---|
| Wheel | `laya-0.3.20-py3-none-any.whl` | `laya_mlx-0.2.0-py3-none-any.whl` |
| sha256 (matches PyPI JSON) | `6039e802fa5effb8dd492061cd7ad39a43087beadc4a4fa4a649614e77eb83d4` | `1a80a0cc79c55be808de0b1208a172566209b5780d796b98d86235e9cf335187` |
| Generator / purelib | setuptools 84.0.0, `Root-Is-Purelib: true` | hatchling 1.32.4, `Root-Is-Purelib: true` |
| `.pth`, `.so`, `.dylib`, `.pyc` | none | none |
| Build hooks (pyproject at source) | `setuptools.build_meta`, and `setup.py` is a bare `setup()` shim. No cmdclass. | `hatchling.build`, no `[tool.hatch.build.hooks]` |
| entry_points | `laya`, `laya-mcp-server`, `laya-serve` | `laya-mlx = laya_mlx.cli:main`, `laya-snake = laya_mlx.snake.cli:main` |
| Source trace | 21/21 `.py` byte-identical to GitHub tag `v0.3.20`. PyPI provenance attestation: publisher GitHub `NandhaKishorM/laya`, workflow `release.yml`. | 22/22 `.py` byte-identical to `mizorewww/laya-mlx@0a859518634112655cb97c745dbf04f5191aaf13`. No provenance attestation (integrity endpoint 404). |

**Import-time behaviour.** An AST scan of every module's top-level statements found only constant or regex tables and `threading.Lock()`. The exceptions are `laya/mcp/server.py`, which builds an `MCPServer` object when that submodule is imported (not imported by `laya/__init__`), and `__main__` guards. `laya/__init__` resolves torch-backed names lazily. `laya_mlx/__init__` imports `agent`, which imports `mlx.core`, `numpy` and `huggingface_hub.snapshot_download`. There is no network activity at import.

**Network.** The only network path in laya-mlx is `huggingface_hub.snapshot_download` inside `resolve_model()`, called from `Agent.__init__` / `load()`. Its allow-list is `model.safetensors`, `rl_agent_config.json`, `encoder/config.json`, `tokenizer/*` and `mlx_config.json`, with optional `token` and `revision`. `Router` reads `HF_TOKEN` from the environment. There is no telemetry code. The Snake demo sets `HF_HUB_OFFLINE=1` and `HF_HUB_DISABLE_TELEMETRY=1`.

In laya, the paths are `snapshot_download` (agent.py l.259-270, onnx_agent.py), `AutoTokenizer.from_pretrained(cfg["encoder"])` fallback (agent.py l.155), and a stdlib `urllib` client in `integrations/langchain.py` that only calls a caller-given `laya-serve` `base_url` and refuses cross-origin redirects.

**Code execution.** Weights load through safetensors only: `mx.load(...model.safetensors)` in laya-mlx and `safetensors.torch.load_file` in laya. There is no `torch.load`, pickle, `trust_remote_code`, `exec` or `eval(` on data (the `eval` hits are `mx.eval` and `model.eval()`). The subprocess calls are confined to the laya-mlx Snake demo: `sysctl -n machdep.cpu.brand_string` and an ffmpeg pipe in `snake/replay.py`. `laya/mcp/tools.py` uses `__import__("laya"/"transformers")` for version reporting only.

## Weights and their licence

| Checkpoint | Host | Licence | Notes |
|---|---|---|---|
| `convaiinnovations/laya` (root: English; subfolders `multilingual/`, `typed-decisions/`) | Hugging Face, public, not gated | apache-2.0 (card + tag) | `model.safetensors` sha256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`, 842,609,210 B. This is identical at pinned rev `c5d78730f3493e4fe16d61507ef4b78eef7318cf` (the revision the port validated) and at main `55cf4c4e`. |
| `convaiinnovations/laya-multilingual`, `convaiinnovations/laya-typed-decisions` | HF, public | apache-2.0 | |
| `aac6fef/laya-mlx` (+ `-multilingual-mlx`, `-typed-decisions-mlx`) | HF, third-party account `aac6fef` | apache-2.0 | FP16 re-export of `convaiinnovations/laya@c5d78730`. `model.safetensors` sha256 `b9c07bf1...a3de`, recorded in the port repo's `benchmarks/results/hub-publication.json`. |

Recommendation: load the **original** checkpoint with a pinned revision, `laya.load("convaiinnovations/laya", revision="c5d78730f3493e4fe16d61507ef4b78eef7318cf")`, which the laya-mlx README documents. This avoids trusting the third-party `aac6fef` mirror.

## Licence notice text needed later

Apache-2.0 §4 requires a copy of the licence text and retention of attribution notices. Upstream laya ships no NOTICE file. laya-mlx ships this NOTICE, verbatim from `laya_mlx-0.2.0.dist-info/licenses/NOTICE`:

```
laya-mlx
Copyright 2026 laya-mlx contributors

This product includes software derived from Laya:
https://github.com/NandhaKishorM/laya
Copyright Convai Innovations and Laya contributors. Licensed under Apache-2.0.
Upstream source revision: 573e5b62696ba441230cd6be71d593331b5d23af

The token sequence construction, question rendering, confidence calculation,
presets, email utilities and language router are adapted from Laya.
The neural network is reimplemented using Apple's MLX, following Laya's
DecisionModel and the ModernBERT architecture in Hugging Face Transformers.
Model weights are downloaded separately from Convai Innovations on Hugging Face;
they are not included in this repository.
```

Plus the full Apache License 2.0 text (identical in both wheels, 10,173 bytes).

## API usage (laya-mlx 0.2.0, from its README and agent.py)

```python
import laya_mlx as laya
agent = laya.load("convaiinnovations/laya", revision="c5d78730f3493e4fe16d61507ef4b78eef7318cf",
                  dtype="float16", batch_size=16)   # device="gpu"|"cpu"; compile/pad_to_multiple/cache_prompts opt-in
result = agent.predict(state, {                      # system_one is an alias; state = str | dict | conversation list
  "department": {"type": "choice", "instructions": "Which team should handle this?",
                 "criteria": {"billing": "invoices, payments", "technical": "bugs"}},  # or a list of unique labels
  "urgency":    {"type": "score", "instructions": "How urgent?", "criteria": ["not urgent", "soon", "critical"]},
  "refund":     {"type": "noul",  "instructions": "Does the customer ask for money back?"},
})
# result = {"model": "laya-rl-agent", "answers": {qid: {...}}, "usage": {"input_tokens": n, "output_tokens": 0}}
# choice -> {"choice": label, "probabilities": {label: p}, "confidence", "action": {"act_probability"}}
# score  -> {"score": expected 0-based level, "legend": {"0": ...}, "probabilities": {"0": p}, "confidence"}
# noul   -> {"noul": P(true), "confidence": max(p, 1-p)}
```

Other exports: `Router` (checkpoint routing by language), `predict_shortlist` + `embed_fn_from_agent` (for large option sets), the presets `triage_questions` / `email_questions` / `guard_questions` / `moderation_questions` / `router_questions`, and `detect_language`. There is also a CLI: `laya-mlx predict --model ... --state-file ... --questions ...`.

## Fine-tune data format

laya-mlx does inference only. Its README says "RLCD training and fine-tuning remain in the upstream project". Upstream documents fine-tuning only through the notebook `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`, read at commit `970dc8c5` (S/finetune.ipynb). It trains on HF dataset `LocalLLaMA/typed-decisions` (config `all`, splits `train`/`test`). The row fields are used verbatim:

- `id`, `workflow`
- `state`: a JSON string
- `questions`: a JSON string `{qid: {"type": "choice"|"score"|"noul", "instructions": str, "criteria": {label: desc} | [levels]}}`
- `gold`: a JSON string `{qid: {"label": ..., "probabilities": {label|"false"/"true"|"0".."n": p}, "noul"?: p}}`

The training target is the normalised `gold[qid]["probabilities"]` over the rendered options. The notebook fits one `temperature` per type and drops `temperature_by_options`. There is no standalone schema doc or training CLI. The format is inferred from notebook code, not a stable contract.

## Risks

1. **Third-party port.** laya-mlx is maintained by `mizorewww`, not Convai. It has no PyPI attestation and the uploader is unconfirmed. It was last synced to upstream v0.3.5 behaviour (commit `0a859518`), while upstream is at 0.3.20.
2. **Missing upstream fix.** laya-mlx 0.2.0 lacks upstream's `noul` `labels` override (no `labels` handling in `laya_mlx/common.py`). That override is the documented workaround for upstream issue #156, where `noul` follows the `false:`/`true:` label pair on the English checkpoint.
3. **Weak base model.** Zero-shot accuracy is below the majority-class baseline, and probabilities are over-confident until temperatures are fitted. `action.act_probability` carries no usable signal (upstream #185). Upstream warns against boolean-word labels in `choice`.
4. **Silent truncation.** English context is 512 tokens (~320 for the state). `build_sequence` silently truncates the state to the room left (`st[:room]`) with no warning. Options past the `head_max_len` budget raise "too many options for the token budget". Accuracy is weak above ~20 options.
5. **Brittle pin.** laya-mlx pins `mlx<0.33,>=0.32.2`, and 0.32.2 is the current latest. The mlx dependency carries a `darwin and arm64` marker, so on other platforms the package installs without mlx and fails at import.
6. **First-load network.** First load downloads about 843 MB from Hugging Face. Pin `revision=` and set `HF_HUB_OFFLINE=1` after the download for deterministic, offline runs.
7. **Churn.** The project is 7 days old, with 21 laya releases between 2026-09-18 and 2026-09-24. Pin exact versions.
8. **Unusual repo stats.** GitHub shows 22,977 stars and 1,976 forks for NandhaKishorM/laya, and 6,214 stars for the port, within about a week. This is noted only, not assessed.
9. **Unmeasured memory.** The "<1 GB resident" figure is unverified. The documented figure is 943.6 MiB peak MLX allocation on M3 Max, not RSS on this M1.

## Pinned install (for the scratch venv only, not this release)

`<python> -m pip install "laya-mlx==0.2.0"`, where `<python>` is `~/.local/bin/python3.12` (3.12.13) or `/opt/homebrew/bin/python3.13` (3.13.13). Both have cp312/cp313 `macosx_14_0_arm64` mlx 0.32.2 wheels. Expected wheel sha256 is `1a80a0cc79c55be808de0b1208a172566209b5780d796b98d86235e9cf335187`.
