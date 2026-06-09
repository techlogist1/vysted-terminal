"use client";

import { ListX } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { formatPrice, formatUnit } from "@/lib/format";

import type { EarningsEstimateDetail } from "../../../types/earnings";

interface EstimateRow {
  /** Stable row id (labels repeat across the EPS / Revenue sections). */
  id: string;
  label: string;
  value: string | null;
}

/** Statement-table columns — label left, estimate right-aligned in its own
 *  numeric column (design law: never a key-value dump grid). */
const COLUMNS: DataColumn<EstimateRow>[] = [
  { key: "label", header: "Metric", tier: "secondary", width: "60%", format: (r) => r.label },
  { key: "value", header: "Estimate", numeric: true, width: "40%", format: (r) => r.value },
];

function eps(value: number | null, digits = 2): string | null {
  return value === null ? null : formatPrice(value, digits);
}

function revenue(value: number | null): string | null {
  return value === null ? null : formatUnit(value);
}

interface Props {
  estimate: EarningsEstimateDetail | null;
}

/**
 * Next-quarter estimate detail as a two-section statement table (EPS /
 * Revenue) on the shared DataTable — label left, value right-aligned tabular.
 * Missing upstream values render the shared null glyph; a missing detail
 * altogether renders the composed dense empty state.
 */
export function EpsEstimateGrid({ estimate }: Props) {
  if (!estimate) {
    return (
      <div data-testid="eps-estimate-grid-empty">
        <EmptyState
          dense
          icon={ListX}
          headline="No estimate detail"
          hint="The provider surfaced no consensus detail for this event."
        />
      </div>
    );
  }
  return (
    <div data-testid="eps-estimate-grid">
      <DataTable
        columns={COLUMNS}
        sections={[
          {
            label: "EPS",
            rows: [
              { id: "eps-mean", label: "Mean", value: eps(estimate.eps_estimate_mean) },
              { id: "eps-median", label: "Median", value: eps(estimate.eps_estimate_median) },
              { id: "eps-high", label: "High", value: eps(estimate.eps_estimate_high) },
              { id: "eps-low", label: "Low", value: eps(estimate.eps_estimate_low) },
              { id: "eps-stddev", label: "Std. dev.", value: eps(estimate.eps_estimate_stddev, 3) },
              {
                id: "eps-analysts",
                label: "Analysts",
                value: String(estimate.estimate_analyst_count),
              },
            ],
          },
          {
            label: "Revenue",
            rows: [
              { id: "rev-mean", label: "Mean", value: revenue(estimate.revenue_estimate_mean) },
              { id: "rev-high", label: "High", value: revenue(estimate.revenue_estimate_high) },
              { id: "rev-low", label: "Low", value: revenue(estimate.revenue_estimate_low) },
            ],
          },
        ]}
        rowKey={(row) => row.id}
      />
    </div>
  );
}
