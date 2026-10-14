# UI-7 — fresh GUI verification at 1fddb2b (close-verify-UI-7)

- verifier: Opus 5.5, fresh context; inputs limited to the check, `UI-7/DRIVE.md`, `UI-7/*.png`, `UI-7/raw/*`, `CAPTURES.jsonl`, `presence.log`, and code at `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056`.
- verdict: **partial**

## Evidence admissibility

All eight PNGs under `UI-7/` were re-hashed (`shasum -a 256`); every hash matches a `CAPTURES.jsonl` row (lines 274-281) with tool `scripts/rig/rig.py capture` and window_owner `Vysted Terminal`. Presence lines precede them: `12:44:23Z [UI-7 pre-capture-01]` (idle 1008.5 s, sentinel 12:57:00Z) before 01 at 12:44:24Z; `12:44:53Z [UI-7 pre-batch-01]` (idle 1038.4 s) before 02-08 at 12:44:56-12:45:13Z. `raw/rig-01.log` and `raw/rig-02.log` repeat the same hashes, EXIT=0, 21/21 steps ok. Unregistered captures: none. Each capture was opened and judged directly.

## Per part

### 1. Fresh profile, terms with no keys
- Evidence: `1fddb2b-01-terms-boot.png`.
- Shows: "Welcome to Vysted / Please review the terms before you start" modal: not investment advice, no brokerage connection / cannot place, route or simulate orders, data may be delayed, AI can be wrong, PolyForm Strict 1.0.0 or commercial license; button "I understand — continue". Header CONNECTING…; behind the modal an empty Chat 1.
- Ruling: **holds**. The fresh-profile setup itself (empty data dir + `{"secrets": {}}` keystore) is attested only by the driver's text, not by a capture or raw file. The first-launch terms modal appearing is consistent with a fresh profile.

### 2. Onboarding walked with no keys (capture each step)
- Evidence: `02-onboarding-welcome`, `03-onboarding-local`, `04-local-tab-focus`, `05-back-to-welcome`, `06-cockpit-composer`.
- Shows: 02 WELCOME "An agent-native finance terminal", green "It already works — no key, no account", cards "Add a key →" / "Set up local AI →", "Skip — I'll explore first →". 03 "Run a local model": "Apple M1 Pro · 16 GB RAM · Apple Silicon", `qwen3:8b` "runs locally · ~7.8 GB", "fits with headroom (7.8 GiB of 10.6 GiB GPU budget)", button "✓ Use qwen3:8b". 04 same step, focus ring on the Back arrow. 05 Back returns to WELCOME. 06 Skip dismisses onboarding to the cockpit.
- Ruling: **holds for the steps driven; partially not driven**. Not captured: the Cloud ("Add a key") step and the Done step (reached only via "Use qwen3:8b"). Also, because the onboarding status route is hard-coded to :11434 (below), the Local step showed the operator's real daemon as running, so the Local step's Ollama-unreachable state ("Download Ollama" guidance, `OnboardingFlow.tsx:574-599`) was not seen.

### 3. Composer lands on the keyless local (Ollama) lane
- Evidence: `1fddb2b-07-model-picker.png` (and 06 for the composer).
- Shows: picker open from the composer chip; PROVIDER list with "Ollama (local)" highlighted as the selected row; MODEL list with `qwen2.5:7b` highlighted. No key was entered at any point.
- Ruling: **holds**.

### 4. Ollama unreachable -> keyless CTA, not an error
- Evidence: `06-cockpit-composer`, `08-final`; `raw/validate-ollama.json` = `{"ok":false,"reason":"unreachable","detail":"Ollama is not running. ..."}`; `raw/vysted-log-excerpt.txt` 12:44:49Z "validation transport error: Failed to connect to Ollama".
- Shows: the down lane was really down for this app (`OLLAMA_HOST=http://127.0.0.1:9`; the code honours it: `sidecar/services/llm/ollama.py:144` `ollama.AsyncClient(host=self._base_url)` with `base_url=None`). The chat empty state is the normal "Ask anything about what you're viewing" + TRY THIS + "Mode Agent · lens Vysted Copilot"; no error text anywhere. The keyless CTA is the app banner directly above the chat: "Add a cloud provider key — or run a local model (Ollama) — to unlock the assistant ... Set up a provider →", plus the header chip "OLLAMA (LOCAL) · NOT RUNNING — SET UP IN SETTINGS".
- Ruling: **holds, with a note**: the CTA is in the banner/chip above the chat, not inside the chat empty state; there is no error. A send on the down lane was not driven, so the in-chat reaction to a send is unverified.

## Driver findings

1. **Keyless readiness chip/banner can stick on "NOT RUNNING" after a slow sidecar boot**: **not confirmed** (plausible, medium if real). Code at the sha supports the mechanism: `useKeylessReadiness` (`src/lib/provider-validation.ts:153-182`) skips the probe on a `sidecarStatus` change while a failed result is still within the 30 s TTL, and has no timer to re-render when that TTL expires. `validateProvider` returns `reason: "unreachable"` when the sidecar itself cannot be reached, and the chip renders any not-ok keyless result as Ollama not running. Capture 01 shows "OLLAMA (LOCAL) · NOT RUNNING" while the header still says CONNECTING…, which is consistent with that. `app-stdout.log` holds only one `POST /llm/keys/validate` in the 82 s after the sidecar bound, and the driver says that one was its own curl. But in this run Ollama really was unreachable for the app, so every chip state captured here is correct. The wrong-chip-with-daemon-up case the driver cites lives in other items' files, which this verification is not allowed to read.
2. **Onboarding Local step and chat lane resolve the Ollama endpoint differently**: **confirmed, low**. `sidecar/routers/system.py:28` `_OLLAMA_URL = "http://127.0.0.1:11434"` (the `/system/ollama/status` route, hit at 12:44:57Z per the log). The UI sends `/llm/models?...base_url=http://127.0.0.1:11434` (log 12:44:30Z). Readiness and chat use `AsyncClient(host=None)`, which honours `OLLAMA_HOST`. Capture 03 shows "✓ Use qwen3:8b", which `OnboardingFlow.tsx:604` renders only when `ollama.running && installed`, while the same frame's header says NOT RUNNING. It needs a non-default `OLLAMA_HOST`, so it hits few users.

## Missed defects

None beyond the above. The CONNECTING-state "NOT RUNNING" label in 01 (a sidecar-unreachable result shown as an Ollama fault) is folded into finding 1.
