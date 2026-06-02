# Recon — A12:citation-validate

I now have the complete map. The default search tier is `native`, OpenRouter is NOT in `SUPPORTS_NATIVE_SEARCH`, the streaming adapter never captures `annotations`, and there is no citation field on any LLM event. This means OpenRouter currently takes the BYOK/local `web_search` tool path, NOT native. Here is the blueprint.

---

# Blueprint: Live-validate native-citation emission (Track 6 #5)

## (1) Findings — file:line precise

**Normalizers exist, fully unit-tested, ZERO production consumers.** `sidecar/services/llm/native_search.py:140-253` defines `normalize_anthropic/openai/gemini/xai` → `{url,title,excerpt}`. Tested at `sidecar/tests/test_native_search.py` (18 tests, fake payloads only). A grep for these names outside the def/test/`__all__` returns **nothing** — no adapter, router, or research module ever calls them. The adapters only _inject_ the search affordance (request side); nobody _parses_ the response citations.

**The streaming OpenAI adapter discards citations.** `openai.py:204-243` iterates `stream` reading only `delta.content` and `delta.tool_calls`. OpenAI/OpenRouter web-search `annotations` arrive on `choices[0].delta.annotations` (streaming) or `message.annotations`; **none are read**. No `LLM*Event` (`models/llm.py:120-180`) carries a citation/sources field, so even a captured annotation has no wire frame.

**OpenRouter is NOT a native-search provider.** `native_search.py:49` `SUPPORTS_NATIVE_SEARCH = {anthropic, openai, gemini, groq, xai}` — `openrouter` absent. `agent_runtime.py:532-538`: native dispatch only fires `provider_id in SUPPORTS_NATIVE_SEARCH`. So an OpenRouter turn (default tier `native`, `config.py:96`) keeps the BYOK/local `web_search` **tool** (`agent_tools/web_search.py`), which needs an Exa/SearXNG key and is unrelated to native annotations. **OpenRouter never exercises `normalize_openai`.** Adapter's `web_search` branch (`openai.py:171-178`) only injects the tool for `provider_id=="openai"`, never `"openrouter"`.

**OpenRouter's actual native-search mechanism** is the **`:online` model suffix** (or `plugins:[{id:"web"}]`), which returns OpenAI-shaped `annotations` of `type:"url_citation"` on the message — exactly what `normalize_openai` parses. This is OpenRouter's own web plugin, billed per-result.

**Key availability — CONFIRMED.** Keychain service `vysted-terminal` (`src-tauri/src/keychain.rs:16`), account `llm-provider:openrouter` (`src/lib/keychain.ts:28`). Probe (presence only, no secret read): **`PRESENT: llm-provider:openrouter`** and `llm-provider:deepseek`; all direct providers absent. Renderer reads it via `getSecret` and sends header `X-LLM-Key` (`model-catalog.ts:95`); the sidecar never touches the keychain.

**Brief surface.** `types/brief.ts:16-28` `BriefSource{url,title,excerpt,domain?}` — field-identical to the normalizer output. `BriefPanel.tsx` renders `sources` with `[n]` chips. Research already populates `sources` from `web_search` tool `citations` (`research/deep.py:204-217`, `fast.py:250`), **not** from native annotations.

## (2) Exact change plan

The cheapest validation does **not** require wiring the full UI path. It validates the **normalizer against a real provider payload**. Two scopes — lead picks based on appetite:

**Scope A (minimal, recommended — pure parser proof, ~$0):**

- **Create** `sidecar/tests/test_native_search_live.py` — a `@pytest.mark.live` (or `skipif` on env) test that:
  1. Reads the key NOT from keychain (sidecar can't) but from an env var the lead exports for the run: `OPENROUTER_LIVE_KEY` (lead pipes the keychain value in; test never logs it).
  2. Calls OpenRouter chat-completions **non-streaming** directly: `openai.AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)`, `model="google/gemini-2.5-flash-lite:online"` (cheapest tool+web capable; `:online` forces the web plugin), `messages=[{"role":"user","content":"What is the latest SEC filing date for Apple? Cite sources."}]`, `max_tokens=200`, `extra_body={"plugins":[{"id":"web","max_results":2}]}`.
  3. Extracts `resp.choices[0].message.annotations`, feeds to `normalize_openai`, asserts `len(out)>=1` and every record has a non-empty `url` starting `http`.
- This proves the **real OpenRouter annotation shape matches `normalize_openai`** — the only thing never validated. Cost: one ~250-token call + 2 web results ≈ **<$0.001**.

**Scope B (also wire the runtime — if lead wants OpenRouter native to actually work):**

- **Edit `native_search.py:49`** — add `"openrouter"` to `SUPPORTS_NATIVE_SEARCH`. (Touches a normalizer-module constant, NOT a Tier-1 locked file.)
- **Edit `openai.py:171-178`** — add an `elif self._provider_id == "openrouter":` branch setting `request_kwargs["extra_body"]["plugins"]=[{"id":"web","max_results":_n}]` (merge with the existing `provider` extra_body at `:186-193`).
- **Edit `openai.py:204-243`** — capture `getattr(delta,"annotations",None)`; accumulate; after stream-end call `normalize_openai` and yield them. **Requires a new event** — add `LLMCitationsEvent(sources: list[dict])` to `models/llm.py:~180` and the SSE encoder in `routers/llm.py:_encode_event`. Then `agent_runtime` folds it into research `sources`.
- Scope B is a real feature, multi-file, contract-touching (new event type) — **out of scope for a "minimal live validation."** Recommend Scope A now; file Scope B as follow-up.

## (3) Risks + safe fallback

| Risk                                                                              | Fallback                                                                                                                                                                      |
| --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Key absent on lead's machine                                                      | It is present (probed). If a CI box lacks it → test `skipif(not os.getenv("OPENROUTER_LIVE_KEY"))`; documented as manual step.                                                |
| OpenRouter changes annotation shape / returns objects nested under `url_citation` | `normalize_openai` already handles both flat & nested (`native_search.py:187-189`); test asserts on output, not raw shape.                                                    |
| Chosen model dropped or no longer `:online`-capable                               | Fallback model list: `openai/gpt-4o-mini:online`, `perplexity/sonar` (always cited). Test parametrizes; first that returns annotations wins.                                  |
| Spend creep                                                                       | `max_tokens=200`, `max_results=2`, single call, no streaming loop. Hard ceiling ~$0.001.                                                                                      |
| Secret leakage                                                                    | Key only via env var for the run; test asserts `key not in repr(resp)`; never `print`. Lead exports inline, `unset` after.                                                    |
| Touching Tier-1                                                                   | Scope A touches only a new test file. Scope B touches non-locked adapter/model files (verify `models/llm.py` & `native_search.py` are NOT in the locked list — they are not). |

## (4) Verification — exact steps

**Live parser proof (Scope A):**

```bash
# Lead exports the keychain value inline (value never printed):
export OPENROUTER_LIVE_KEY="$(security find-generic-password -s vysted-terminal -a llm-provider:openrouter -w)"
cd sidecar && python -m pytest tests/test_native_search_live.py -m live -x -q
unset OPENROUTER_LIVE_KEY
```

Pass = assertions hold (≥1 normalized source with http url).

**Raw-shape sanity (one curl, confirms `:online` emits `url_citation`):**

```bash
curl -s https://openrouter.ai/api/v1/chat/completions \
 -H "Authorization: Bearer $OPENROUTER_LIVE_KEY" \
 -H "HTTP-Referer: https://vysted.app" -H "X-Title: Vysted Terminal" \
 -d '{"model":"google/gemini-2.5-flash-lite:online","max_tokens":200,
      "plugins":[{"id":"web","max_results":2}],
      "messages":[{"role":"user","content":"Apple latest 10-K filing date? Cite."}]}' \
 | python -c 'import sys,json;d=json.load(sys.stdin);print(json.dumps(d["choices"][0]["message"].get("annotations","NONE"),indent=2))'
```

Confirms `annotations[].type=="url_citation"` with `url`/`title` before trusting `normalize_openai`.

**Regression (unchanged unit suite must stay green):**

```bash
cd sidecar && python -m pytest tests/test_native_search.py -q
```

**If Scope B taken**, add: `pytest tests/test_llm_openai.py tests/test_native_search.py -q`, `ruff format --check sidecar && ruff check sidecar`, and `pnpm typecheck` (new event type crosses `types/llm` if mirrored). No rig/vitest needed for Scope A.

**In short:**

- The 5 normalizers are dead code in production — nothing parses provider citation payloads off the response; only the BYOK `web_search` _tool_ feeds `sources` today.
- A live OpenRouter key IS present (`vysted-terminal/llm-provider:openrouter`); the cheapest validation is one non-streaming `:online` call (~$0.001) asserting `normalize_openai` produces ≥1 http source.
- Minimal scope = new `test_native_search_live.py` only (no Tier-1, no contract change). Actually wiring OpenRouter-native into the runtime/UI is a separate multi-file feature (new `LLMCitationsEvent`).
- Confidence: 8/10 — uncertain only whether OpenRouter currently nests citations under `message.annotations` vs `delta.annotations` in streaming; the recommended non-streaming probe sidesteps that and the curl step de-risks it before any code lands.

Key files: `sidecar/services/llm/native_search.py:49,140-253`; `sidecar/services/llm/openai.py:171-178,204-243`; `sidecar/services/agent_runtime.py:524-538`; `sidecar/models/llm.py:120-180`; `sidecar/tests/test_native_search.py`; `types/brief.ts:16-28`; `src/lib/keychain.ts:28`; `src/store/model-catalog.ts:95`; `src-tauri/src/keychain.rs:16`.
