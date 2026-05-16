/**
 * Tradesa V2 wrapper — Settings & Drift panel.
 *
 * Two tabs:
 *   "Current Settings" — searchable table of every bot_settings row.
 *   "Drift" — diffs vs the last snapshot the plugin saw (previous → current).
 *
 * Polls both surfaces every 60 seconds. The first drift refresh seeds
 * the baseline; subsequent refreshes show any deltas.
 *
 * Read-only display per v0.6.5 contract — the plugin never POSTs to
 * `/tradesa-v2/settings`.
 */

"use client";

import { useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";

import { POLL_CADENCE_MS, arrayOrEmpty, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import { formatRelativeIso, useInterval } from "./_utils";

import type { TradesaBotSetting, TradesaSettingsDrift } from "../../../types/tradesa_v2";

type TabKey = "current" | "drift";

function TabButton({
  active,
  count,
  onClick,
  children,
  testId,
}: {
  active: boolean;
  count: number;
  onClick: () => void;
  children: React.ReactNode;
  testId: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      aria-pressed={active}
      className={`-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm transition-colors ${
        active
          ? "border-blue-500 text-zinc-100"
          : "border-transparent text-zinc-400 hover:text-zinc-200"
      }`}
    >
      {children}
      <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-300">
        {count}
      </span>
    </button>
  );
}

function CurrentSettingsTable({ rows }: { rows: readonly TradesaBotSetting[] }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => row.key.toLowerCase().includes(q));
  }, [rows, query]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-2 border-b border-zinc-800 bg-zinc-950/60 px-3 py-2">
        <Search className="size-3.5 text-zinc-500" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by key…"
          aria-label="Filter settings by key"
          data-testid="tradesa-settings-search"
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none"
        />
        <span className="text-[10px] text-zinc-500">
          {filtered.length} / {rows.length}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div
          data-testid="tradesa-settings-empty"
          className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
        >
          {rows.length === 0 ? "No settings loaded yet." : "No keys match your filter."}
        </div>
      ) : (
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-zinc-950">
              <tr className="border-b border-zinc-800 text-left text-[11px] font-medium tracking-wide text-zinc-500 uppercase">
                <th className="px-3 py-2">Key</th>
                <th className="px-3 py-2">Value</th>
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2 text-right">Updated</th>
                <th className="px-3 py-2">Changed by</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr
                  key={row.key}
                  data-testid="tradesa-settings-row"
                  className="border-b border-zinc-900/50 transition-colors hover:bg-zinc-900/40"
                >
                  <td className="px-3 py-2 font-mono text-[11px] text-zinc-300">{row.key}</td>
                  <td className="px-3 py-2 font-mono text-[11px] text-zinc-100">{row.value}</td>
                  <td className="px-3 py-2 text-xs text-zinc-400">{row.description ?? "—"}</td>
                  <td className="px-3 py-2 text-right text-xs text-zinc-400">
                    {formatRelativeIso(row.updated_at)}
                  </td>
                  <td className="px-3 py-2 text-xs text-zinc-400">{row.changed_by ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function DriftList({ rows }: { rows: readonly TradesaSettingsDrift[] }) {
  if (rows.length === 0) {
    return (
      <div
        data-testid="tradesa-drift-empty"
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
      >
        No drift detected since last refresh.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col gap-2 overflow-auto p-3">
      {rows.map((drift) => (
        <article
          key={`${drift.key}-${drift.changed_at}`}
          data-testid="tradesa-drift-row"
          className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-zinc-300">{drift.key}</span>
            <span className="ml-auto text-[10px] text-zinc-500">
              {formatRelativeIso(drift.changed_at)} by{" "}
              <span className="text-zinc-400">{drift.changed_by ?? "system"}</span>
            </span>
          </header>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded bg-zinc-950 px-2 py-1 font-mono text-zinc-500 line-through">
              {drift.previous_value ?? <em>unset</em>}
            </span>
            <ArrowRight className="size-3.5 text-zinc-500" aria-hidden />
            <span className="rounded bg-zinc-950 px-2 py-1 font-mono text-emerald-300">
              {drift.current_value}
            </span>
          </div>
        </article>
      ))}
    </div>
  );
}

export function SettingsPanel() {
  const settingsState = useTradesaStore((s) => s.settings);
  const driftState = useTradesaStore((s) => s.settingsDrift);
  const refreshSettings = useTradesaStore((s) => s.refreshSettings);
  const refreshSettingsDrift = useTradesaStore((s) => s.refreshSettingsDrift);
  const [tab, setTab] = useState<TabKey>("current");

  useInterval(() => {
    void refreshSettings();
  }, POLL_CADENCE_MS.settings);

  useInterval(() => {
    void refreshSettingsDrift();
  }, POLL_CADENCE_MS.settings);

  const rows = arrayOrEmpty(settingsState.data);
  const drift = arrayOrEmpty(driftState.data);

  return (
    <PanelShell title="Settings & Drift">
      <nav
        role="tablist"
        aria-label="Settings tabs"
        className="flex shrink-0 border-b border-zinc-800 bg-zinc-950/60 px-2"
      >
        <TabButton
          active={tab === "current"}
          onClick={() => setTab("current")}
          count={rows.length}
          testId="tradesa-tab-current"
        >
          Current
        </TabButton>
        <TabButton
          active={tab === "drift"}
          onClick={() => setTab("drift")}
          count={drift.length}
          testId="tradesa-tab-drift"
        >
          Drift
        </TabButton>
      </nav>
      {tab === "current" ? <CurrentSettingsTable rows={rows} /> : <DriftList rows={drift} />}
    </PanelShell>
  );
}

export default SettingsPanel;
