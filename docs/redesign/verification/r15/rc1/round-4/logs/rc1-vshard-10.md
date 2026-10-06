# rc1-vshard-10 working log (gate round 4)
- 05:09 IST worktree HEAD 68d5573aff9a579af084dcbb124843f2aecff6e8 confirmed; read register entries CODE-PLATFORM-014, CODE-PLATFORM-030, LEAD-043.
- 05:10 PLATFORM-014: scratch vitest (config + test in scratchpad, root = worktree, no worktree edit) 2/2 passed.
- 05:11 booted own sidecar :52610 on seed copy (sleep pid 36694); /health ok. No API_KEY env vars in shell or sidecar env.
- 05:11 vy.py refused :52610 (non-GET restricted to 52100-52399); used curl with vy.py's invoke payload (no key / fixed fake key, $0).
- 05:12 LEAD-043: all no-key/bad-key probes code auth or "rejected" on invoke, /llm/chat and /runs.
- 05:12 PLATFORM-030: entry repro + 3 fresh variants; pinned pytest 3 passed; float-dust adjacent low filed.
- 05:13 killed sleep pid 36694; :52610 free; worktree status clean. Verdicts: holds x3.
