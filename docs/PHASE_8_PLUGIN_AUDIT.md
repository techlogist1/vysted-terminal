# Phase 8 Plugin Audit — T4 (plugin contract + runtime)

**Date:** 2026-05-18
**Baseline:** v0.7.0 (commit 947d297)
**Auditor:** Sonnet 4.6 (teammate t4-plugin)
**Branch:** worktree-agent-t4-plugin

## Severity scheme

| Level | Meaning |
|-------|---------|
| S1 | Tier-1 contract violation; runtime crash on plugin load; malformed manifest accepted silently |
| S2 | Plugin imports from host-private surface (`src/lib/`, `src/store/`, `src/components/`); React warnings on mount; hot-reload state loss |
| S3 | Companion-module wiring gap; manifest validation accepts malformed-but-non-load-bearing field |
| S4 | Cosmetic |

## Scope

Plugins audited:
- `plugins/example/`
- `plugins/openbb-mcp/`
- `plugins/tradesa-v2/`
- `plugins/brokers/alpaca/`
- `plugins/brokers/angelone/`
- `plugins/brokers/ccxt-exec/`
- `plugins/brokers/dhan/`
- `plugins/brokers/ib/`
- `plugins/brokers/kite/`
- `plugins/brokers/oanda/`

Key files read:
- `types/plugin.ts` (Tier-1 locked contract)
- `src/lib/plugin-bootstrap.ts` (BUNDLED_PLUGINS + PLUGIN_COMPANIONS)
- `src/lib/plugin-runtime.ts` (PluginRuntime supervisor)
- `types/plugin-runtime.ts` (PluginManifest, LoadedPlugin)

---

## Part A — Plugin contract usage (grep audit)

<!-- SKELETON — full findings below -->

---

## Part B — Plugin runtime verification

<!-- SKELETON — full findings below -->

---

## Special attention — tradesa-v2 3-layer read-only invariants

<!-- SKELETON — full findings below -->

---

## Summary

<!-- SKELETON — filled after all parts complete -->
