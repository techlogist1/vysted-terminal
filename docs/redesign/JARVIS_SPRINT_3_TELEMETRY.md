# JARVIS Sprint 3 — telemetry (the research-experience pass)

_Companion to [`JARVIS_SPRINT_3_REPORT.md`](JARVIS_SPRINT_3_REPORT.md) +
[`JARVIS_SPRINT_3_FINDINGS.md`](JARVIS_SPRINT_3_FINDINGS.md). Branch
`002-jarvis-intelligence`, base `2397260`. Not merged to main; version untouched._

---

## Phase 0 — fan-out spike

| Metric          | Value                                                                  |
| --------------- | ---------------------------------------------------------------------- |
| Agents          | 7 (4 read-only code-seam mappers `Explore` + 3 web-research `general`) |
| Subagent tokens | ~793k                                                                  |
| Tool calls      | 245                                                                    |
| Wall            | ~32 min                                                                |
| Output          | the four code seams + the typed-block schema + the Tongyi verdict      |

The spike confirmed the root cause (the brief is "dead data" unless a weak model
calls `publish_brief`) and the safe architecture (deterministic auto-publish +
frontend-derived typed blocks), so no track was built on an unverified guess.

## The governing principle this pass

**Reduce LLM dependence wherever deterministic logic can do the job.** Prior
passes' "felt intelligence" was capped by the default local model (`qwen2.5:7b`,
unreliable tool-use). Every Track-1/2/3 surface here is deterministic:

- The brief **auto-publishes** from the research tool result (runtime), not on a
  model `publish_brief` call.
- The typed blocks are **derived on the frontend** from `{markdown, structured,
sources}`, not emitted as model JSON.
- The chat **collapses** on a published brief regardless of how verbose the model is.
- The fit-aware arrange has a **deterministic guard** beneath the agent's choice.

Result: the experience holds up on the weak local model and steps up on a capable one.

## Per-track — decisions & forks (every fork kept a working fallback)

| Track                  | Decision                                                         | Fork / fallback                                                                                                                                                                         |
| ---------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — visual brief**   | frontend-derived typed blocks (metric/table/prose/heading/list)  | NOT model-emitted JSON (fragile on weak models). Markdown→blocks parser is a strict superset; empty body → no body, panel still frames.                                                 |
| **2 — clickable**      | ticker chips → `loadSymbolIntoChart` (always-consumed channel)   | detection = cashtag + known-set (resolved/watchlist/structured) + a stoplist-gated uppercase heuristic — precision over recall (a wrong chip just loads an empty chart, never harmful). |
| **3 — short + act**    | deterministic auto-publish (runtime) + frontend essay collapse   | rides the EXISTING proposed-changes gate (AUTO applies / review queues) — never bypasses §6.5. Idempotent with a model publish. Malformed result → skip (no half-publish).              |
| **3 — deep metrics**   | enrich DEEP/iter `structured` with a price+fundamentals snapshot | shared `snapshot_structured`; each leg pre-wrapped (a failed leg renders no card, never raises). FAST already carried it.                                                               |
| **4 — fit-aware**      | deterministic `fitLayoutTemplate` + agent viewport-awareness     | downgrade research-cockpit→chart+brief essentials / macro-scan→single-focus below a width threshold; unknown width (0) → never downgrade. Existing templates stay the fallback.         |
| **5 — engine + probe** | settings selector + live `/system/deepresearch/probe`            | Tongyi key on the foreground (never-persisted) request only; the durable delegate path carries the non-secret backend, never the key. Probe miss → "use the fallback", never an error.  |

## Tongyi routing (live-confirmed this pass)

`alibaba/tongyi-deepresearch-30b-a3b` = **0 endpoints (listed-but-unrouted)**;
the `alibaba` author is now absent from the 343-model OpenRouter catalog feed
entirely — only the `/endpoints` lookup resolves it. Unchanged from Sprint-1. The
probe resolves to `qwen/qwen3-30b-a3b-thinking-2507` (2 live endpoints) and SAYS
so. No `tongyi.py` code change needed; this pass built the UI + probe + honest
reporting around the correct existing probe logic.

## Floor

- **Tier-1 LOCKED files vs base `2397260`: EMPTY diff** (`types/plugin.ts`,
  `types/safety.ts`, `types/broker.ts`, the safety/broker/audit/kill-switch
  models, `broker_base.py`, `kill_switch.rs`, `test_safety_end_to_end.py`,
  `tauri.conf.json`, CI).
- **§6.5 safety audit: 9/9** (`test_safety_end_to_end.py`, 9 passed).
- **No new pip dependency** — the probe uses the already-shipped `httpx`; the
  block deriver / auto-publish are pure stdlib + existing modules. No PyInstaller
  `--copy-metadata`/`--collect-data`/`--add-data` exposure.
- **Orders never auto-apply** — the auto-publish emits only `publish_brief` (a
  UI mutation); the order exclusion in `proposed-changes` is untouched.
- **Secrets** — the OpenRouter key rides the probe header / foreground request
  only, never logged/echoed/persisted (asserted by `test_deepresearch_probe_
never_echoes_the_key`); never extracted to the shell.

## Verification (filled at close)

- `pnpm ci-local`: _recorded in the report_.
- `smoke-test-sidecars.mjs` (binary-runtime gap; the sidecar was rebuilt): _recorded_.
- Rig (live, awake, populated): _recorded in the report §rig evidence_.
