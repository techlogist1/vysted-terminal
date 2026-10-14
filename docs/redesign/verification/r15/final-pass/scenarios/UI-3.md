# UI-3 — quote freshness follows the exchange calendar (final-adv-maintainer, d38b5d1a)

## Live (own :52825, Sat 3 Oct 09:47Z; UI-3/live-freshness.txt)
Every equity quote is `eod`, none `live`, under both X-Vysted-Region IN and US: AAPL/SPY/^GSPC (US, bar Fri 2 Oct), INFY/TCS.NS/RELIANCE.BO (NSE/BSE, bar Thu 1 Oct — Fri 2 Oct is the Gandhi Jayanti NSE holiday, so a Thu bar is correctly the last session, not stale), ^NSEI (IN calendar), 7203.T/HSBA.L (foreign, fail-closed). Several calls answered the honest throttle message (upstream 429), never a fabricated quote. The portfolio panel badges the same labels (UI-2 rows: "EOD", "EOD Weekend" from the NSE `market_state: CLOSED`).

## Calendar matrix (in-process `instrument_region` + `freshness_for` with a fixed clock; UI-3/calendar-matrix.txt)
- AAPL mid-US-session, tick today → live; tick yesterday → eod; during NSE hours (US closed) → eod (the R15-UI-090 headline harm — a closed US quote reading live during Indian hours — does not recur).
- INFY mid-NSE-session → live; on the Oct 2 NSE holiday and the following Saturday → eod; ^NSEI dated on the IN calendar → live mid-NSE-session.
- AAPL on US Thanksgiving / the Friday after → eod.
- One missed session still reads eod (the documented `_STALE_REJECT_SESSIONS` tolerance in `freshness_for`), by design.
- 7203.T mid-Tokyo-session → eod: the foreign-exchange half that DECISIONS 4.20 left `blocked_tier4` (operator decision pending). Evidence attached to R15-UI-090, not re-filed.

VERDICT UI-3: pass
