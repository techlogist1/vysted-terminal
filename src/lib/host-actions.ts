/**
 * Host actions — the agent's cockpit-driving mutations, and how the diff/accept
 * gate stages, describes, and applies them (FR-002 act-path, FR-010, FR-011).
 *
 * The catalog tags four capabilities `kind="host_action", read_only=false`:
 * `open_panel`, `set_chart_symbol`, `add_to_watchlist`, `propose_order`. The
 * agent emits them as `tool_use` events; instead of applying immediately, the
 * chat surface stages each as a `ProposedChange` (see `store/proposed-changes`),
 * and these helpers do the work:
 *   - `describeHostAction` — read the live stores to build the old→new diff.
 *   - `applyHostAction`     — apply a non-order mutation on accept.
 *   - `routeOrderProposal`  — route an accepted order through the §6.5
 *                              propose→confirm path (the AI never places).
 */

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useBrokersStore } from "@/store/brokers";
import { useChartSyncBus } from "@/store/chart-sync";
import { useOrdersStore } from "@/store/orders";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

import type { BrokerId, BrokerOrderProposal } from "../../types/broker";
import type { ProposedChangeKind } from "../../types/proposed-change";

/** The four catalog host-action tool ids (`kind="host_action"`, `read_only=false`). */
export const HOST_ACTION_NAMES = new Set([
  "open_panel",
  "set_chart_symbol",
  "add_to_watchlist",
  "propose_order",
]);

/** A host-action mutation the diff gate must intercept rather than auto-apply. */
export function isHostActionMutation(name: string): boolean {
  return HOST_ACTION_NAMES.has(name);
}

function str(input: Record<string, unknown>, key: string): string {
  const v = input[key];
  return typeof v === "string" ? v : "";
}

function num(input: Record<string, unknown>, key: string): number {
  const v = input[key];
  return typeof v === "number" ? v : Number(v ?? 0);
}

/** Human-friendly panel label from a panel id. */
function panelLabel(id: string): string {
  return id.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Describe a host-action mutation as a reviewable old→new diff. Reads the live
 * stores so the "before" reflects the real current cockpit state.
 */
export function describeHostAction(
  name: string,
  input: Record<string, unknown>,
): { kind: ProposedChangeKind; title: string; before: string; after: string } {
  const symbol = str(input, "symbol");
  switch (name) {
    case "set_chart_symbol": {
      const current = useChartSyncBus.getState().symbol?.symbol ?? "—";
      const tf = str(input, "timeframe");
      return {
        kind: "chart",
        title: `Load ${symbol || "symbol"} into the chart`,
        before: `Chart symbol: ${current}`,
        after: `Chart symbol: ${symbol}${tf ? ` · ${tf}` : ""}`,
      };
    }
    case "open_panel": {
      const panel = str(input, "panel");
      return {
        kind: "panel",
        title: `Open the ${panelLabel(panel)} panel`,
        before: `${panelLabel(panel)} panel: not open`,
        after: `${panelLabel(panel)} panel: open`,
      };
    }
    case "add_to_watchlist": {
      const entries = useSymbolsStore.getState().entries;
      const already = entries.some((e) => e.symbol.toUpperCase() === symbol.toUpperCase());
      return {
        kind: "watchlist",
        title: `Add ${symbol} to your watchlist`,
        before: `Watchlist: ${entries.length} symbol${entries.length === 1 ? "" : "s"}`,
        after: already
          ? `Watchlist: ${symbol} already tracked`
          : `Watchlist: +${symbol} (${entries.length + 1} total)`,
      };
    }
    case "propose_order": {
      const side = str(input, "side");
      const qty = num(input, "quantity");
      const type = str(input, "order_type") || "market";
      const limit = input.limit_price;
      return {
        kind: "order",
        title: `${side ? side.toUpperCase() : "ORDER"} ${qty || ""} ${symbol}`
          .replace(/\s+/g, " ")
          .trim(),
        before: "No order placed",
        after: `${side} ${qty} ${symbol} (${type}${typeof limit === "number" ? ` @ ${limit}` : ""}) — routes to the confirm-before-place dialog`,
      };
    }
    default:
      return { kind: "panel", title: name.replace(/_/g, " "), before: "—", after: "—" };
  }
}

/**
 * Apply a non-order host-action mutation to the live stores. Returns a short
 * label, or `null` if it couldn't apply. Orders are NOT applied here — they
 * route through `routeOrderProposal` → the §6.5 dialog.
 */
export function applyHostAction(name: string, input: Record<string, unknown>): string | null {
  const symbol = str(input, "symbol");
  switch (name) {
    case "set_chart_symbol":
      if (symbol) {
        useChartSyncBus.getState().setSymbol("copilot", symbol);
        return `Loaded ${symbol} into the chart`;
      }
      return null;
    case "open_panel": {
      const panel = str(input, "panel");
      if (panel) {
        useWorkspaceStore.getState().openPanel(panel);
        return `Opened ${panelLabel(panel)}`;
      }
      return null;
    }
    case "add_to_watchlist":
      if (symbol) {
        const assetClass = input.asset_class === "crypto" ? "crypto" : "equity";
        useSymbolsStore.getState().addSymbol(symbol, assetClass);
        return `Added ${symbol} to your watchlist`;
      }
      return null;
    default:
      return null;
  }
}

/**
 * Resolve which broker an AI-proposed order targets: an explicit `broker` arg if
 * the model gave one, else the user's currently-connected broker, else `kite`
 * (the reference broker). This avoids blindly routing every order to kite when
 * the user has a different broker connected (the §6.5 dialog still shows the
 * broker and gates placement regardless).
 */
function resolveTargetBroker(input: Record<string, unknown>): BrokerId {
  if (typeof input.broker === "string" && input.broker) {
    return input.broker as BrokerId;
  }
  const connected = useBrokersStore
    .getState()
    .brokers()
    .find((b) => b.status === "connected");
  return (connected?.broker ?? "kite") as BrokerId;
}

/**
 * Route an agent-proposed order through the existing §6.5 propose→confirm path
 * (FR-011). POSTs `/brokers/{broker}/orders` with `source="ai-agent"`, then opens
 * the `OrderConfirmationDialog`. The AI NEVER reaches `confirm_and_place` — the
 * dialog's explicit "I reviewed" + Confirm is the only path to placement.
 */
export async function routeOrderProposal(
  input: Record<string, unknown>,
  meta: { agentId?: string; agentName?: string },
): Promise<{ ok: boolean; error?: string }> {
  const broker = resolveTargetBroker(input);
  const symbol = str(input, "symbol");
  const side = str(input, "side");
  const type = str(input, "order_type") || "market";
  const quantity = num(input, "quantity");
  const limitPrice = typeof input.limit_price === "number" ? input.limit_price : undefined;
  try {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/brokers/${encodeURIComponent(broker)}/orders`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          side,
          type,
          quantity,
          limitPrice,
          source: "ai-agent",
          sourceDetails: { agentId: meta.agentId, agentName: meta.agentName },
        }),
      },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail !== undefined) {
          detail = body.detail;
        }
      } catch {
        // ignore non-JSON body
      }
      return { ok: false, error: detail };
    }
    const proposal = (await response.json()) as BrokerOrderProposal;
    useOrdersStore.getState().addProposal(proposal);
    useOrdersStore.getState().openProposal(proposal.proposalId);
    return { ok: true };
  } catch (err: unknown) {
    return { ok: false, error: err instanceof Error ? err.message : "Order proposal failed" };
  }
}
