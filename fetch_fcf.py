#!/usr/bin/env python3
"""
Nightly GitHub Actions script — fetches FCF Yield (current + historical)
for all portfolio tickers using yfinance, writes to fcf_data.json.

FCF Yield = Free Cash Flow (TTM) / Market Cap
Historical = annual FCF / year-end market cap (approximated via avg price * shares)
"""

import json
import datetime
import sys

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

TICKERS = sorted(set([
    # Hunter's Portfolio
    "AMZN", "ASML", "BIDU", "BYDDY", "CRM", "GOOGL", "GRRR", "HIMS",
    "IONQ", "JD", "ONDS", "OSCR", "PEGA", "PEP", "QBTS", "SE",
    "TSLA", "UNH", "ZETA", "ZVRA", "IBIT",
    # Dividend Growth Portfolio
    "AAPL", "ABBV", "ACN", "AVGO", "BAC", "CB", "CMCSA", "CVX",
    "ELV", "EOG", "HD", "HON", "JNJ", "JPM", "KO", "MA", "MCD",
    "MDT", "MRK", "MRSH", "MSFT", "NEE", "PFE", "PG", "PM",
    "SCHW", "TXN", "UNP", "V", "WMT", "XOM",
    # Large Value Portfolio
    "AIG", "AXP", "BRK-B", "C", "CI", "COF", "COP", "CVS",
    "DE", "DIS", "GM", "INTC", "LOW", "META",
    "NOC", "RTX", "TMO", "WFC",
]))

SYMBOL_MAP = {
    "BRK.B":   "BRK-B",
    "ETH/USD": None,
    "IBIT":    None,
}

def get_fcf_data(ticker_sym):
    """
    Returns dict with:
      - current: float (TTM FCF yield) or None
      - history: list of {year, fcfYield} for up to 5 years
      - avg5y:   float (5-year average FCF yield) or None
    """
    result = { "current": None, "history": [], "avg5y": None }
    try:
        t = yf.Ticker(ticker_sym)
        info = t.info

        # ── Current TTM FCF Yield ────────────────────────────────────────────
        fcf_ttm    = info.get("freeCashflow")
        market_cap = info.get("marketCap")
        shares_out = info.get("sharesOutstanding")

        if fcf_ttm and market_cap and market_cap > 0:
            result["current"] = fcf_ttm / market_cap

        # ── Historical Annual FCF Yield ──────────────────────────────────────
        # Use annual cash flow statement for FCF
        cf = t.cashflow  # columns = fiscal year end dates
        if cf is None or cf.empty:
            return result

        # FCF = Operating Cash Flow - Capital Expenditures
        history = []
        for col in cf.columns[:5]:  # last 5 fiscal years
            try:
                op_cf = None
                capex = 0

                # Try multiple row name variations yfinance uses
                for row in ["Operating Cash Flow", "Total Cash From Operating Activities",
                            "Cash Flow From Continuing Operating Activities"]:
                    if row in cf.index:
                        op_cf = cf.loc[row, col]
                        break

                for row in ["Capital Expenditure", "Capital Expenditures",
                            "Purchase Of Property Plant And Equipment"]:
                    if row in cf.index:
                        capex = cf.loc[row, col]
                        break

                if op_cf is None or str(op_cf) == 'nan':
                    continue

                fcf_annual = float(op_cf) - abs(float(capex)) if str(capex) != 'nan' else float(op_cf)

                # Get year-end price to approximate market cap
                year = col.year
                # Use shares outstanding * year-end closing price
                if shares_out:
                    # Fetch year-end price
                    year_str  = f"{year}-12-15"
                    year_str2 = f"{year}-12-31"
                    try:
                        hist = t.history(start=year_str, end=year_str2, interval="1d")
                        if not hist.empty:
                            yr_price   = float(hist["Close"].iloc[-1])
                            yr_mktcap  = yr_price * shares_out
                            fcf_yield  = fcf_annual / yr_mktcap
                            history.append({
                                "year":     year,
                                "fcfYield": round(fcf_yield, 4)
                            })
                    except Exception:
                        pass

            except Exception as e:
                print(f"    History error for {ticker_sym} {col}: {e}")
                continue

        # Sort chronologically
        history.sort(key=lambda x: x["year"])
        result["history"] = history

        # 5-year average
        if history:
            vals = [h["fcfYield"] for h in history if h["fcfYield"] is not None]
            result["avg5y"] = round(sum(vals) / len(vals), 4) if vals else None

    except Exception as e:
        print(f"  Error fetching {ticker_sym}: {e}")

    return result


def main():
    results = {}
    total = len(TICKERS)
    print(f"Fetching FCF data for {total} tickers...\n")

    for i, sym in enumerate(TICKERS):
        yf_sym = SYMBOL_MAP.get(sym, sym)
        if yf_sym is None:
            print(f"[{i+1}/{total}] {sym} — skipped")
            results[sym] = { "current": None, "history": [], "avg5y": None }
            continue

        print(f"[{i+1}/{total}] {sym}...", end=" ", flush=True)
        data = get_fcf_data(yf_sym)

        cur = f"{data['current']*100:.2f}%" if data["current"] is not None else "n/a"
        avg = f"{data['avg5y']*100:.2f}%" if data["avg5y"] is not None else "n/a"
        print(f"current={cur}  5yr_avg={avg}  history={len(data['history'])} years")

        results[sym] = data
        if sym == "BRK-B":
            results["BRK.B"] = data

    output = {
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "data": results
    }

    with open("fcf_data.json", "w") as f:
        json.dump(output, f, indent=2)

    success = sum(1 for v in results.values() if v.get("current") is not None)
    print(f"\nDone. {success}/{total} tickers with FCF data. Written to fcf_data.json")

if __name__ == "__main__":
    main()
