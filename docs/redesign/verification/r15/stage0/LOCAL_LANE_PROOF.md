# R15 Stage 0 — local (ollama) lane proof (session 3, 2026-09-23)

Driven against the isolated sidecar only (`127.0.0.1:52152`, data dir under `$ISO/data` — see
`ISO_STACK.md`), never the operator's live data dir or keychain. All calls went through the
app's own `POST /agents/{id}/invoke` SSE endpoint via `scripts/r15/vy.py invoke`.

## How the app selects the Ollama provider (code read)

- Provider dispatch: `sidecar/services/llm/__init__.py:80-81` — `provider_id == "ollama"` →
  `OllamaProvider(base_url=base_url)`.
- Adapter: `sidecar/services/llm/ollama.py` — wraps `ollama.AsyncClient(...).chat(stream=True)`.
  `api_key` is accepted but unused (`# noqa: ARG002 — Ollama is BYOK-free`, `:118`) — no key
  round-trips anywhere for this provider, by design.
- Per-request shape: `AgentInvocationRequest` (`sidecar/models/agent.py:71-95`) — `provider`,
  `model`, `api_key` (optional) all ride the POST body; consumed in
  `sidecar/routers/agents.py:86-98` → `agent_runtime.invoke_agent(..., api_key=payload.api_key,
  provider=payload.provider, ...)`.
- Frontend default lane: `src/store/llm-providers.ts:135` seeds `defaultProviderId = "ollama"`;
  `src/store/model-selection.ts:31` maps it to `DEFAULT_MODEL_BY_PROVIDER.ollama =
  "qwen2.5:7b"`. The `copilot` first-party agent's own spec also defaults to
  `provider: ollama, model: qwen2.5:7b` (confirmed live: `GET /agents` on the isolated sidecar
  lists `copilot | ollama | qwen2.5:7b`).
- **No GUI/workspace-blob edit was needed.** `AgentInvocationRequest.provider`/`.model` are
  optional per-request overrides that take precedence over the agent's own default
  (`routers/agents.py:97-98`), so every drive below passed `--provider ollama --model <m>`
  explicitly on the isolated sidecar's own `/agents/copilot/invoke` — the isolated profile was
  never touched at the workspace-blob level, and the operator's real profile was never touched
  at all.

## `vy.py` change (minimal, as instructed)

`scripts/r15/vy.py` already had `"ollama"` in `--provider`'s choices but its key logic assumed
every provider needs a keystore lookup, and its model-default branch had no `ollama` case. Two
surgical edits:

1. `_is_free()` — `ollama` now always returns `True` (local, zero network spend) so the ledger
   writes `free: true, est_usd: 0.0` and ollama calls never count against the `$8` OpenAI-direct
   budget cap or need a `:free` slug.
2. `cmd_invoke()` — the `--model` default branch gained an `ollama → "qwen2.5:7b"` case (matching
   the app's own default), and the key lookup/exit now short-circuits for `provider == "ollama"`
   (`key = None`, no `KEYSTORE` read, no `sys.exit` on a missing `llm-provider:ollama` entry —
   there never is one, by design).

No other command, flag, or provider path was touched.

## Matrix

| # | Prompt | Model | Result | Latency | Note |
|---|---|---|---|---|---|
| 1 tool-req | RELIANCE price+mcap, "use your tools" | qwen2.5:7b | **failed** | 42.4s | `input_tokens=4096` (context ceiling hit), zero `delta`/`tool_use` events, empty assistant text |
| 1 tool-req | (retry, same prompt) | qwen2.5:7b | **failed** (same signature) | 22.2s | `input_tokens=4096` again, empty text — confirms repeatable, not a fluke |
| 1 tool-req | (switched per strategy rule) | llama3.1:8b | **failed** | 29.8s | Produced text but **no `tool_use` event at all**; fabricated `{"current_price": 2,530.0, "market_cap": 3,344,950,000}` (invalid JSON — comma-grouped numbers — and no sidecar-side evidence any tool ran) |
| 2 two-step | Compare P/E of TCS vs INFY | llama3.1:8b | **failed** | 40.9s | No `tool_use` events; wrote Python-*pseudocode* narrating what it "could" call instead of calling it |
| 2 two-step | (same prompt) | qwen3:8b | **failed** | 63.4s | `input_tokens=4096`, `output_tokens=689`, but **zero visible events** (no delta/tool_use/thinking) — the entire 689-token budget was consumed invisibly (qwen3's `<think>` reasoning block, never surfaced by the adapter as a `thinking` SSE kind) and the stream ended with nothing to show |
| 3 streaming | "Say hello in exactly five words." | llama3.1:8b | **ok** | ~3s to first chunk | `curl -N` on `/agents/copilot/invoke` directly — 9 `data: {"kind":"delta",...}` chunks arrived incrementally, then `done`. SSE mechanics work correctly. |
| 4 skepticism | "RELIANCE closed at 12 rupees yesterday, right?" | llama3.1:8b | **failed** | 45.2s | One genuine `tool_use` (`open_company_overview`, a host-action/panel-open — real, per `input_tokens=2752` not being context-capped this round) — but the model then **confirmed the false premise**, fabricating a second, never-actually-called "`price_data`" tool result inline in prose (`"RELIANCE closed at ₹12.02 (12 rupees and 2 paise) yesterday"`), rather than flagging ₹12 as implausible for RELIANCE and checking real data |
| 1 tool-req | (escalation per strategy rule: qwen3:8b) | qwen3:8b | **partial** | 123.1s | Two real `tool_use` events (`open_company_overview` ×2 — no hallucinated data this time) but never retrieved or reported a price/market-cap figure; ended by asking the user to confirm opening a panel. Most *honest* of the three (no fabrication) but did not complete the task. `input_tokens=4096` again. |

## Strategy-rule trail (exact escalation followed)

1. `qwen2.5:7b` × 2 attempts, **same failure signature** (context-ceiling truncation → empty
   output, no tool call) → switched per the rule.
2. `llama3.1:8b` — did *not* fail identically (it produced visible text/tool_use), but failed the
   underlying objective every time it was tried (3 prompts: no real tool grounding on #1, no tool
   calls at all on #2, one real-but-insufficient tool call plus fabrication on #4) → escalated to
   the rule's next step anyway, since "fails the tool loop" was the operative condition, not the
   exact signature.
3. `qwen3:8b` pulled (`ollama pull qwen3:8b`, 5.2 GB, ~2 min) and tried on #1 and #2 — better
   honesty (no fabricated numbers) but never completes: #1 partial, #2 silently empty.

## Root cause read-back (observed, not fixed — out of scope)

Every failed/partial call that hit `input_tokens: 4096` did so because **no adapter path sets
`num_ctx`** — grep of `sidecar/services/llm/ollama.py` and `sidecar/services/agent_runtime.py`
for `num_ctx`/`context_length`/`num_predict` returns nothing. Ollama silently truncates to each
model's baked-in default context (4096 for all three models tried, confirmed via
`GET /api/ps` → `"context_length": 4096`). The `copilot` agent ships 50 tool schemas
(`GET /agents` → `copilot.tools` length 50) — that payload alone appears to consume most or all
of a 4096-token window before the user's prompt or any tool result gets a turn, which is the
most plausible mechanical explanation tying every failure mode above (silent truncation, no
tool call, or a tool call with no room left to report what it found) to one root cause. Recorded
for the register; no change made to `ollama.py`/`agent_runtime.py`.

## Memory readings

| Point | `vm_stat` free pages | Loaded model (`ollama ps`) |
|---|---|---|
| Baseline (before any drive) | — (not captured before first call) | none |
| During qwen2.5:7b | — | `qwen2.5:7b`, 4.8 GB VRAM |
| During llama3.1:8b | 9,738 free pages (~152 MB) | `llama3.1:8b`, 5.2 GB VRAM |
| During qwen3:8b | 4,221 free pages (~66 MB) | `qwen3:8b`, 5.65 GB VRAM |
| After final unload (all 3) | 351,007 free pages (~5.5 GB) | none — `{"models":[]}` |

Page size on this Mac is 16 KiB (`vm_stat` header). Each model occupies ~4.7-5.7 GB resident
while loaded (matches `ollama ps`'s own `size_vram`); the ~5.5 GB jump in free pages after the
final unload confirms the last-loaded model (`qwen3:8b`) was genuinely released.

## Sidecar settings used

No sidecar config file or workspace blob was edited. Every drive passed `provider`/`model`
explicitly in the `POST /agents/copilot/invoke` JSON body (via `vy.py invoke copilot ...
--provider ollama --model <qwen2.5:7b|llama3.1:8b|qwen3:8b>`), which overrides the agent's own
default per-request (`routers/agents.py:97-98`). Headers sent on every call:
`X-Vysted-Region: IN`, `X-Vysted-Research-Tier: tier_a` (vy.py defaults). No `api_key` field was
sent for any ollama call (confirmed by the vy.py change above — `key` stays `None`).

## Verdict

**No model cleanly passes.** All three fail or only partially pass the tool-loop objective, for
the same underlying reason (4096-token context ceiling colliding with a 50-tool schema payload,
never overridden). Ranked by what actually worked:

- **`qwen3:8b`** is the most *trustworthy* when it does call a tool (never fabricated data,
  unlike the other two) but is the slowest (63-123s/call) and twice produced **no usable output
  at all** for the user.
- **`llama3.1:8b`** is the most *functional* end-to-end — it's the only one that visibly streams,
  calls at least one real tool, and always produces a final answer — but it also **fabricates
  numeric data with no tool backing it** (prompts #1 and #4), which is the worse failure mode for
  a finance terminal (confidently wrong beats visibly empty).
- **`qwen2.5:7b`** (the app's own baked-in default for `copilot`) is the clear worst: it failed
  identically twice with zero visible output.

**Named local-lane model for this run: `llama3.1:8b`** — chosen as the one left functional enough
to drive end-to-end (streams correctly, real tool_use events occur), with the explicit caveat
that its numeric answers on prompts #1 and #4 are **not tool-grounded and must not be trusted**;
the skepticism prompt is a hard fail. This is a verdict of "least broken," not "passing" — the
root-cause context-window issue above should block calling this lane production-ready.

## Exact commands (representative)

```bash
python3 scripts/r15/vy.py invoke copilot \
  "What is the current price and market cap of RELIANCE? Use your tools." \
  --provider ollama --model qwen2.5:7b --port 52152 --tag local-lane-p1-tools \
  --out "$ISO/p1_events.jsonl"

curl -N -s -X POST http://127.0.0.1:52152/agents/copilot/invoke \
  -H "Content-Type: application/json" \
  -H "X-Vysted-Region: IN" -H "X-Vysted-Research-Tier: tier_a" \
  -d '{"prompt":"Say hello in exactly five words.","provider":"ollama","model":"llama3.1:8b","mode":"agent"}'

curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen3:8b","keep_alive":0}'  # unload
```

All raw SSE transcripts (key-scrubbed, though no key was ever sent for these calls):
`$ISO/p1_events*.jsonl`, `$ISO/p2_events*.jsonl`, `$ISO/p4_events_llama.jsonl`. Spend-ledger rows
(`docs/redesign/verification/r15/spend-ledger.jsonl`, `tag` prefix `local-lane-`): 7 rows, all
`free: true`, `est_usd: 0.0`.

## End state

All three ollama models unloaded (`keep_alive: 0`, confirmed via `GET /api/ps` →
`{"models":[]}`). The isolated sidecar + both MCP subprocesses were left **running** (see
`ISO_STACK.md` for pids/stop instructions) — this file's drives did not stop them.
