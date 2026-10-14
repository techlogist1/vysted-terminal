# final-docs log

Started Sat Oct  3 15:41:35 IST 2026. Head d38b5d1a. Read-only via git show at sha.
- (a) versions: all 0.9.0 incl. /health. PASS.
- (b) pnpm/node refs: 0 real misses. Runbook ci-local "verbatim" drift (low).
- (c) paths: 132 raw -> 25 after basename resolution -> 6 real mismatches (CURRENT_STATE x4 classes, README counts, RUNBOOK step 1).
- (d) SIDECAR_API: 0 doc-not-live, 91/111 live undocumented; CORS/macro/stub claims false. medium.
- (e) MCP: 39 live, 14 undocumented, 0 doc-not-live. low. Protocol-version drift lib.rs vs mcp_server (low).
- (f) src: 0 offers. Docs: R12 hand-testing guide order showcase (medium, docs).
- (g) banned: 0 whole-word in scope; 1 substring false positive; repo-wide hits only in docs/redesign/verification.
- (h) SAFETY_ARCHITECTURE §2 matches AUTO_APPLIED_KINDS at sha. No finding.
- (i) CLAUDE.md notes: Tongyi probe section stale; "12 node types" vs 24.
- Wrote DOCS_VS_REALITY.md and findings/docs.json (9 findings).
