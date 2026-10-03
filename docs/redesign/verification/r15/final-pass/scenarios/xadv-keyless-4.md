# xadv-keyless-4 — no key, no Ollama: what the agent surface says to a stranger

## Default lane for a stranger
`src/store/llm-providers.ts:90  defaultProviderId: "ollama",` — the keyless local lane is the default. `GET /llm/providers` (own stack) lists ollama `requires_key: False, default_base_url http://127.0.0.1:11434, default_model qwen2.5:7b`.

## Live probes (own stack :52900; "no Ollama installed" simulated per COMMON by a base URL on a closed local port 52909; no request reached :11434)
```
POST /llm/keys/validate {"provider":"ollama","api_key":null,"model":"llama3.1:8b","base_url":"http://127.0.0.1:52909"}
 -> {"ok":false,"reason":"unreachable","detail":"Ollama is not running. Start Ollama (open the app or run `ollama serve`), then try again."}
POST /llm/keys/validate {"provider":"openrouter","api_key":null}  -> {"ok":false,"reason":"not_configured","detail":"No API key is set for OpenRouter."}
POST /llm/keys/validate {"provider":"anthropic","api_key":null}   -> {"ok":false,"reason":"not_configured","detail":"No API key is set for Anthropic."}
GET /system/ollama/status -> {"running":true,...} on this box (the real daemon); the route returns {"running":false,...} on any exception (system.py:143-160) and its docstring says running:false "means the daemon is not installed / not started — the onboarding flow then shows install guidance".
```

## What the stranger sees (source at d38b5d1a)
- Before sending: `src/components/OnboardingBanner.tsx` shows (until dismissed) "Add a cloud provider key — or run a local model (Ollama) — to unlock the assistant, agents, and research tools..." with "Set up a provider →" (opens Settings) whenever no key exists and the keyless default answered not-ready. Good.
- On send with the default lane (`src/modules/chat/ChatSidebar.tsx` ~834-862): only `model_not_pulled` and `not_configured` open the guided setup; everything else sets the status line `${providerLabel} isn't ready: ${readiness.detail}`. The sidecar can never return `not_configured` for ollama (`routers/llm.py` validate_key: `not_configured` only when `info.requires_key and api_key is None`), so a NEVER-INSTALLED Ollama is `unreachable` and the stranger reads:
  "Ollama (local) isn't ready: Ollama is not running. Start Ollama (open the app or run `ollama serve`), then try again."
  — an instruction to open an app they do not have, with no install link, while the onboarding's local step already has the right state machine (`OnboardingFlow.tsx:574-599`: not-installed daemon -> "Download Ollama — ollama.com/download" / "brew install ollama" / "I've installed it — re-check →").
- The welcome dialog shows exactly once (durable marker), so a stranger who clicked "Skip — I'll explore first" reaches the chat with only the banner as a route (and it is dismissible).

## R3 duplicate check
- R15-UI-013 (fixed): split validation erased WHY; fix routes unreachable to a status line instead of "No AI model is set up yet". Its promise holds (a stopped sidecar no longer opens setup). This item is the residue its design left: "not installed" and "not running" are one reason. Not a regression; adjacent.
- R15-AGENT-027 (open, medium): humanize() picks next steps by HTTP status alone (429/400 cases). Different mechanism (no HTTP status here; a connect failure with no installed-vs-running distinction, and the chat's routing).
- R15-LEAD-103 (open, low): onboarding recommendation collapses sidecar failure to "Couldn't reach the local engine" — different surface.
Filed new, low (R2: the banner gives a route; the chat's next step is wrong for the most common keyless stranger: no Ollama installed).

VERDICT xadv-keyless-4: finding keyless:2
