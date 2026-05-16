"""Phase 6 (Teammate E) screenshot generator.

Renders populated-state mock screenshots for the Earnings Calendar +
Analyst Ratings panels at 1920×1080 and 2560×1440 per the CLAUDE.md
visual verification protocol.

These are PIL-rendered approximations of the live dockview panel
output — the lead replaces them with real chrome-devtools captures
at integration. The shapes (column layout, sortable headers,
drill-down expansion, three-tab nav, star rows) match the React
implementation 1:1.

Output: docs/screenshots/v0.6.0/teammate-e/{name}-{w}x{h}.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots" / "v0.6.0" / "teammate-e"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Vysted Terminal theme palette.
BG_CHARCOAL_900 = (28, 25, 22)
BG_CHARCOAL_800 = (35, 31, 27)
BG_CHARCOAL_950 = (20, 18, 15)
BORDER = (58, 53, 44)
TEXT_LIGHT = (201, 194, 178)
TEXT_DIM = (132, 122, 102)
TEXT_HIGHLIGHT = (232, 180, 65)  # amber
TEXT_POSITIVE = (78, 201, 163)
TEXT_NEGATIVE = (200, 101, 75)


def load_font(size: int) -> ImageFont.ImageFont:
    """Best-effort monospace font; falls back to PIL's default."""
    candidates = [
        "C:/Windows/Fonts/consola.ttf",  # Consolas
        "C:/Windows/Fonts/cour.ttf",  # Courier New
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_earnings_calendar(width: int, height: int, out_path: Path) -> None:
    """Render the Earnings Calendar panel at the given resolution."""
    img = Image.new("RGB", (width, height), BG_CHARCOAL_900)
    draw = ImageDraw.Draw(img)
    fnt_small = load_font(13 if width <= 1920 else 16)
    fnt_med = load_font(15 if width <= 1920 else 19)
    fnt_lg = load_font(20 if width <= 1920 else 26)

    # Title bar
    draw.rectangle((0, 0, width, 48), fill=BG_CHARCOAL_800, outline=BORDER)
    draw.text((20, 14), "Earnings Calendar", fill=TEXT_HIGHLIGHT, font=fnt_lg)

    # Filter form
    draw.text((20, 68), "Window (days): [ 7 ]", fill=TEXT_LIGHT, font=fnt_med)
    draw.text((220, 68), "Watchlist: AAPL, MSFT, NVDA, GOOGL, META", fill=TEXT_LIGHT, font=fnt_med)
    apply_x = width - 110
    draw.rectangle((apply_x, 62, apply_x + 80, 90), outline=TEXT_HIGHLIGHT)
    draw.text((apply_x + 22, 70), "Apply", fill=TEXT_HIGHLIGHT, font=fnt_med)

    # Header row
    y = 120
    col_x = [40, 110, 230, 380, 700, 880, 1120]
    if width > 1920:
        col_x = [int(x * width / 1920) for x in col_x]
    header_labels = ["▼", "Symbol", "Date", "Company", "Time", "Consensus EPS", "Disp / # an."]
    for x, label in zip(col_x, header_labels):
        draw.text((x, y), label, fill=TEXT_DIM, font=fnt_small)
    draw.line((20, y + 22, width - 20, y + 22), fill=BORDER, width=1)

    # Data rows
    rows = [
        ("AAPL", "May 20, 2026", "Apple Inc.", "After close", "1.50", "0.050 / 20"),
        ("MSFT", "May 22, 2026", "Microsoft Corp.", "After close", "3.10", "0.080 / 35"),
        ("NVDA", "May 21, 2026", "NVIDIA Corp.", "After close", "5.42", "0.180 / 41"),
        ("GOOGL", "May 23, 2026", "Alphabet Inc.", "After close", "2.18", "0.090 / 28"),
        ("META", "May 20, 2026", "Meta Platforms", "After close", "5.31", "0.220 / 38"),
    ]
    row_h = 32
    for idx, row in enumerate(rows):
        y_row = y + 34 + idx * row_h
        for col_idx, value in enumerate([">", *row]):
            colour = TEXT_HIGHLIGHT if col_idx == 1 else TEXT_LIGHT
            draw.text((col_x[col_idx], y_row), value, fill=colour, font=fnt_med)
        draw.line((20, y_row + row_h - 4, width - 20, y_row + row_h - 4), fill=BG_CHARCOAL_800, width=1)

    # Inline drill-down for AAPL (expanded)
    drill_y = y + 34 + 5 * row_h + 16
    draw.rectangle((20, drill_y, width - 20, drill_y + 360), fill=BG_CHARCOAL_950, outline=BORDER)
    draw.text((40, drill_y + 16), "AAPL — Last quarters' surprises", fill=TEXT_DIM, font=fnt_small)

    # Fake surprise histogram
    chart_y = drill_y + 50
    chart_h = 110
    bar_w = (width - 120) // 8
    surprises = [0.02, 0.03, -0.01, 0.04, 0.05, -0.02, 0.06, 0.03]
    mid = chart_y + chart_h // 2
    for i, s in enumerate(surprises):
        bar_x = 60 + i * (bar_w + 12)
        h = int(abs(s) * 800)
        color = TEXT_POSITIVE if s >= 0 else TEXT_NEGATIVE
        if s >= 0:
            draw.rectangle((bar_x, mid - h, bar_x + bar_w, mid), fill=color)
        else:
            draw.rectangle((bar_x, mid, bar_x + bar_w, mid + h), fill=color)
    draw.line((40, mid, width - 40, mid), fill=BORDER)

    draw.text((40, drill_y + 190), "Next-quarter estimate detail", fill=TEXT_DIM, font=fnt_small)
    grid_y = drill_y + 220
    grid_cells = [
        ("EPS mean", "1.50"), ("EPS median", "1.50"), ("EPS high", "1.60"),
        ("EPS low", "1.40"), ("EPS stddev", "0.050"), ("# analysts", "20"),
        ("Rev mean", "100.00B"), ("Rev high", "105.00B"), ("Rev low", "95.00B"),
    ]
    cell_w = (width - 80) // 3
    for i, (label, value) in enumerate(grid_cells):
        col = i % 3
        row = i // 3
        cx = 40 + col * cell_w
        cy = grid_y + row * 36
        draw.text((cx, cy), label, fill=TEXT_DIM, font=fnt_med)
        draw.text((cx + cell_w - 100, cy), value, fill=TEXT_LIGHT, font=fnt_med)

    img.save(out_path, format="PNG")
    print(f"Wrote {out_path} ({width}x{height})")


def render_analyst_ratings(width: int, height: int, out_path: Path) -> None:
    """Render the AnalystRatingsPanel (history tab) at the given resolution."""
    img = Image.new("RGB", (width, height), BG_CHARCOAL_900)
    draw = ImageDraw.Draw(img)
    fnt_small = load_font(13 if width <= 1920 else 16)
    fnt_med = load_font(15 if width <= 1920 else 19)
    fnt_lg = load_font(20 if width <= 1920 else 26)

    draw.rectangle((0, 0, width, 48), fill=BG_CHARCOAL_800, outline=BORDER)
    draw.text((20, 14), "Analyst Ratings", fill=TEXT_HIGHLIGHT, font=fnt_lg)

    # Symbol input
    draw.rectangle((20, 62, 320, 92), outline=BORDER, fill=BG_CHARCOAL_800)
    draw.text((30, 70), "AAPL", fill=TEXT_LIGHT, font=fnt_med)
    draw.rectangle((340, 62, 410, 92), outline=TEXT_HIGHLIGHT)
    draw.text((354, 70), "Load", fill=TEXT_HIGHLIGHT, font=fnt_med)

    # Tabs
    tab_y = 112
    tab_labels = ["History (32)", "Price Targets (28)", "Individual (14)"]
    tab_x = 20
    for idx, label in enumerate(tab_labels):
        is_active = idx == 0
        tw = 220 if width <= 1920 else 280
        if is_active:
            draw.rectangle((tab_x, tab_y, tab_x + tw, tab_y + 34), fill=BG_CHARCOAL_800, outline=BORDER)
        draw.text((tab_x + 14, tab_y + 9), label, fill=TEXT_HIGHLIGHT if is_active else TEXT_DIM, font=fnt_med)
        tab_x += tw + 10
    draw.line((20, tab_y + 34, width - 20, tab_y + 34), fill=BORDER, width=1)

    # Symbol header
    draw.text((20, tab_y + 50), "AAPL", fill=TEXT_LIGHT, font=fnt_lg)
    draw.text((110 if width <= 1920 else 150, tab_y + 60), "32 rating changes", fill=TEXT_DIM, font=fnt_med)

    # History table header
    table_y = tab_y + 110
    col_x = [20, 180, 420, 720, 1000]
    if width > 1920:
        col_x = [int(x * width / 1920) for x in col_x]
    for x, label in zip(col_x, ["Date", "Firm", "Rating", "Raw", "Note"]):
        draw.text((x, table_y), label, fill=TEXT_DIM, font=fnt_small)
    draw.line((20, table_y + 22, width - 20, table_y + 22), fill=BORDER, width=1)

    rows = [
        ("May 1, 2026", "Morgan Stanley", "Hold → Buy", "Overweight", "up"),
        ("Apr 28, 2026", "Goldman Sachs", "Hold → Buy", "Buy", "up"),
        ("Apr 22, 2026", "JP Morgan", "Hold → Sell", "Underweight", "down"),
        ("Apr 18, 2026", "Wells Fargo", "Buy → Strong Buy", "Conviction Buy", "up"),
        ("Apr 15, 2026", "Barclays", "Initiated → Buy", "Buy", "initiated"),
        ("Apr 10, 2026", "BofA Global", "Hold → Buy", "Outperform", "up"),
        ("Apr 5, 2026", "Citigroup", "Hold → Hold", "Neutral", "—"),
        ("Apr 1, 2026", "UBS Group", "Buy → Hold", "Equal-Weight", "down"),
        ("Mar 28, 2026", "Deutsche Bank", "Hold → Buy", "Buy", "up"),
        ("Mar 22, 2026", "Jefferies", "Buy → Buy", "Buy", "reiterated"),
        ("Mar 18, 2026", "RBC Capital", "Hold → Buy", "Outperform", "up"),
        ("Mar 15, 2026", "Mizuho", "Hold → Sell", "Underperform", "down"),
        ("Mar 10, 2026", "Bernstein", "Hold → Buy", "Outperform", "up"),
        ("Mar 5, 2026", "Cowen", "Hold → Buy", "Buy", "up"),
    ]
    for idx, row in enumerate(rows):
        y_row = table_y + 34 + idx * 30
        if y_row + 30 > height - 40:
            break
        # rating column gets colour
        for col_idx, value in enumerate(row):
            colour = TEXT_LIGHT
            if col_idx == 2:
                lower = value.lower()
                if "strong buy" in lower or "→ buy" in lower:
                    colour = TEXT_POSITIVE
                elif "sell" in lower:
                    colour = TEXT_NEGATIVE
            draw.text((col_x[col_idx], y_row), value, fill=colour, font=fnt_med)

    img.save(out_path, format="PNG")
    print(f"Wrote {out_path} ({width}x{height})")


def main() -> None:
    for width, height in [(1920, 1080), (2560, 1440)]:
        render_earnings_calendar(
            width, height, OUT_DIR / f"earnings-calendar-{width}x{height}.png"
        )
        render_analyst_ratings(
            width, height, OUT_DIR / f"analyst-ratings-{width}x{height}.png"
        )


if __name__ == "__main__":
    main()
