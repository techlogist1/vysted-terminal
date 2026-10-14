# final-drive-research-briefs log

Head under test d38b5d1a. Own sidecar 127.0.0.1:52841 from final-cand/sidecar source, data dir
scratchpad/final-data-final-drive-research-briefs (cp -R of final-seed-data). launcher 62125,
sleep pid 62127 (kill this), worker 62128. Evidence: docs/redesign/verification/r15/surface/research-briefs/final/.

- 15:53 DECISION (harness cause, not product): scripts/r15/vy.py:310 refuses non-GET calls outside
  ports 52100-52399, so the assigned :52841 cannot take agent turns (first two runs refused before any
  request; no spend). Same resolution as final-adv-maintainer/investor: stopped :52841 (killed sleep
  62127, confirmed down) and rebooted my own source sidecar on in-range :52344, same data dir, MCP
  52801/52802. sleep pid 62834 (kill this), launcher 62832, worker 62835. All writes/agent turns -> :52344.
- 15:58 search/status + searxng/status on shared :52800 -> 04/05 files; searxng state degraded with per-engine reasons (RESEARCH-028 holds).
- 15:59 direct code repros (06-direct-code-repros.txt): RESEARCH-002/004 hold; 007 blocked_tier4 shape holds (tier 3);
  LEAD-060 (open) still reproduces (attach); RESEARCH-043 (blocked_tier4) still reproduces in code (attach-only).
- 03-ultra (gpt-4o-mini, prompt 'Research Data Patterns (India) for me: order book, margins and valuation.', depth ultra):
  model answered from price/fundamentals/financial_statements, never called research -> no brief. One sample, model routing.
  03b re-run with census-style prompt -> research(depth=ultra) Heavy mode.
- 01 (llama, depth slider normal): model passed depth='deep' explicitly (documented: explicit model depth wins).
- 16:06 03b: after 2 of 4 sequential ULTRA runs published (~590s, ~$0.32 each), stopped my client by pid (vy.py 64055, child of turn.py 64050) to cap shared spend; checking the sidecar cancels the in-flight 3rd run (AGENT-002).

- 16:16 IST: filed drive-research-briefs:4 (cold FAST briefs empty, fundamentals 9-16 s vs 6 s box, panel silent; price half attached to LEAD-128). KL row against LEAD-030 (Sonata market cap). ATTACHED: LEAD-060, RESEARCH-043, LEAD-128, AGENT-027. NEEDS_GUI: favicon onError, export. Drive table written: drives/research-briefs.md.
- 16:16 IST: stopped own sidecar :52344 (kill 62834, my recorded pid); :52841 already down. No lock held. Nothing committed.
