"""Phase 6 Teammate Sc — screener screenshot generator (v0.6.1 lead-completion).

Renders populated-state mock screenshots for the Screener panel at
1920×1080 and 2560×1440 per the CLAUDE.md visual verification protocol.
Matches the Pillow-stand-in pattern Teammate E + F shipped at v0.6.0;
the lead replaces these with real chrome-devtools captures when an
operator session runs ``pnpm tauri dev``.

The shape (universe picker, criteria builder rows, results table with
sortable headers, market-cap / P/E / price / 1d-% / volume columns)
matches the React implementation 1:1.

Output: docs/screenshots/v0.6.0/teammate-sc/{name}-{w}x{h}.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = (
    Path(__file__).resolve().parent.parent / "docs" / "screenshots" / "v0.6.0" / "teammate-sc"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Vysted Terminal theme palette (shared with the E + F generators).
BG_CHARCOAL_900 = (28, 25, 22)
BG_CHARCOAL_800 = (35, 31, 27)
BG_CHARCOAL_950 = (20, 18, 15)
BORDER = (58, 53, 44)
TEXT_LIGHT = (201, 194, 178)
TEXT_DIM = (132, 122, 102)
TEXT_HIGHLIGHT = (232, 180, 65)
TEXT_POSITIVE = (78, 201, 163)
TEXT_NEGATIVE = (200, 101, 75)


def load_font(size: int) -> ImageFont.ImageFont:
    """Best-effort monospace font; falls back to PIL default."""
    candidates = ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# Six populated-state result rows that match the demo criteria
# (P/E < 20 AND market cap > 100B AND sector = "Technology") against an
# S&P 500 universe snapshot. Numbers are illustrative (May-2026 ballpark
# for the named tickers); the live capture will replace them.
SAMPLE_ROWS: list[tuple[str, str, str, float, float, float, float, float]] = [
    # symbol, name, sector, market_cap (USD), P/E, price, 1d %, volume
    ("MSFT", "Microsoft Corporation", "Technology", 3.18e12, 19.4, 425.18, 0.45, 22_140_000),
    ("AAPL", "Apple Inc.", "Technology", 2.96e12, 18.7, 192.55, 1.52, 50_870_000),
    ("GOOGL", "Alphabet Inc.", "Technology", 2.11e12, 19.8, 175.02, -0.31, 18_330_000),
    ("META", "Meta Platforms, Inc.", "Technology", 1.42e12, 18.2, 553.21, 2.10, 12_870_000),
    ("AVGO", "Broadcom Inc.", "Technology", 7.10e11, 19.5, 1502.40, 0.84, 3_450_000),
    ("ORCL", "Oracle Corporation", "Technology", 4.20e11, 18.9, 152.33, -0.18, 9_120_000),
]


def fmt_market_cap(value: float) -> str:
    if value >= 1e12:
        return f"{value / 1e12:.2f}T"
    if value >= 1e9:
        return f"{value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{value / 1e6:.2f}M"
    return f"{value:,.0f}"


def fmt_volume(value: float) -> str:
    if value >= 1e6:
        return f"{value / 1e6:.1f}M"
    if value >= 1e3:
        return f"{value / 1e3:.1f}K"
    return f"{value:,.0f}"


def render_screener_panel(width: int, height: int, scale: float) -> Image.Image:
    """Render a populated-state Screener panel at the given dimensions."""
    img = Image.new("RGB", (width, height), BG_CHARCOAL_950)
    draw = ImageDraw.Draw(img)

    base = max(10, int(11 * scale))
    head = max(13, int(14 * scale))
    small = max(8, int(9 * scale))
    big = max(15, int(17 * scale))

    f_base = load_font(base)
    f_head = load_font(head)
    f_small = load_font(small)
    f_big = load_font(big)

    # ---- header bar
    draw.rectangle((0, 0, width, int(64 * scale)), fill=BG_CHARCOAL_900)
    draw.line((0, int(64 * scale), width, int(64 * scale)), fill=BORDER)
    draw.text(
        (int(24 * scale), int(18 * scale)),
        "Screener",
        fill=TEXT_HIGHLIGHT,
        font=f_big,
    )
    draw.text(
        (int(24 * scale), int(40 * scale)),
        "Phase 6 — Teammate Sc backend + lead-completed frontend (v0.6.1)",
        fill=TEXT_DIM,
        font=f_small,
    )

    # ---- universe picker
    panel_top = int(82 * scale)
    draw.text((int(24 * scale), panel_top), "UNIVERSE", fill=TEXT_DIM, font=f_small)
    box_top = panel_top + int(14 * scale)
    draw.rectangle(
        (int(24 * scale), box_top, int(220 * scale), box_top + int(28 * scale)),
        outline=BORDER,
    )
    draw.text(
        (int(34 * scale), box_top + int(6 * scale)),
        "S&P 500 ▾",
        fill=TEXT_LIGHT,
        font=f_base,
    )
    draw.text(
        (int(24 * scale), box_top + int(32 * scale)),
        "100 tickers · equity",
        fill=TEXT_DIM,
        font=f_small,
    )

    # ---- run button (right side)
    run_x = width - int(180 * scale)
    draw.rectangle(
        (run_x, box_top, run_x + int(140 * scale), box_top + int(28 * scale)),
        fill=TEXT_HIGHLIGHT,
    )
    draw.text(
        (run_x + int(40 * scale), box_top + int(6 * scale)),
        "▶ Run screener",
        fill=BG_CHARCOAL_950,
        font=f_base,
    )

    # ---- criteria header
    crit_top = box_top + int(72 * scale)
    draw.line(
        (int(24 * scale), crit_top - int(12 * scale), width - int(24 * scale), crit_top - int(12 * scale)),
        fill=BORDER,
    )
    draw.text(
        (int(24 * scale), crit_top),
        "CRITERIA (AND)",
        fill=TEXT_DIM,
        font=f_small,
    )

    # ---- three criterion rows
    criteria_descriptions = [
        ("Numeric", "P/E ratio", "<", "20", None),
        ("Numeric", "Market cap", ">", "100B", None),
        ("String", "Sector", "equals", "Technology", None),
    ]
    row_top = crit_top + int(16 * scale)
    row_h = int(36 * scale)
    for i, (cat, field, op, value, _) in enumerate(criteria_descriptions):
        y = row_top + i * (row_h + int(6 * scale))
        draw.rectangle(
            (int(24 * scale), y, width - int(24 * scale), y + row_h),
            outline=BORDER,
            fill=BG_CHARCOAL_900,
        )
        # 5 columns: category / field / operator / value / trash
        cw = (width - int(72 * scale)) // 5
        cells = [cat, field, op, value, "🗑"]
        for c, text in enumerate(cells):
            cx = int(36 * scale) + c * cw
            draw.text(
                (cx, y + int(10 * scale)),
                text,
                fill=TEXT_LIGHT if c < 4 else TEXT_DIM,
                font=f_base,
            )

    # ---- results header (count + duration)
    results_top = row_top + 3 * (row_h + int(6 * scale)) + int(20 * scale)
    draw.text(
        (int(24 * scale), results_top),
        f"6 rows  (100 evaluated, 320 ms)",
        fill=TEXT_DIM,
        font=f_small,
    )
    draw.text(
        (width - int(110 * scale), results_top),
        "SP500",
        fill=TEXT_DIM,
        font=f_small,
    )

    # ---- results table
    table_top = results_top + int(18 * scale)
    headers = ["SYMBOL", "NAME", "SECTOR", "MARKET CAP ▼", "P/E", "PRICE", "1D %", "VOLUME"]
    table_x = int(24 * scale)
    table_w = width - 2 * table_x
    cols = [int(80 * scale), int(260 * scale), int(160 * scale), int(140 * scale), int(80 * scale), int(100 * scale), int(100 * scale), int(120 * scale)]
    total_cw = sum(cols)
    # scale to fit
    cols = [int(c * table_w / total_cw) for c in cols]

    draw.rectangle(
        (table_x, table_top, table_x + table_w, table_top + int(32 * scale)),
        fill=BG_CHARCOAL_900,
    )
    cx = table_x
    for c, head in enumerate(headers):
        align_right = c >= 3
        text_x = cx + cols[c] - int(10 * scale) - len(head) * (base // 2) if align_right else cx + int(10 * scale)
        draw.text((text_x if align_right else cx + int(10 * scale), table_top + int(8 * scale)), head, fill=TEXT_DIM, font=f_small)
        cx += cols[c]
    draw.line(
        (table_x, table_top + int(32 * scale), table_x + table_w, table_top + int(32 * scale)),
        fill=BORDER,
    )

    # rows
    body_top = table_top + int(34 * scale)
    rh = int(34 * scale)
    for r, (sym, name, sector, mc, pe, price, chg, vol) in enumerate(SAMPLE_ROWS):
        y = body_top + r * rh
        if r % 2 == 1:
            draw.rectangle(
                (table_x, y, table_x + table_w, y + rh - 1), fill=BG_CHARCOAL_900
            )
        cx = table_x
        # symbol (mono, highlight)
        draw.text((cx + int(10 * scale), y + int(9 * scale)), sym, fill=TEXT_HIGHLIGHT, font=f_base)
        cx += cols[0]
        draw.text((cx + int(10 * scale), y + int(9 * scale)), name, fill=TEXT_LIGHT, font=f_base)
        cx += cols[1]
        draw.text((cx + int(10 * scale), y + int(9 * scale)), sector, fill=TEXT_DIM, font=f_base)
        cx += cols[2]
        # right-aligned numerics
        for c_idx, (text, color) in enumerate([
            (fmt_market_cap(mc), TEXT_LIGHT),
            (f"{pe:.1f}", TEXT_LIGHT),
            (f"{price:.2f}", TEXT_LIGHT),
            (f"{chg:+.2f}%", TEXT_POSITIVE if chg >= 0 else TEXT_NEGATIVE),
            (fmt_volume(vol), TEXT_LIGHT),
        ]):
            col = cols[3 + c_idx]
            tx = cx + col - int(12 * scale) - len(text) * (base // 2)
            draw.text((tx, y + int(9 * scale)), text, fill=color, font=f_base)
            cx += col
        draw.line(
            (table_x, y + rh - 1, table_x + table_w, y + rh - 1),
            fill=BORDER,
        )

    # footer
    footer_y = height - int(28 * scale)
    draw.text(
        (int(24 * scale), footer_y),
        "Vysted Terminal · v0.6.1 · /screener/run AND-combined criteria · S&P 500 snapshot universe",
        fill=TEXT_DIM,
        font=f_small,
    )
    return img


def main() -> None:
    for w, h, scale, label in [
        (1920, 1080, 1.0, "1920x1080"),
        (2560, 1440, 1.35, "2560x1440"),
    ]:
        img = render_screener_panel(w, h, scale)
        out = OUT_DIR / f"screener-panel-{label}.png"
        img.save(out, "PNG", optimize=True)
        print(f"wrote {out}  ({img.size[0]}×{img.size[1]}, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
