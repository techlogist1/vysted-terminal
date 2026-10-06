# R7 Lead integration checklist (running)

- [ ] ChatSidebar: replace local `activeAgentId` useState with `useActiveAgentStore` (after track C merges) so palette agent switching takes effect; lens chip shows display name.
- [ ] Sidecar: honor `options.research_depth` (normal|deep|ultra) from the invocation body as the default research depth (after track R lands the depth router); frontend sends it from the composer depth slider (track C).
- [ ] Wire track D's disclosures router into app.py + roster-count test bumps per INTEGRATION_NOTES_R7.md files in each worktree.
- [ ] Track briefs' INTEGRATION*NOTES*\*.md: apply catalog.py entries (hack track run_custom_backtest; data track corporate_announcements/shareholding_pattern).
- [ ] Workspace blob migration: purge legacy duplicate Chart panels + stale "screener" (bare id) panels from saved layouts on load.
- [ ] Announcements/disclosures UI surface (equity-overview tab or section) after D merges.
- [ ] catalog.py: add `open_company_overview` host-action Capability (symbol, highlight?) — frontend fully wired (host-actions + equity-command store); panel-side highlight consumption (scroll + one peach pulse on the named metric row — live-agent-activity accent role) lands in EquityOverviewPanel AFTER track P merges; then add the tool id to copilot's allow-list + read-gate panel allow-list; roster-count tests bump.
- [ ] Palette ticker rows: also offer "add to watchlist" secondary action (nice-to-have).

## Integration sequence (planned ~when tracks land)

1. Merge r7-chart (PASSED adversarial review). Live-eyeball toolbar; consider `▾` → ASCII per review note.
2. Merge r7-chat → wire useActiveAgentStore into ChatSidebar (replace local state); lens display-name; verify stop/queue/depth live.
3. Merge r7-hack → apply its INTEGRATION_NOTES (catalog: transform.code parity handler note, run_custom_backtest, save_workflow MCP).
4. Merge r7-panels (disjoint sweep).
5. Merge r7-research then r7-data (sidecar) → wire disclosures router into app.py; catalog entries (corporate_announcements, shareholding_pattern, open_company_overview, run_custom_backtest); roster-test bumps; agent_runtime honors options.research_depth as the research default; rebuild binary; smoke test; full pytest.
6. Lead UI on top: Settings search-tier section (T1 status w/ per-engine cooldowns from /search/status; T2 SearXNG guided one-click flow vs its state machine; T3 engine pick Firecrawl/Exa + sonar lane), equity-overview Disclosures section, highlight-metric pulse.
7. A/B harness (5 finance queries lane A sonar-deep-research vs lane B our loop+hosted) through the app with the operator's OpenRouter key via the rig; record verdict in DECISIONS.md; set shipped default.
8. Full gates + binary + acceptance cases + adversarial defect hunt + release-bundle computer-use pass.
