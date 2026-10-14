# Vysted R16 "Easy Install" (0.10.0) — run state

Acknowledged 02:02 IST Thu 15 Oct 2026: R16 brief accepted as the mandate; beginning with the approval pass.

## Header

- **Brief (verbatim, git-ignored):** `docs/redesign/verification/R16_BRIEF.md`
- **Run state (this file):** `docs/redesign/verification/vysted-r16-run-state.md`
- **Evidence root:** `docs/redesign/verification/r16/` (machine-local, git-ignored: `r16/local/`)
- **Decisions:** `docs/redesign/DECISIONS_FOR_OPERATOR.md` (section 0 is the operator's step list)
- **Run report:** `docs/redesign/verification/R16_RUN_REPORT.md` (written at the end)
- **Branch:** `005-r16-easy-install` off `main` @ `f0ce9bed` (v0.9.0 merge = `6e1b52b9`)
- **Fallback tag:** `v0.9.0`
- **Stage:** 0 closing (chain #3 running at bef864a9) + wave 1 writers in flight (workflow wf_13581ecc-d2f)
- **Gates that hold:** Stage 0 (chain green at bef864a9: vitest 2062/2062, pytest 4014 passed 1 skipped, cargo green; production build launches) (r16-rc1: items 1+2; r16-rc2: items 3+4 + chain + CI 9/9 + Gate 8; v0.10.0: GUI round + docs + final review)
- **Claude Code:** 2.1.300
- **Lead:** Opus 5.5 high. Routing per brief (Opus 5.5 medium risk-adjacent writers, Sonnet 5.5 high other code, Haiku 5.5 low/medium volume, never code/certify; Opus 5.5 medium certifier). The brief's Haiku volume tier overrides CLAUDE.md's "never Haiku workers" for this run by explicit operator instruction.
- **Next action:** read wave-1 reports; integrate branches r16-w-{release,updater,llama-bundle,engine,models,profile} into 005-r16-easy-install (lead reads every diff); one ci-local on the merge; tag v0.10.0-beta.1 for the CI release pipeline.

## Resume prompt (paste into a fresh session)

```
Resume Vysted R16 "Easy Install". Read docs/redesign/verification/R16_BRIEF.md (the mandate) and
this run-state header in docs/redesign/verification/vysted-r16-run-state.md, then reconcile:
git status, git worktree list, git branch, newest tag, running vysted/llama processes. Continue
from "Next action". Operator is away unless they say otherwise.
```

## Approval pass (02:05–02:45 IST 15 Oct)

GRANTED: caffeinate (run-scoped, `caffeinate -dimsu`, pid in `r16/local/caffeinate.pid`) · git push to scratch branch `r16-scratch-approval` · computer-use (Vysted, Vysted Terminal [click tier, by bundle id], Finder, System Settings) · rig-equivalent window capture (venv python Quartz, 2560x1664) + harmless pointer event · packaged-app launch (fresh 0.9.0 production build, HOME-isolated) · MCP: github get_me, Notion get-self, Gmail list_labels, Claude Docs guide, tauri-mcp status (not_running), claude-in-chrome tabs_context (no group), playwright tabs list · one subagent (Haiku, Explore) · one single-agent workflow (Haiku, wf_545ca6a4-aff).
NOT RUN: Spotify (tool is restricted to explicit playback questions; no run path needs it) · context7/Drive/etc. (authenticate-only, unauthenticated).
DENIED: none. Rig proper (`rig.py capture/click`) is presence-gated (900 s idle + sentinel) and cannot run with the operator at the keyboard by design; it runs unattended from here.
Sleep: Amphetamine (since 23 Sep) prevents display + system sleep; run caffeinate added; pmset sleep 1/displaysleep 10 are overridden by both assertions; screensaver idleTime unset (no screensaver); screenLock delay 300 s only applies after display sleep/screensaver, which Amphetamine blocks (same setup held 88 min unattended on 4 Oct).
Sentinel armed until 2026-10-15T11:11:54+00:00 (operator away from 02:45 IST).

## Log

- 02:31 IST Stage 0 production build at f0ce9bed: `pnpm tauri build` exit 0 in 5m47s (dmg 239 MB). Cold launch from a fresh HOME: window paints at once; openbb-mcp bound at ~39 s; main sidecar /health at 81.8 s; sec-edgar bound 81.9 s. FINDINGS: (1) terms dialog and onboarding did NOT appear on the fresh profile, because the terms ack lives in the shared OS keychain service "vysted-terminal" -> wave-1 profile writer; (2) toolbar chip stayed "CONNECTING..." 10 min after /health was up (to check in the GUI round); (3) default provider is Ollama qwen2.5:7b, "not running" for a stranger.
- 02:45 IST Updater key: the Phase 0 private key was never stored (no copy on this Mac). New minisign keypair, key id 89FF38F7524553ED: private `~/.tauri/vysted-updater.key` (0600), backup `~/.tauri/backup/`, Actions secret TAURI_SIGNING_PRIVATE_KEY (no password); pubkey in tauri.conf.json (d1f22c7b).
- Stage 0 chain #1 (f0ce9bed): 1 pytest failure, test_search_exports read sidecar/.venv/site-packages/test/__init__.py (a RAR header) installed by smartapi-python 1.5.5, a broker SDK left in the LOCAL venv from before D81 (not in requirements). Uninstalled it from the local venv (environment fix, no test change). Chain #2 failed on prettier for the lead's CONTRACT.md; fixed in bef864a9.
- llama.cpp pin: release v0.6.0 = build b11429; assets verified by GitHub asset digests. Windows build decision (evidence: package contents): win-vulkan-x64 ships ggml-vulkan.dll + 16 ggml-cpu-<arch>.dll variants loaded dynamically, so it runs on any GPU vendor with a Vulkan driver and falls back to CPU without one; CUDA builds are 150-420 MB and NVIDIA-only. To be measured on the ROG.
- Stage 0 chain #3 at bef864a9: EXIT 0 in 6m24s; vitest 170 files / 2062 tests; pytest 4014 passed, 1 skipped; cargo test green; lint, format, typecheck, fmt, clippy green. Stage 0 PASSES.
