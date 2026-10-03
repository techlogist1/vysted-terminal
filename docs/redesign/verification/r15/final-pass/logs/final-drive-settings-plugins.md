# final-drive-settings-plugins — working log

- Head under test d38b5d1a (final-cand worktree, read-only). Own sidecar :52845 from final-cand/sidecar source,
  data dir scratchpad/final-data-final-drive-settings-plugins (cp -R final-seed-data), MCP pair :52801/:52802 (shared).
  sh pid 84449, SLEEP pid 84451 (stop target), worker 84452. Log scratchpad/fdsp/sidecar.log.
- Baseline: rc1 drive (r15/rc1/drives/settings-plugins.md) + census EVIDENCE.md/COVERAGE.json.
- Group code delta 4c6dfe8c..d38b5d1a: llm.py (validate humanize, AGENT-019), system.py (rig-hook gate, LIFECYCLE-033),
  KeyEntryDialog (store-unavailable, CROSS-PLATFORM-011), PluginManagerPanel + SettingsPanel (openPanel('marketplace'),
  contributesNothing always-on, layout maxLength 200, palette chord hint), marketplace store remove deletes grants
  (PLATFORM-049), settings store setAll applyDefaultAgent (FRONTEND-030), workspace.ts (UI-070 etc).
- harness: census shim returned a bare port; get_sidecar_port now returns {port,state,reason} (LIFECYCLE-010), so the shim was updated (harness change, not a product defect).
- 16:44-16:46 HTTP probes A-F against :52845 (the first detached loop also completed; its files kept as final/run1-*). Fake keys all rejected; layouts 200-byte rule with reason; plugin toggle round-trips; NewsAPI fake key -> unauthorized; trip/reset 404.
- 16:45 SearXNG status: cli_present true, daemon_running false -> UI copy "Docker not found / install Docker" (code-proven, SettingsPanel.tsx:841,967; no frontend reads the docker flags) -> new_defect medium. By 16:50 Docker was up (degraded, engines CAPTCHA-blocked) and the harness rendered the degraded card honestly.
- 16:50-16:53 jsdom harness: settings 9/9, plugins 3/3, modules 1/1 (after fixing the fake dockview addPanel return). Replays copied to surface/settings-plugins/final/05-harness-*.
- Attached: R15-LEAD-089 (import fontSize-only toast), R15-LEAD-068 (privacy copy). No regressions. NEEDS_GUI entry appended (layout save/load, export download, real keychain write, nav scroll).
- Sidecar stopped: killed sleep pid 84451; :52845 no longer answers; worker 84452 gone.
