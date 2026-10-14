# rc1-battery-15 (gate round 6-rc2) at ace7dd76
Sidecar :52355 on copy of seed data (sleep pid 99289, stopped at end). Sets 2, 3, 99, 129, 82, 138 done; 24 ids, all raw files from this run. 17 holds, 7 ci_pinned (frontend vitest-only repros: workspace.test.ts), 0 regressed. Findings: [].
Notes: vy.py has no groq provider (deepseek substituted for LEAD-043). Live gpt-4o-mini research runs of RESEARCH-001/003/004/029 replaced by in-process replicas on the same code (original BDL feed, original r3-ultra-kaynes markdown). Ollama lock taken once (RESEARCH-010), released by trap.
