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
      className={`text-body -mb-px flex items-center gap-2 border-b-2 px-3 py-2 transition-colors ${
        active
          ? "text-charcoal-100 border-amber-400"
          : "text-charcoal-400 hover:text-charcoal-200 border-transparent"
      }`}
    >
      {children}
      <span className="bg-charcoal-800 text-charcoal-300 text-micro rounded-control px-1 py-0.5 font-mono">
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
      <div className="border-charcoal-800 bg-charcoal-925/60 flex shrink-0 items-center gap-2 border-b px-3 py-2">
        <Search
          className={"text-charcoal-500 size-3.5" /* tokens-ok: 14px icon - R9 s3 toolbar rung */}
          aria-hidden
        />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by key…"
          aria-label="Filter settings by key"
          data-testid="tradesa-settings-search"
          className="text-charcoal-200 placeholder:text-charcoal-600 text-body flex-1 bg-transparent focus:outline-none"
        />
        <span className="text-charcoal-500 text-micro">
          {filtered.length} / {rows.length}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div
          data-testid="tradesa-settings-empty"
          className="text-charcoal-500 text-body flex flex-1 items-center justify-center p-6"
        >
          {rows.length === 0 ? "No settings loaded yet." : "No keys match your filter."}
        </div>
      ) : (
        <div className="overflow-auto">
          <table className="text-body w-full">
            <thead className="bg-charcoal-950 sticky top-0 z-10">
              <tr className="border-charcoal-800 text-charcoal-500 text-micro border-b text-left font-medium tracking-wide uppercase">
                <th className="px-3 py-1">Key</th>
                <th className="px-3 py-1">Value</th>
                <th className="px-3 py-1">Description</th>
                <th className="px-3 py-1 text-right">Updated</th>
                <th className="px-3 py-1">Changed by</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr
                  key={row.key}
                  data-testid="tradesa-settings-row"
                  className="border-charcoal-900/50 hover:bg-charcoal-900/40 border-b transition-colors"
                >
                  <td className="text-charcoal-300 text-micro px-3 py-1 font-mono">{row.key}</td>
                  <td className="text-charcoal-100 text-micro px-3 py-1 font-mono">{row.value}</td>
                  <td className="text-charcoal-400 text-caption px-3 py-1">
                    {row.description ?? "—"}
                  </td>
                  <td className="text-charcoal-400 text-caption px-3 py-1 text-right">
                    {formatRelativeIso(row.updated_at)}
                  </td>
                  <td className="text-charcoal-400 text-caption px-3 py-1">
                    {row.changed_by ?? "—"}
                  </td>
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
        className="text-charcoal-500 text-body flex flex-1 items-center justify-center p-6"
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
          className="border-charcoal-800 bg-charcoal-900/40 rounded-none border p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <span className="text-charcoal-300 text-micro font-mono">{drift.key}</span>
            <span className="text-charcoal-500 text-micro ml-auto">
              {formatRelativeIso(drift.changed_at)} by{" "}
              <span className="text-charcoal-400">{drift.changed_by ?? "system"}</span>
            </span>
          </header>
          <div className="text-caption mt-2 flex flex-wrap items-center gap-2">
            <span className="bg-charcoal-950 text-charcoal-500 rounded-control px-2 py-1 font-mono line-through">
              {drift.previous_value ?? <em>unset</em>}
            </span>
            <ArrowRight className="text-charcoal-500 size-3" aria-hidden />
            <span className="bg-charcoal-950 text-positive rounded-control px-2 py-1 font-mono">
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
        className="border-charcoal-800 bg-charcoal-925/60 flex shrink-0 border-b px-2"
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
