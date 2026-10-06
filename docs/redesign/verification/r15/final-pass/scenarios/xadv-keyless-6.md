# xadv-keyless-6 — README / quickstart promises versus what a keyless stranger gets

README.md at d38b5d1a (unchanged at the current HEAD: `git diff d38b5d1a HEAD -- README.md` empty).

| README claim (line) | Reality at d38b5d1a | Verdict |
|---|---|---|
| :26-27 "a **Next.js static-export frontend**" | Vite 8 + React 19 (package.json `vite`; no next) | ATTACHED to R15-DOCS-003 (blocked_tier4; README.md is in its files) |
| :39-40 "13 first-party agents" | `GET /agents` on the clean profile -> 13 | holds |
| :41-42 "BYOK across 7 LLM providers (Anthropic, OpenAI, Gemini, Groq, Ollama, DeepSeek, xAI)" | `GET /llm/providers` -> 8: anthropic, openai, gemini, groq, ollama (requires_key False), deepseek, xai, **openrouter** — the provider the same README (:74-77) and the welcome dialog sell as THE one key is missing from the list, and Ollama is keyless, not BYOK | part of keyless:3 |
| :60-62 "Vysted works the moment you open it — no account, no key, no setup. Live quotes, charts, news, screeners, **and web research (keyless, via DuckDuckGo) all run out of the box**." | No keyless web-research surface exists: web search runs only inside an agent turn, which needs a model (Ollama installed or a key). The app's own copy was corrected for exactly this by R15-UI-052: OnboardingFlow.tsx:240-242 "Live quotes, charts, news and screeners run right now. Pick a path below to turn on the AI agent (and its web research)"; DoneStep :690 "Add a model anytime from Settings to turn on the agent and its web research"; OnboardingFlow.test.tsx:33-37 "the welcome step used to claim 'web research run[s] right now' with no key (no keyless web-research surface exists)". `grep '"/research\|"/search' src/lib/sidecar-client.ts` -> no direct research/search client. | **keyless:3** |
| :70-73 local model: "no key, no cost, **fully offline**" | The welcome card says the opposite (OnboardingFlow.tsx:260 "it still reaches out for market data and web searches, but the model itself is yours"); R15-UI-052 removed "fully private… offline" from the app for this reason. A keyless agent turn on this stack called `market_overview` and `research` (network tools) — xadv-keyless-5. | **keyless:3** (same mechanism as UI-052; also the LEAD-068 class) |
| :79-81 "your keys live in the OS keychain — they never touch disk" | Release builds: OS keychain. Debug builds use a 0600 dev-keystore.json (CLAUDE.md, keychain.rs); a downloaded release is the user's case, so holds for the README audience | holds (release path needs_gui to prove; not re-tested) |
| :87-90 "Grab the latest .dmg from the Releases page" | `gh api repos/techlogist1/vysted-terminal/releases --jq length` -> `0` (today, 15:2x IST) | ATTACHED to R15-RELEASE-002 (blocked_tier4; its repro names README.md:88-90) |
| :108-111 "a one-time ~30–90s warm-up" | 168 s cold on this contended box (xadv-keyless-1); not attributable here | not filed |

## R3
- R15-UI-052 (fixed, medium): "First-run copy makes false promises: 'web research runs right now' with no key ... and ... 'fully private… offline'". Files: OnboardingFlow.tsx, OnboardingBanner.tsx, ChatSidebar.tsx — README.md was never in scope, and the README repeats both promises verbatim in spirit. Same mechanism, uncovered surface -> new entry with note "README residue of R15-UI-052 (app copy fixed, README not)". Severity medium as UI-052 (the README is the first thing a stranger reads, and both promises are false for the no-key user).
- R15-LEAD-068 (open, medium): Settings privacy over-promise (SettingsPanel.tsx:122 "Nothing leaves this machine except calls you make to providers you configure" — still present at the sha). The README "fully offline" is the same over-promise class; recorded in keyless:3 and cross-referenced, not separately attached.

VERDICT xadv-keyless-6: finding keyless:3
