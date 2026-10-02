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
    // R15-UI-068: aria-sort lives on the <th> (WAI-ARIA sortable-table
    // pattern); the click target is the nested <button> so the header is
    // keyboard-reachable — see the next test for the keyboard path.
    fireEvent.click(screen.getByRole("button", { name: "Price" }));
    expect(onSort).toHaveBeenCalledWith("price");
  });

  it("makes a sortable header keyboard-operable (R15-UI-068)", () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.symbol} onSort={onSort} />);
    const button = screen.getByRole("button", { name: "Symbol" });
    // A real <button> is natively focusable and fires `click` for both Enter
    // and Space without any extra key-handling code — that's the whole fix.
    button.focus();
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    expect(onSort).toHaveBeenCalledWith("symbol");
  });

  it("renders skeleton rows and marks the table busy when loading (R15-UI-068)", () => {
    const { container } = render(
      <DataTable columns={columns} rows={[]} rowKey={(r) => r.symbol} loading={{ rows: 3 }} />,
    );
    const table = container.querySelector("table")!;
    expect(table.getAttribute("aria-busy")).toBe("true");
    expect(container.querySelectorAll("tbody tr").length).toBe(3);
    // Skeleton rows are presentational only — no real cell text is rendered.
    expect(screen.queryByText("AAPL")).not.toBeInTheDocument();
  });

  it("renders the empty slot when there are zero rows and not loading (R15-UI-068)", () => {
    render(
      <DataTable
        columns={columns}
        rows={[]}
        rowKey={(r) => r.symbol}
        empty="No symbols match this screen."
      />,
    );
    expect(screen.getByText("No symbols match this screen.")).toBeInTheDocument();
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
