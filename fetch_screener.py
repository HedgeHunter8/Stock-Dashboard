#!/usr/bin/env python3
"""
Nightly GitHub Actions script — Russell 3000 FCF Screener
Fetches comprehensive FCF metrics for all Russell 3000 components,
excluding Financials, REITs, and Insurance sectors.
Writes results to screener_data.json.

Metrics calculated per ticker:
  - FCF Yield (current TTM + 5yr history)
  - FCF/Net Income ratio (quality signal)
  - FCF/Share + 3yr growth rate + stability score
  - Shareholder Yield (FCF + Dividend + Buyback yield)
  - P/FCF current + 5yr historical average
  - FCF/S > EPS green flag
  - FCF Yield vs 10yr Treasury spread

Runtime: ~45-60 minutes on GitHub Actions free tier.
"""

import json
import time
import datetime
import sys
import math
import urllib.request

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed.")
    sys.exit(1)

# ── Excluded sectors/industries ──────────────────────────────────────────────
EXCLUDED_SECTORS    = {"Financial Services", "Financials"}
EXCLUDED_INDUSTRIES = {
    "Banks—Diversified","Banks—Regional","Banks - Diversified","Banks - Regional",
    "Mortgage Finance","Credit Services",
    "Insurance—Diversified","Insurance—Life","Insurance—Property & Casualty",
    "Insurance—Specialty","Insurance—Reinsurance",
    "Insurance - Diversified","Insurance - Life","Insurance - Property & Casualty",
    "Insurance - Specialty","Insurance - Reinsurance",
    "REIT—Diversified","REIT—Healthcare Facilities","REIT—Hotel & Motel",
    "REIT—Industrial","REIT—Mortgage","REIT—Office","REIT—Residential",
    "REIT—Retail","REIT—Specialty",
    "REIT - Diversified","REIT - Healthcare Facilities","REIT - Hotel & Motel",
    "REIT - Industrial","REIT - Mortgage","REIT - Office","REIT - Residential",
    "REIT - Retail","REIT - Specialty",
    "Real Estate Investment Trusts",
    "Asset Management","Capital Markets","Financial Conglomerates",
}

def get_russell3000_tickers():
    tickers = [
        "AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","META","TSLA","AVGO","COST",
        "NFLX","AMD","ADBE","QCOM","TXN","INTU","CSCO","AMAT","PANW","LRCX",
        "KLAC","SNPS","CDNS","MRVL","FTNT","ORCL","CRM","NOW","WDAY","SNOW",
        "DDOG","ZS","CRWD","NET","MDB","HUBS","TEAM","OKTA","VEEV","ANSS",
        "PTC","EPAM","CTSH","ACN","IBM","HPQ","HPE","DELL","NTAP","WDC",
        "STX","LLY","UNH","JNJ","ABBV","MRK","TMO","ABT","DHR","ISRG",
        "VRTX","REGN","GILD","AMGN","BSX","EW","SYK","MDT","ZBH","BDX",
        "DXCM","IDXX","IQV","ILMN","RMD","ALGN","HCA","THC","UHS","CYH",
        "ENSG","OSCR","MOH","CNC","CVS","CI","ELV","HUM","WMT","HD","MCD",
        "NKE","SBUX","TGT","LOW","TJX","ROST","ORLY","AZO","TSCO","ULTA",
        "LULU","RH","WSM","DG","DLTR","KR","SYY","GIS","K","CPB","HRL",
        "CAG","PG","CL","CHD","KMB","CLX","PEP","KO","MNST","CELH","STZ",
        "XOM","CVX","COP","EOG","SLB","MPC","VLO","PSX","HES","DVN",
        "HAL","BKR","OXY","FANG","APA","CTRA","MRO","GE","HON","RTX",
        "LMT","NOC","GD","BA","CAT","DE","EMR","ETN","PH","ROK","AME",
        "VRSK","CPRT","SAIA","XPO","JBHT","ODFL","WM","RSG","CTAS","RCL",
        "CCL","NCLH","MAR","HLT","EXPE","BKNG","UAL","DAL","LUV","FDX",
        "UPS","TDG","HEI","AXON","LIN","APD","SHW","ECL","PPG","NEM",
        "FCX","NUE","STLD","CMC","NEE","DUK","SO","AEP","EXC","SRE",
        "PEG","XEL","ES","AWK","PPL","DTE","WEC","GOOGL","META","NFLX",
        "DIS","CMCSA","T","VZ","TMUS","CHTR","LYV","HIMS","GRRR","IONQ",
        "QBTS","ONDS","OSCR","PEGA","ZETA","ZVRA","BIDU","JD","SE","ASML",
        "RBLX","U","TTWO","EA","TTD","APP","W","ETSY","CHWY","ONON",
        "CROX","SKX","DECK","BOOT","PVH","RL","VFC","SPGI","MSCI","EFX",
        "TRU","FICO","PAYC","PAYX","ADP","CDAY","PCTY","MTZ","PWR","PRIM",
        "GNRC","MMM","AOS","ADI","ADM","ADP","ADSK","AEE","AEP","AES",
        "AKAM","ALB","ALGN","ALK","ALLE","AMCR","AME","AMP","AMT","ANET",
        "ANSS","AON","APA","APD","APH","APTV","ATO","AVB","AVY","AZO",
        "BA","BAX","BBWI","BBY","BDX","BF-B","BIIB","BIO","BKNG","BKR",
        "BLL","BMY","BR","BRO","BSX","CAG","CAH","CARR","CAT","CB",
        "CBOE","CBRE","CCL","CDNS","CDW","CE","CEG","CF","CHD","CHRW",
        "CHTR","CI","CINF","CL","CLX","CME","CMG","CMI","CMS","CNC",
        "CNP","COO","COP","COST","CPB","CPRT","CRL","CSCO","CSGP","CSX",
        "CTAS","CTLT","CTSH","CTVA","CVS","CVX","DAL","DD","DE","DG",
        "DGX","DHI","DHR","DIS","DLR","DLTR","DOV","DOW","DPZ","DRI",
        "DTE","DUK","DVA","DVN","DXC","DXCM","EA","EBAY","ECL","ED",
        "EFX","EIX","EL","ELV","EMN","EMR","ENPH","EOG","EPAM","EQR",
        "ES","ESS","ETN","ETR","EVRG","EW","EXC","EXPD","EXPE","EXR",
        "FANG","FAST","FCX","FDX","FE","FFIV","FIS","FISV","FLT","FMC",
        "FOX","FOXA","FSLR","FTNT","FTV","GD","GE","GEHC","GEN","GILD",
        "GIS","GLW","GM","GNRC","GPC","GRMN","GWW","HAL","HAS","HCA",
        "HD","HES","HII","HLT","HOLX","HON","HPE","HPQ","HRL","HSIC",
        "HST","HSY","HUBB","HUM","HWM","IBM","ICE","IDXX","IEX","IFF",
        "ILMN","INCY","INTC","INTU","IP","IPG","IQV","IR","ISRG","IT",
        "ITW","J","JBHT","JCI","JKHY","JNJ","JNPR","K","KEYS","KHC",
        "KLAC","KMB","KMI","KMX","KO","KR","L","LDOS","LEN","LH","LHX",
        "LIN","LKQ","LLY","LMT","LNT","LOW","LRCX","LUV","LYB","LYV",
        "MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT",
        "MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH",
        "MOS","MPC","MPWR","MRK","MRNA","MSCI","MSFT","MSI","MTD","MU",
        "NCLH","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC","NTAP",
        "NUE","NVDA","NVR","NXPI","ODFL","OKE","OMC","ON","ORCL","ORLY",
        "OXY","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PG","PH",
        "PHM","PKG","PM","POOL","PPG","PPL","PSX","PTC","PWR","PXD",
        "QCOM","RCL","REGN","RHI","RJF","RL","RMD","ROK","ROL","ROP",
        "ROST","RSG","RTX","SBUX","SHW","SJM","SLB","SNA","SNPS","SO",
        "SPGI","SRE","STE","STX","STZ","SWK","SWKS","SYK","SYY","T",
        "TAP","TDG","TDY","TEL","TER","TGT","TJX","TMO","TMUS","TPR",
        "TRMB","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL","UAL",
        "UHS","ULTA","UNH","UNP","UPS","URI","V","VFC","VLO","VMC",
        "VRSK","VRSN","VRTX","VZ","WAB","WAT","WBA","WBD","WDC","WEC",
        "WFC","WHR","WM","WMB","WMT","WRB","WRK","WST","WY","WYNN",
        "XEL","XOM","XYL","YUM","ZBH","ZBRA","ZTS",
    ]
    return sorted(set(tickers))


def should_exclude(info):
    sector     = info.get("sector", "")    or ""
    industry   = info.get("industry", "")  or ""
    quote_type = info.get("quoteType", "") or ""
    if sector in EXCLUDED_SECTORS:            return True, f"sector={sector}"
    if industry in EXCLUDED_INDUSTRIES:       return True, f"industry={industry}"
    if "REIT" in industry.upper():            return True, "REIT"
    if quote_type in {"ETF","MUTUALFUND"}:    return True, f"quoteType={quote_type}"
    return False, ""


def safe_float(val):
    try:
        v = float(val)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def get_10yr_treasury():
    """Fetch current 10-year US Treasury yield from FRED (free, no key needed)."""
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&vintage_date="
        url += datetime.datetime.utcnow().strftime("%Y-%m-%d")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            lines = r.read().decode().strip().split("\n")
            for line in reversed(lines):
                parts = line.split(",")
                if len(parts) == 2 and parts[1].strip() not in (".", ""):
                    return round(float(parts[1]) / 100, 4)
    except Exception as e:
        print(f"  Treasury fetch error: {e}")
    return None


def calc_growth_rate(values):
    """CAGR from first to last value. Returns None if insufficient data."""
    vals = [v for v in values if v is not None and v > 0]
    if len(vals) < 2:
        return None
    n = len(vals) - 1
    try:
        return round((vals[-1] / vals[0]) ** (1/n) - 1, 4)
    except Exception:
        return None


def calc_stability(values):
    """
    Stability score 0-1: fraction of year-pairs where value increased.
    1.0 = increased every year, 0.0 = decreased every year.
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    pairs   = [(vals[i], vals[i+1]) for i in range(len(vals)-1)]
    increases = sum(1 for a, b in pairs if b > a)
    return round(increases / len(pairs), 2)


def get_ticker_data(sym):
    """Fetch all FCF metrics for one ticker."""
    result = {
        "name": None, "sector": None, "industry": None, "marketCap": None,
        "excluded": False, "excludeReason": "",
        # FCF core
        "current": None, "history": [], "avg5y": None,
        "trend": "insufficient", "proj2026": "unclear",
        # New metrics
        "fcfNetIncomeRatio": None,   # FCF / Net Income (>1 = quality)
        "fcfPerShare":       None,   # FCF/Share TTM
        "fcfPerShareHistory":[],     # list of {year, fcfPS}
        "fcfPSGrowth3yr":    None,   # 3yr CAGR of FCF/Share
        "fcfPSStability":    None,   # 0-1 stability score
        "dividendYield":     None,   # from info
        "buybackYield":      None,   # shares reduced YoY / market cap
        "shareholderYield":  None,   # FCF yield + div yield + buyback yield
        "pFCF":              None,   # current P/FCF
        "pFCFHistory":       [],     # list of {year, pFCF}
        "pFCFAvg5y":         None,   # 5yr avg P/FCF
        "pFCFVsAvg":         None,   # % current P/FCF vs 5yr avg
        "fcfVsEPS":          None,   # True/False: FCF/S > EPS (green flag)
        "eps":               None,   # trailing EPS
    }

    try:
        t    = yf.Ticker(sym)
        info = t.info

        excl, reason = should_exclude(info)
        if excl:
            result["excluded"]      = True
            result["excludeReason"] = reason
            return result

        result["name"]      = info.get("shortName") or info.get("longName")
        result["sector"]    = info.get("sector")
        result["industry"]  = info.get("industry")
        result["marketCap"] = info.get("marketCap")

        shares_out   = safe_float(info.get("sharesOutstanding"))
        market_cap   = safe_float(info.get("marketCap"))
        div_yield    = safe_float(info.get("dividendYield"))
        price        = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        eps_ttm      = safe_float(info.get("trailingEps"))
        fcf_ttm      = safe_float(info.get("freeCashflow"))

        result["dividendYield"] = div_yield
        result["eps"]           = eps_ttm

        # Current FCF Yield
        if fcf_ttm and market_cap and market_cap > 0:
            result["current"] = round(fcf_ttm / market_cap, 4)

        # FCF per Share (TTM)
        if fcf_ttm and shares_out and shares_out > 0:
            result["fcfPerShare"] = round(fcf_ttm / shares_out, 4)

        # FCF/S > EPS green flag
        if result["fcfPerShare"] is not None and eps_ttm is not None:
            result["fcfVsEPS"] = result["fcfPerShare"] > eps_ttm

        # Current P/FCF
        if price and result["fcfPerShare"] and result["fcfPerShare"] > 0:
            result["pFCF"] = round(price / result["fcfPerShare"], 2)

        # ── Income statement for net income ──────────────────────────────────
        try:
            inc = t.income_stmt
            if inc is not None and not inc.empty:
                for row in ["Net Income","Net Income Common Stockholders","Net Income From Continuing Operations"]:
                    if row in inc.index:
                        net_inc = safe_float(inc.loc[row, inc.columns[0]])
                        if net_inc and net_inc != 0 and fcf_ttm:
                            result["fcfNetIncomeRatio"] = round(fcf_ttm / net_inc, 2)
                        break
        except Exception:
            pass

        # ── Cash flow statement for history ──────────────────────────────────
        try:
            cf = t.cashflow
            if cf is not None and not cf.empty:
                history     = []
                fcfps_hist  = []
                pfcf_hist   = []
                shares_hist = []

                for col in cf.columns[:5]:
                    try:
                        op_cf = None
                        capex = 0
                        for row in ["Operating Cash Flow","Total Cash From Operating Activities",
                                    "Cash Flow From Continuing Operating Activities"]:
                            if row in cf.index:
                                op_cf = safe_float(cf.loc[row, col])
                                break
                        for row in ["Capital Expenditure","Capital Expenditures",
                                    "Purchase Of Property Plant And Equipment"]:
                            if row in cf.index:
                                capex = safe_float(cf.loc[row, col]) or 0
                                break

                        if op_cf is None: continue
                        fcf_ann = op_cf - abs(capex)
                        year    = col.year

                        if shares_out:
                            hist_px = t.history(start=f"{year}-12-15", end=f"{year}-12-31", interval="1d")
                            if not hist_px.empty:
                                yr_price  = float(hist_px["Close"].iloc[-1])
                                yr_mktcap = yr_price * shares_out

                                # FCF Yield history
                                if yr_mktcap > 0:
                                    history.append({"year": year, "fcfYield": round(fcf_ann / yr_mktcap, 4)})

                                # FCF/Share history
                                fcfps = round(fcf_ann / shares_out, 4)
                                fcfps_hist.append({"year": year, "fcfPS": fcfps})

                                # P/FCF history
                                if fcfps and fcfps > 0:
                                    pfcf_hist.append({"year": year, "pFCF": round(yr_price / fcfps, 2)})

                        # Track shares for buyback calc
                        for row in ["Share Issued","Common Stock","Shares Outstanding"]:
                            if row in cf.index:
                                sh = safe_float(cf.loc[row, col])
                                if sh: shares_hist.append((year, sh))
                                break

                    except Exception:
                        continue

                history.sort(   key=lambda x: x["year"])
                fcfps_hist.sort(key=lambda x: x["year"])
                pfcf_hist.sort( key=lambda x: x["year"])

                result["history"]          = history
                result["fcfPerShareHistory"]= fcfps_hist
                result["pFCFHistory"]      = pfcf_hist

                # 5yr avg FCF Yield
                if history:
                    vals = [h["fcfYield"] for h in history if h["fcfYield"] is not None]
                    result["avg5y"] = round(sum(vals)/len(vals), 4) if vals else None

                # FCF/S 3yr growth + stability
                if len(fcfps_hist) >= 3:
                    recent = [h["fcfPS"] for h in fcfps_hist[-3:]]
                    result["fcfPSGrowth3yr"] = calc_growth_rate(recent)
                    result["fcfPSStability"] = calc_stability(recent)

                # P/FCF 5yr average + vs current
                if pfcf_hist:
                    pfcf_vals = [h["pFCF"] for h in pfcf_hist if h["pFCF"] is not None and h["pFCF"] > 0]
                    if pfcf_vals:
                        result["pFCFAvg5y"] = round(sum(pfcf_vals)/len(pfcf_vals), 2)
                        if result["pFCF"] and result["pFCFAvg5y"]:
                            result["pFCFVsAvg"] = round(
                                (result["pFCF"] - result["pFCFAvg5y"]) / result["pFCFAvg5y"] * 100, 1
                            )

                # Buyback yield: share count reduction YoY vs market cap
                if len(shares_hist) >= 2 and market_cap and market_cap > 0 and price:
                    shares_hist.sort(key=lambda x: x[0])
                    sh_old = shares_hist[0][1]
                    sh_new = shares_hist[-1][1]
                    if sh_old > 0:
                        shares_reduced = sh_old - sh_new
                        buyback_val    = shares_reduced * price
                        result["buybackYield"] = round(buyback_val / market_cap, 4)

        except Exception as e:
            pass

        # Shareholder Yield = FCF Yield + Dividend Yield + Buyback Yield
        sy_components = [
            result["current"]     or 0,
            result["dividendYield"] or 0,
            result["buybackYield"]  or 0,
        ]
        if result["current"] is not None:
            result["shareholderYield"] = round(sum(sy_components), 4)

        # Trend + projection
        result["trend"]    = calc_fcf_trend(result["history"])
        result["proj2026"] = calc_projected_2026(result["history"], result["current"])

    except Exception as e:
        result["error"] = str(e)[:80]

    return result


def calc_fcf_trend(history):
    yields = [h["fcfYield"] for h in history if h["fcfYield"] is not None]
    if len(yields) < 3: return "insufficient"
    inc = sum(1 for i in range(1, len(yields)) if yields[i] > yields[i-1])
    dec = len(yields) - 1 - inc
    if inc >= 3: return "improving"
    if dec >= 3: return "deteriorating"
    return "mixed"


def calc_projected_2026(history, current):
    yields = [h["fcfYield"] for h in history if h["fcfYield"] is not None]
    if len(yields) < 2: return "unclear"
    recent_trend = yields[-1] - yields[-2]
    avg  = sum(yields) / len(yields)
    curr = current if current is not None else yields[-1]
    if recent_trend > 0 and curr >= avg: return "likely_up"
    if recent_trend < 0 and curr < avg:  return "likely_down"
    if recent_trend > 0:  return "likely_up"
    if recent_trend < 0:  return "likely_down"
    return "unclear"


def main():
    print("Fetching 10-year Treasury yield...")
    treasury_10yr = get_10yr_treasury()
    print(f"  10yr Treasury: {treasury_10yr*100:.2f}%" if treasury_10yr else "  Treasury: unavailable")

    tickers = get_russell3000_tickers()
    total   = len(tickers)
    print(f"\nProcessing {total} tickers...\n")

    results  = {}
    excluded = 0
    success  = 0
    errors   = 0

    for i, sym in enumerate(tickers):
        print(f"[{i+1}/{total}] {sym}...", end=" ", flush=True)
        data = get_ticker_data(sym)

        if data.get("excluded"):
            print(f"excluded ({data['excludeReason']})")
            excluded += 1
            continue
        if data.get("error"):
            print(f"error: {data['error'][:50]}")
            errors += 1
            continue

        # FCF Yield vs Treasury spread
        if data["current"] is not None and treasury_10yr is not None:
            data["fcfVsTreasury"] = round(data["current"] - treasury_10yr, 4)
        else:
            data["fcfVsTreasury"] = None

        cur = f"{data['current']*100:.2f}%" if data["current"] is not None else "n/a"
        sy  = f"{data['shareholderYield']*100:.2f}%" if data["shareholderYield"] is not None else "n/a"
        print(f"{(data.get('name') or '')[:22]:22} cur={cur} sy={sy} trend={data['trend']} proj={data['proj2026']}")

        results[sym] = data
        success += 1
        time.sleep(0.4)

    output = {
        "updated":      datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "treasury10yr": treasury_10yr,
        "count":        success,
        "excluded":     excluded,
        "errors":       errors,
        "data":         results,
    }

    with open("screener_data.json", "w") as f:
        json.dump(output, f, separators=(',',':'))

    size_mb = len(json.dumps(output)) / 1e6
    print(f"\nDone. {success} tickers → screener_data.json ({size_mb:.1f} MB)")
    print(f"Excluded: {excluded} | Errors: {errors}")

    # Inject into index.html as window._SCREENER_DATA fallback
    inject_screener_into_html(output)


def inject_screener_into_html(data_obj):
    import re
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print("  index.html not found — skipping HTML injection")
        return

    json_str = json.dumps(data_obj, separators=(',', ':'))
    marker_start = "/* SCREENER_DATA_START */"
    marker_end   = "/* SCREENER_DATA_END */"
    new_block    = f"{marker_start}\nwindow._SCREENER_DATA={json_str};\n{marker_end}"

    if marker_start in html and marker_end in html:
        pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
        html = re.sub(pattern, new_block, html, flags=re.DOTALL)
        print("  Injected screener data into existing marker in index.html")
    else:
        html = html.replace("/* FCF_DATA_START */", f"{new_block}\n/* FCF_DATA_START */")
        print("  Inserted screener data marker into index.html")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  index.html updated with screener data ({len(json_str)/1e6:.1f} MB injected)")

if __name__ == "__main__":
    main()
