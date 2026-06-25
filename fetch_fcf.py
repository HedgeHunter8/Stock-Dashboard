#!/usr/bin/env python3
"""
Nightly GitHub Actions script — fetches FCF Yield (current + historical)
for all portfolio tickers using yfinance.

Writes results to:
  1. fcf_data.json  — raw data archive
  2. Injects the data directly into index.html as a JS variable
     so the dashboard never needs a fetch() call (avoids CORS issues)
"""

import json
import datetime
import sys
import re

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

TICKERS = sorted(set([
    # Hunter's Portfolio
    "AMZN", "ASML", "BABA", "BIDU", "BYDDY", "CRM", "GOOGL", "GRRR", "HIMS",
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
    result = { "current": None, "history": [], "avg5y": None }
    try:
        t = yf.Ticker(ticker_sym)
        info = t.info

        fcf_ttm    = info.get("freeCashflow")
        market_cap = info.get("marketCap")
        shares_out = info.get("sharesOutstanding")

        if fcf_ttm and market_cap and market_cap > 0:
            result["current"] = fcf_ttm / market_cap

        cf = t.cashflow
        if cf is None or cf.empty:
            return result

        history = []
        for col in cf.columns[:5]:
            try:
                op_cf = None
                capex = 0
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
                year = col.year
                if shares_out:
                    year_str  = f"{year}-12-15"
                    year_str2 = f"{year}-12-31"
                    try:
                        hist = t.history(start=year_str, end=year_str2, interval="1d")
                        if not hist.empty:
                            yr_price  = float(hist["Close"].iloc[-1])
                            yr_mktcap = yr_price * shares_out
                            fcf_yield = fcf_annual / yr_mktcap
                            history.append({"year": year, "fcfYield": round(fcf_yield, 4)})
                    except Exception:
                        pass
            except Exception as e:
                print(f"    History error for {ticker_sym} {col}: {e}")
                continue

        history.sort(key=lambda x: x["year"])
        result["history"] = history
        if history:
            vals = [h["fcfYield"] for h in history if h["fcfYield"] is not None]
            result["avg5y"] = round(sum(vals) / len(vals), 4) if vals else None

    except Exception as e:
        print(f"  Error fetching {ticker_sym}: {e}")
    return result


def inject_into_html(data_obj):
    """Replace the FCF data inline script tag in index.html."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print("  index.html not found — skipping HTML injection")
        return

    json_str = json.dumps(data_obj, separators=(',', ':'))

    # Replace between marker comments
    marker_start = "/* FCF_DATA_START */"
    marker_end   = "/* FCF_DATA_END */"
    new_block    = f"{marker_start}\nwindow._FCF_DATA={json_str};\n{marker_end}"

    if marker_start in html and marker_end in html:
        # Replace existing block
        pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
        html = re.sub(pattern, new_block, html, flags=re.DOTALL)
        print("  Injected FCF data into existing marker block in index.html")
    else:
        # Insert before closing </script> of the main script block
        html = html.replace("// ── Init", f"{new_block}\n// ── Init")
        print("  Inserted FCF data marker block into index.html")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


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

    # 1. Write raw JSON archive
    with open("fcf_data.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWritten to fcf_data.json")

    # 2. Inject directly into index.html
    print("Injecting into index.html...")
    inject_into_html(output)

    success = sum(1 for v in results.values() if v.get("current") is not None)
    print(f"Done. {success}/{total} tickers with current FCF data.")

if __name__ == "__main__":
    main()
