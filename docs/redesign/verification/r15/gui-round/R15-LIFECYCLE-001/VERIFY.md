# GUI verify — R15-LIFECYCLE-001 at d38b5d1 (d38b5d1a2487bd52fe8a7e741a3a5266e3206611)

- verifier: fresh Opus 5.5 context (gui-verify-R15-LIFECYCLE-001). No GUI, no app launch.
- inputs: register entry (title, repro, fix_shape, note), DRIVE.md (Round 3 section judged; 9368c62/ace7dd7 sections are prior rounds), the d38b5d1-* captures, raw/d38b5d1-boot-timeline-{check1,launchC}.txt, raw/d38b5d1-app-stdout-excerpts.txt, CAPTURES.jsonl, presence.log, code at d38b5d1 (src-tauri/src/lib.rs, src-tauri/src/sec_edgar_mcp.rs, src/lib/sidecar-client.ts).
- registration: all 12 d38b5d1 PNGs hash-match a CAPTURES.jsonl row (tool `scripts/rig/rig.py capture`, window_owner "Vysted Terminal"), and each has a presence.log line before it (lines 92, 93, 95, 97, 98; idle 909-4038 s, load recorded). Unregistered: none. Every capture opened and judged here.
- environment: warm launches only (no reboot); the entry's repro names a cold launch after a reboot. Machine otherwise idle (load 1.5-4.7, the three --onefile extractions).

## Per part (the note's four GUI checks)

| Check | Evidence | What it shows | Ruling |
|---|---|---|---|
| 1. window paints and takes input while both MCP children bind; no beachball | d38b5d1-01 (+3.9 s), -02 (+6.6 s), -03 (+9.8 s), -04 (+12.1 s); timeline-check1 l.7 (all three children at t=2.5 s, listen=-) | 01 painted window, chip CONNECTING…, terms modal; 02 modal gone after the click; 03 command palette open from the toolbar click; 04 palette closed after escape. First MCP bind is at t=63 s, so all input landed during the bind window. | SHOWN (warm launch only) |
| 2. data engine answers /health before the MCP binds finish | timeline-check1 l.215 (health=200 at t=107.47 s; openbb listen 59639 earlier); timeline-launchC l.196 (health=200 at t=98.51 s); stdout excerpts (openbb healthy, sec-edgar killed after 45 s x 2, main "healthy" after attempt 2/6) | Main sidecar spawned at +1.5-2.5 s with the MCP children (original serial spawn gone), but /health came AFTER the openbb bind (63 s / 49 s) and after the sec-edgar budget expired, on 2/2 idle launches. | NOT SHOWN — the opposite order, on an idle machine |
| 3. renamed vysted-sidecar: chip red and panels name "The data engine could not start (...)" at once | d38b5d1-20 (+3.8 s), -21 (+14.9 s); stdout "could not start (No such file or directory (os error 2))" | Chip "SIDECAR ERROR — THE DATA ENGINE COULD NOT START (NO SUCH FILE OR DIRECTORY (OS ERROR 2))." at +3.8 s. Panels show only their own generic copy ("Could not refresh quotes", "Could not load the news feed" with its sub-line clipped, "This portfolio is empty"); no panel body carries the named reason. | Chip SHOWN; panel half NOT SHOWN |
| 4. kill running sidecar: chip "Sidecar error", panels and chat say "The data engine stopped (exit code ...)" | d38b5d1-30 (healthy, CONNECTED, populated), -31 (+4 s), -32 (+37 s), -33 (chat), -34 (portfolio); stdout "The data engine stopped (signal 15)." | 31 chip generic "NOT RESPONDING — IT MAY HAVE STOPPED"; 32 chip settled "SIDECAR ERROR — THE DATA ENGINE STOPPED (SIGNAL 15)."; 33 chat says "Ollama (local) isn't ready: The data engine is not responding — it may have stopped. Restart Vysted."; 34 Portfolio says "Couldn't refresh live quotes — values shown without market data." Neither panel nor chat names the termination reason. Code agrees: sidecar-client.ts caches the base URL after ready, a request to the dead port becomes SIDECAR_UNREACHABLE; only the chip listens to vysted://sidecar-terminated (lib.rs:442). | Chip SHOWN; panels and chat show the DEFECT (generic copy, captures 33, 34) |

## Claim (title + fix_shape)

- Frozen main loop for the bind window: absent (check 1), warm launch only.
- "Data sidecar is not even spawned until both MCP binds return": absent — spawned at +1.5-2.5 s (timelines).
- fix_shape "a late MCP bind attaches instead of being lost": not exercised. Raw stdout shows the sec-edgar child still killed after 45 s x 2 with "/sec routes will 501" on both launches — the repro's last sentence ("a child that overruns is killed ... lost for the session") is still the logged behaviour; whether it would have bound later is not shown.
- Lead note (R15-LEAD-123, adjacent): a 107 s / 98 s main-sidecar bind now reaches CONNECTED and populates the seeded layout (d38b5d1-05, -30). Holds.

## Verdict: not_certified

Captures d38b5d1-33 and d38b5d1-34 show the chat and Portfolio after a sidecar death with generic "not responding" / "Couldn't refresh live quotes" copy, not the "The data engine stopped (...)" text the note's check 4 requires; check 3's panel half likewise carries no reason; and check 2 shows /health after the MCP binds on 2/2 idle launches. Checks 1 and the spawn-order headline hold (warm only).
