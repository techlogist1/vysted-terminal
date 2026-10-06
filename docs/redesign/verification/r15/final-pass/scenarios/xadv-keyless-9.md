# xadv-keyless-9 — first-launch window flow for a keyless stranger (terms, welcome, skip, banner, first chat send)

Needs a real window (the terms dialog, the one-time welcome dialog, the banner and the chat status line render only in the webview; the GUI redrive owns the screen and COMMON forbids GUI here). Per R5 this is operator-attended; steps in docs/redesign/verification/r15/final-pass/xadv-keyless-NEEDS_GUI.md.

What the source at d38b5d1a says should happen (for the attended run to compare against):
- Welcome (OnboardingFlow.tsx:230-262): "It already works — no key, no account. Live quotes, charts, news and screeners run right now. Pick a path below to turn on the AI agent (and its web research), or explore first." Two cards: "Connect a model" (OpenRouter) / "Run it locally" ("...it still reaches out for market data and web searches, but the model itself is yours").
- Skip -> DoneStep (:690): "You're exploring keyless — data, charts, news and screeners all work. Add a model anytime from Settings to turn on the agent and its web research."
- Banner (OnboardingBanner.tsx): shown while no key and the keyless default answered not-ready.
- First chat send with no Ollama installed: status line "Ollama (local) isn't ready: Ollama is not running. Start Ollama (open the app or run `ollama serve`), then try again." and the setup is NOT opened (keyless:2, xadv-keyless-4).

VERDICT xadv-keyless-9: needs_gui
