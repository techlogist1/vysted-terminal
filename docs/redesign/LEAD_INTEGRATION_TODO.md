# R7 Lead integration checklist (running)

- [ ] ChatSidebar: replace local `activeAgentId` useState with `useActiveAgentStore` (after track C merges) so palette agent switching takes effect; lens chip shows display name.
- [ ] Sidecar: honor `options.research_depth` (normal|deep|ultra) from the invocation body as the default research depth (after track R lands the depth router); frontend sends it from the composer depth slider (track C).
- [ ] Wire track D's disclosures router into app.py + roster-count test bumps per INTEGRATION_NOTES_R7.md files in each worktree.
- [ ] Track briefs' INTEGRATION*NOTES*\*.md: apply catalog.py entries (hack track run_custom_backtest; data track corporate_announcements/shareholding_pattern).
- [ ] Workspace blob migration: purge legacy duplicate Chart panels + stale "screener" (bare id) panels from saved layouts on load.
- [ ] Announcements/disclosures UI surface (equity-overview tab or section) after D merges.
- [ ] Palette ticker rows: also offer "add to watchlist" secondary action (nice-to-have).
