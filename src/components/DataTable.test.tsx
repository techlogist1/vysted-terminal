import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DataTable, type DataColumn } from "./DataTable";

interface Row {
  symbol: string;
  price: number | null;
}

const columns: DataColumn<Row>[] = [
  { key: "symbol", header: "Symbol", tier: "primary", sortable: true },
  {
    key: "price",
    header: "Price",
    numeric: true,
    sortable: true,
    format: (r) => (r.price === null ? null : r.price.toFixed(2)),
  },
];

const rows: Row[] = [
  { symbol: "AAPL", price: 189.5 },
  { symbol: "MSFT", price: null },
];

describe("DataTable", () => {
  it("renders headers and primary cell values", () => {
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.symbol} />);
    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("189.50")).toBeInTheDocument();
  });

  it("renders the null glyph for a missing value", () => {
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.symbol} />);
    // MSFT row's price is null → em-dash.
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("right-aligns + applies tabular-nums to numeric cells", () => {
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.symbol} />);
    const cell = screen.getByText("189.50");
    expect(cell.className).toContain("text-right");
    expect(cell.className).toContain("tabular-nums");
  });

  it("fires onSort and marks aria-sort on the active sortable header", () => {
    const onSort = vi.fn();
    render(
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.symbol}
        sort={{ key: "price", direction: "desc" }}
        onSort={onSort}
      />,
    );
    const header = screen.getByText("Price").closest("th")!;
    expect(header.getAttribute("aria-sort")).toBe("descending");
    fireEvent.click(header);
    expect(onSort).toHaveBeenCalledWith("price");
  });

  it("renders grouped section header rows", () => {
    render(
      <DataTable
        columns={columns}
        sections={[{ label: "Valuation", rows }]}
        rowKey={(r) => r.symbol}
      />,
    );
    expect(screen.getByText("Valuation")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });
});
