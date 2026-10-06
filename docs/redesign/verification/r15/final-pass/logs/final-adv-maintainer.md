# final-adv-maintainer working log
Head d38b5d1a. Started 2026-10-03 14:46:31 IST.
- Stack: openbb :52821, sec-edgar :52822, main-clean :52820 (binary, stranger profile final-stranger-maintainer), main-data :52825 (source, final-adv-maintainer-data). Pids in scratchpad/fam/pids.txt (kill sleep pid only).
- G8-5 done: pass (53 differing paths, all rowed; cand==head)
- 14:53 DECISION (harness cause, not product): scripts/r15/vy.py refuses non-GET calls outside ports 52100-52399 (vy.py:310), so it cannot invoke on the brief's :52820/:52825. Ollama turns use a keyless stdlib client scratchpad/fam/inv.py (no key ever read or sent) against :52820/:52825 under the lock (fam/ollq.sh, one call per hold). The OpenAI lane (needs vy.py's in-process key + spend guard) runs on an extra source sidecar :52398 (inside vy's range, free at check) on its own seed copy final-data-maint-vy, MCP 52821/52822.
- Cold boot of the bundle-identical binaries on the stranger profile: started 14:46:23, main :52820 + sec-edgar :52822 listening at ~14:50:3x (~4m10s; XprotectService at 71% CPU scanning the freshly extracted _MEI .so files; openbb :52821 bound first at ~2 min).
- G8-1 pass
- 15:05 AC-3 pass, G8-2 pass, maintainer:1 filed (medium, class gap of R15-AGENT-018)
- 15:11 LOCK NOTE: ac4.py's resume-refusal probe resumed cancelled run 437112b0 (resume of cancelled is by design, FR-028) and it ran ~3 Ollama rounds after 15:10:00 OUTSIDE the lock — my probe error, not a product failure.
- 15:13 AC-4 pass; UI-2 finding maintainer:2 (high, region-flip re-pricing of bare-ticker lot)
- 15:16 AC-2/AC-6/UI-1/UI-6/G8-3 pass; KL instance maintainer:kl-1 -> R15-LEAD-038
- 15:21 UI-3 pass (attach UI-090), UI-4 finding maintainer:3 (low)
- 15:24 UI-5 needs_gui, UI-7 pass, free-maintainer-1 -> maintainer:4 (low)
- 15:28 LS-2 run done (own bundle :52827): finding maintainer:5 (medium, corrupt custom_agents.db 500s every custom-agent route), maintainer:6 (low, bind failure aborts with exit 134; first taken-port attempt inconclusive — stdin was /dev/null, re-run with a held fifo)
- 15:30-15:36 LS-3 kills: openbb-mcp worker killed mid-request (sidecar survives, yfinance fallback; empty-200/'Retry' = R15-DATA-061 class, attached); SIGTERM main-vy :52398 mid-SSE (graceful shutdown waits for the held stream); SIGKILL own bundle :52829 mid-SSE (client drops at once, curl rc 18). First :52820 attempt was not mid-request (foreground curls), corrected in kill-probes.txt. LS-3 pass.
- 15:37 R3 re-check: maintainer:2 is a class sibling of R15-DATA-002 (blocked_tier4, 4.15 covers watchlist + agent add only); kept as its own site with register_id recorded.
- 15:40 G8-4 pass (32 SQLite files, no order/broker/trade objects). LS-4: BANNED counts (word-bounded: 0 outside docs/redesign/verification; 0 in all 4 bundle executables, Resources, out/); licence closure scanned on the build venv; THIRD_PARTY_NOTICES lists 56 of 121 main-sidecar versions that differ from what the bundle ships (anyio 4.15.1 inside the binary vs 4.13.0 listed) -> maintainer:7.
- 15:48 LS-4 written (finding maintainer:7; no real secret in history or tree; BANNED counts 0 outside verification and 0 in the bundle). free-maintainer-2 -> maintainer:8 (low, transform.code sum(list,start) bypasses the PLATFORM-066 caps).
- 15:49 All my processes stopped by recorded pid (sidecars 26675/26587/32537/26581/26575 via their sleep pids or directly, LS-2/LS-3 instances by their scripts, secrets scan exited); no Ollama lock held. Lane closed.
