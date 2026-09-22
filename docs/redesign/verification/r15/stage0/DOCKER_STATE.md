# Docker/OrbStack state — recorded BEFORE starting anything (R15 session 2, 2026-09-23 03:44 IST)

## orb status
Stopped

## docker info

failed to connect to the docker API at unix:///Users/lokavyasingh/.orbstack/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/lokavyasingh/.orbstack/run/docker.sock: connect: no such file or directory

## SearXNG :8888 / :8080
http://127.0.0.1:8888 -> 000
http://127.0.0.1:8080 -> 000

## What the app says with Docker down (sidecar-level, from the 19 Sep read-only probe of the operator live stack, live-app-readonly-probe.md)
- GET /search/status -> tier t1_keyless (ddg/brave/mojeek), research silently on the keyless scraper
- GET /search/searxng/status -> state not_installed_docker, detail "docker CLI found but the daemon is not running — start Docker/OrbStack"
- Whether the UI surfaces this is a census item (DECISIONS_FOR_OPERATOR 2.2); the UI-level Docker-down state is re-induced later at the app edge, never by stopping Docker again.

## Operator dev stack
- No Vysted processes or :52052-54 listeners at 03:44 — the 13 Sep stale stack is no longer running (nothing to stop).

## Ollama
NAME           ID              SIZE      MODIFIED     
qwen2.5:7b     845dbda0ea48    4.7 GB    3 months ago    
llama3.1:8b    46e0c10c039e    4.9 GB    3 months ago    
