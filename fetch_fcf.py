#!/usr/bin/env python3
"""
Nightly GitHub Actions script — fetches FCF Yield for all portfolio tickers
using yfinance and writes results to fcf_data.json in the repo root.

FCF Yield = Free Cash Flow (TTM) / Market Cap
"""

import json
import datetime
import sys

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

# ── All unique tickers across all portfolios ─────────────────────────────────
# ETH/USD and crypto/non-standard tickers are excluded (no FCF data)
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
    "DE", "DIS", "ELV", "GM", "INTC", "LOW", "META",
    "NOC", "RTX", "TMO", "WFC",
]))

# Map dashboard symbols to yfinance symbols where they differ
SYMBOL_MAP = {
    "BRK.B": "BRK-B",   # yfinance uses BRK-B
    "ETH/USD": None,     # skip — no FCF
    "IBIT": None,        # skip — ETF, no FCF
}

def get_fcf_yield(ticker_sym):
    """Returns FCF yield as a float (e.g. 0.034 = 3.4%) or None if unavailable."""
    try:
        t = yf.Ticker(ticker_sym)
        info = t.info

        # Free cash flow (TTM)
        fcf = info.get("freeCashflow")
        # Market cap
        market_cap = info.get("marketCap")

        if fcf is None or market_cap is None or market_cap == 0:
            return None

        return fcf / market_cap

    except Exception as e:
        print(f"  Error fetching {ticker_sym}: {e}")
        return None

def main():
    results = {}
    total = len(TICKERS)
    print(f"Fetching FCF Yield for {total} tickers...")

    for i, sym in enumerate(TICKERS):
        # Map to yfinance symbol if needed
        yf_sym = SYMBOL_MAP.get(sym, sym)
        if yf_sym is None:
            print(f"  [{i+1}/{total}] {sym} — skipped (no FCF applicable)")
            results[sym] = None
            continue

        print(f"  [{i+1}/{total}] {sym} ({yf_sym})...", end=" ")
        fcf_yield = get_fcf_yield(yf_sym)

        if fcf_yield is not None:
            print(f"{fcf_yield*100:.2f}%")
        else:
            print("n/a")

        # Store under original dashboard symbol
        results[sym] = fcf_yield
        # Also store under BRK.B if we fetched BRK-B
        if sym == "BRK-B":
            results["BRK.B"] = fcf_yield

    output = {
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "data": results
    }

    with open("fcf_data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. Written to fcf_data.json ({len(results)} tickers)")
    print(f"Timestamp: {output['updated']}")

if __name__ == "__main__":
    main()
