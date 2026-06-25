#!/usr/bin/env python3
"""
Weekly GitHub Actions script — Russell 3000 FCF Screener
Fetches Russell 3000 tickers from iShares IWV ETF holdings CSV,
excludes Financials, REITs, and Insurance, then pulls FCF metrics.
Writes results to screener_data.json and injects into index.html.
"""

import json, time, datetime, sys, math, re, urllib.request, csv, io

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed."); sys.exit(1)

EXCLUDED_SECTORS = {"Financial Services", "Financials"}
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
    """Fetch Russell 3000 components from iShares IWV ETF holdings CSV."""
    print("Fetching Russell 3000 tickers from iShares IWV holdings...")
    tickers = []
    try:
        url = "https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax?fileType=csv&fileName=IWV_holdings&dataType=fund"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.ishares.com"
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8', errors='ignore')

        # iShares CSV has header rows before the actual data — find the ticker column
        lines = raw.split('\n')
        data_start = 0
        for i, line in enumerate(lines):
            if 'Ticker' in line and 'Name' in line:
                data_start = i
                break

        reader = csv.DictReader(lines[data_start:])
        for row in reader:
            ticker = (row.get('Ticker') or row.get('ticker') or '').strip()
            asset_class = (row.get('Asset Class') or '').strip()
            # Only include equities, skip cash/futures/options
            if ticker and ticker != '-' and asset_class in ('Equity', 'equity', ''):
                # Clean up ticker (remove suffixes like .L for London)
                if '.' not in ticker or ticker in ('BRK.B', 'BF.B'):
                    tickers.append(ticker)

        print(f"  Fetched {len(tickers)} tickers from iShares IWV")
    except Exception as e:
        print(f"  iShares fetch failed: {e} — falling back to curated list")
        tickers = get_fallback_tickers()

    if len(tickers) < 100:
        print("  Too few tickers from iShares, using fallback list")
        tickers = get_fallback_tickers()

    return sorted(set(tickers))


def get_fallback_tickers():
    """S&P 500 + S&P 400 MidCap + S&P 600 SmallCap — ~1500 tickers approximating Russell 3000."""
    sp500 = "MMM,AOS,ABT,ABBV,ACN,ADBE,ADI,ADM,ADP,ADSK,AEE,AEP,AES,AFL,A,APD,AKAM,ALK,ALB,ARE,ALGN,ALLE,LNT,ALL,GOOGL,GOOG,MO,AMZN,AMCR,AMD,AIG,AMT,AWK,AMP,ABC,AME,AMGN,APH,ANSS,AON,APA,AAPL,AMAT,APTV,ACGL,ANET,AJG,AIZ,T,ATO,AZO,AVB,AVY,AXON,BKR,BALL,BAC,BBWI,BAX,BDX,WRB,BRK.B,BBY,BIO,BIIB,BLK,BX,BA,BWA,BSX,BMY,AVGO,BR,BRO,BF.B,BLDR,BG,BK,CHRW,CDNS,CZR,CPT,CPB,COF,CAH,KMX,CCL,CARR,CTLT,CAT,CBOE,CBRE,CDW,CE,COR,CNC,CNP,CF,SCHW,CHTR,CVX,CMG,CB,CHD,CI,CINF,CTAS,CSCO,C,CFG,CLX,CME,CMS,KO,CTSH,CL,CMCSA,CMA,CAG,COP,ED,STZ,CEG,COO,CPRT,GLW,CTVA,CSGP,COST,CTRA,CRWD,CCI,CSX,CMI,CVS,DHI,DHR,DRI,DVA,DE,DAL,DVN,DXCM,FANG,DLR,DFS,DG,DLTR,D,DPZ,DOV,DOW,DTE,DUK,DD,EMN,ETN,EBAY,ECL,EIX,EW,EA,ELV,LLY,EMR,ENPH,ETR,EOG,EPAM,EQT,EFX,EQIX,EQR,ESS,EL,ETSY,EG,EVRG,ES,EXC,EXPE,EXPD,EXR,XOM,FFIV,FDS,FICO,FAST,FRT,FDX,FIS,FITB,FSLR,FE,FI,FMC,F,FTNT,FTV,FOXA,FOX,BEN,FCX,GRMN,IT,GEHC,GEN,GNRC,GD,GE,GIS,GM,GPC,GILD,GS,HAL,HIG,HAS,HCA,HSIC,HSY,HES,HPE,HLT,HOLX,HD,HON,HRL,HST,HWM,HPQ,HUBB,HUM,HBAN,HII,IBM,IEX,IDXX,ITW,ILMN,INCY,IR,INTC,ICE,IFF,IP,IPG,INTU,ISRG,IVZ,INVH,IQV,IRM,JBHT,JKHY,J,JNJ,JCI,JPM,JNPR,K,KVUE,KDP,KEY,KEYS,KMB,KIM,KMI,KLAC,KHC,KR,LHX,LH,LRCX,LW,LVS,LDOS,LEN,LIN,LYV,LKQ,LMT,L,LOW,LULU,LYB,MTB,MRO,MPC,MKTX,MAR,MMC,MLM,MAS,MA,MKC,MCD,MCK,MDT,MRK,META,MET,MTD,MGM,MCHP,MU,MSFT,MAA,MRNA,MHK,MOH,TAP,MDLZ,MPWR,MNST,MCO,MS,MOS,MSI,MSCI,NDAQ,NTAP,NFLX,NEM,NWSA,NWS,NEE,NKE,NI,NSC,NTRS,NOC,NCLH,NRG,NUE,NVDA,NVR,NXPI,ORLY,OXY,ODFL,OMC,ON,OKE,ORCL,OTIS,PCAR,PKG,PANW,PH,PAYX,PAYC,PYPL,PNR,PEP,PFE,PCG,PM,PSX,PNW,PNC,POOL,PPG,PPL,PFG,PG,PGR,PLD,PRU,PEG,PTC,PSA,PHM,PWR,QCOM,DGX,RL,RJF,RTX,O,REG,REGN,RF,RSG,RMD,ROK,ROL,ROP,ROST,RCL,SPGI,CRM,SBAC,SLB,STX,SEE,SRE,NOW,SHW,SPG,SWKS,SJM,SNA,SO,LUV,SWK,SBUX,STT,STE,SYK,SYF,SNPS,SYY,TMUS,TROW,TTWO,TPR,TRGP,TGT,TEL,TDY,TFX,TER,TSLA,TXN,TXT,TMO,TJX,TSCO,TT,TDG,TRV,TRMB,TFC,TYL,TSN,USB,UDR,ULTA,UNP,UAL,UPS,URI,UNH,UHS,VLO,VTR,VRSN,VRSK,VZ,VRTX,VTRS,VMC,GWW,WAB,WBA,WMT,DIS,WBD,WM,WAT,WEC,WFC,WELL,WST,WDC,WHR,WMB,WTW,WYNN,XEL,XYL,YUM,ZBRA,ZBH,ZTS"
    sp400 = "ACCO,ACM,AGCO,ASGN,ASH,ATR,AVA,AVNT,AWR,AX,AXL,BCO,BJ,BRC,BRX,BSY,BWA,CABO,CALX,CAR,CASY,CBRL,CBT,CBU,CFLT,CGNX,CHE,CHRD,CMC,CMP,CNK,CNO,COLB,COLM,CPF,CPRI,CR,CRI,CRL,CSL,CSWI,CW,CWT,DCI,DEI,DKS,DLB,DLX,DOCN,DORM,DRH,DV,DY,EAT,EEFT,EGP,EHC,ELF,ENSG,ENVA,EPC,ESE,ESNT,EXP,EXPO,FAF,FBP,FHI,FIX,FN,FORM,FUL,GATX,GBX,GFF,GMS,GPOR,GRC,HAE,HBI,HCC,HI,HL,HLNE,HLX,HNI,HP,HURN,HWKN,HXL,IDCC,IDA,IESC,INGR,INSP,ITT,JBL,JELD,JJSF,JLL,JOE,KBH,KGS,KNF,KNSL,KNX,KRC,KTB,LANC,LBRT,LII,LKFN,LNC,LPX,LSTR,LTC,LXFR,LXP,MBC,MCY,MDC,MEDP,MGEE,MGNI,MIDD,MKSI,MLI,MMSI,MMS,MOG.A,MRC,MRCY,MSA,MSM,MTH,MTRN,MTX,NARI,NBHC,NEU,NFG,NHC,NJR,NOV,NOVT,NUS,NVT,NX,OEC,OFG,OII,OLN,OMCL,OMF,ONTO,ORA,OTTR,OUT,OXM,PATK,PB,PBH,PDCO,PEN,PFBC,PI,PINC,PLXS,PLUS,PNM,PNFP,POR,POWL,PPBI,PRIM,PRKS,PSN,PVH,RAMP,RBC,RDN,REX,RLI,ROAD,RS,RWT,RXO,SAIA,SANM,SBCF,SBH,SCI,SCSC,SEIC,SFL,SFM,SHAK,SIG,SITC,SKYW,SLG,SM,SMG,SMTC,SNDR,SNX,SON,SSD,STAG,STRA,SUM,SXT,SYBT,TALO,TDC,THG,TKR,TMDX,TMHC,TNL,TOL,TPH,TREX,TRN,TTC,TXRH,UCB,UCTT,UE,UGI,UMBF,UNVR,VAC,VC,VFC,VIRT,VIVO,VLY,VMI,VNO,VOYA,VSH,WBS,WERN,WGO,WHR,WK,WLDN,WLY,WMS,WOR,WPC,WSO,WTFC,XPO,ZI"
    sp600 = "AAON,ABCB,ABM,ACLS,ACNB,ADMA,AEIS,AEL,AGFS,AHCO,AIR,AIT,ALEC,ALEX,ALRM,ALTG,AMCX,AMSF,AMWD,ANDE,ANN,APEI,APPF,ARCB,ARKO,AROC,ASIX,ASND,ATNI,ATRI,AUBN,AVNS,AVNT,AVNW,AVO,AX,AZZ,BAND,BANF,BANR,BCPC,BECN,BFC,BFST,BJRI,BLBD,BLMN,BNED,BNL,BOOT,BPMC,BRBR,BRC,BRKL,BSM,BSRR,BUSE,BWXT,BXC,CAKE,CAMP,CARG,CASH,CASS,CATO,CBSH,CDMO,CDNA,CENT,CENX,CEVA,CFFI,CHH,CHRS,CHS,CHUY,CIVB,CIX,CLDT,CLFD,CMC,COBZ,COLB,CONN,CORE,CORT,CPSS,CRMT,CROX,CTBI,CTLP,CTRE,CUZ,CVBF,CVLG,CVLT,CWH,DAN,DCPH,DDS,DENN,DGII,DIOD,DLB,DLX,DOMO,DORM,DRH,DY,EAT,EBIX,ECPG,EEFT,EGBN,EGP,EIG,EML,ENSG,EPC,EPRT,ESE,ESNT,ETSY,EVBG,EVER,EVRI,EWBC,EZPW,FARO,FCF,FCFS,FELE,FFBC,FFIN,FIX,FLNC,FLXS,FMBH,FMNB,FN,FNKO,FORM,FOUR,FRME,FWRD,GBX,GCO,GES,GIII,GMS,GPRO,GVA,HAFC,HASI,HBI,HCI,HCSG,HESM,HFWA,HI,HIBB,HL,HLNE,HNI,HOLX,HOV,HP,HRT,HSII,HTBK,HURN,HVT,HWKN,HXL,IBCP,IBTX,ICFI,ICLR,IDCC,IIN,IMXI,INDB,INGN,INS,INSE,IOSP,IRT,ISNS,JACK,JBSS,JELD,JILL,JJSF,JOE,JOBY,KAI,KALU,KAMN,KAR,KBH,KFY,KGS,KIRK,KMT,KNSA,KREF,KRG,KSS,KTB,KTOS,LBRT,LCII,LDI,LGF.A,LGF.B,LGIH,LGND,LII,LINC,LKFN,LNN,LOB,LOPE,LOVE,LRN,LSCC,LSTR,LUNA,MANT,MATX,MBUU,MCB,MDU,MEDP,MG,MGEE,MGNI,MHO,MIDD,MLKN,MMSI,MNKD,MOD,MRTN,MSA,MSEX,MTH,MTRN,MTRX,MWA,NABL,NBTB,NEU,NFG,NJR,NMIH,NNN,NRC,NRP,NSP,NTCT,NTIC,NUE,NVST,NVT,NX,NXRT,OCFC,OCUL,OFG,OII,OLLI,OLP,OMCL,ORRF,OTTR,OUT,PACK,PARR,PATK,PDCE,PFBC,PFSI,PGTI,PIPR,PLAB,PLXS,PPBI,PRDO,PRGS,PRTH,PRTS,PURE,QNST,QLYS,RDNT,RES,REX,RICK,RMNI,RNST,ROG,RRGB,RST,RUSHA,RUTH,RWT,RYAM,SAFE,SANM,SASR,SBCF,SBH,SBSI,SCHL,SCI,SCSC,SEIC,SFBS,SFNC,SHAK,SHBI,SHCO,SHYF,SIGI,SILC,SKYW,SLG,SLGN,SMBK,SMPL,SMTC,SNBR,SNEX,SPTN,SRC,STGW,STL,STRA,STRL,SUM,SUPN,SWKS,SYBT,TBBK,TCBK,TDOC,TGTX,TILE,TMUS,TPIC,TRMK,TRNO,TROW,TRST,TSRI,TTMI,TVTX,TXMD,TYL,UBSI,UCBI,UCTT,UE,UFCS,UFPI,UFPT,UMBF,UNIT,USAP,USM,UTHR,UTMD,UVE,UVV,VBTX,VC,VCEL,VIAD,VIRT,VIVO,VLY,VMI,VSCO,VSH,VTOL,WABC,WASH,WEST,WETF,WEYS,WGO,WHD,WING,WKME,WLDN,WOR,WRBY,WSC,WTS,WWD,XNCR,XPO,ZI"
    all_t = set()
    for group in [sp500, sp400, sp600]:
        for t in group.split(","):
            t = t.strip()
            if t: all_t.add(t)
    # Add additional tickers not in S&P indices
    extra = ["HIMS","GRRR","IONQ","QBTS","ONDS","PEGA","ZETA","ZVRA","BIDU","BYDDY",
             "JD","SE","ASML","CRM","RBLX","U","TTWO","EA","TTD","APP","W","ETSY",
             "CHWY","ONON","CROX","SKX","DECK","SPGI","MSCI","EFX","TRU","FICO",
             "PAYC","PAYX","ADP","CDAY","PCTY","MTZ","PWR","GNRC","MRSH","OSCR",
             "DDOG","ZS","CRWD","NET","MDB","HUBS","TEAM","VEEV","SNOW","WDAY",
             "NOW","ADSK","PANW","FTNT","OKTA","DOCU","ZM","COIN","HOOD","SOFI",
             "AFRM","UPST","RIVN","LCID","NIO","XPEV","LI","GRAB","GOTO","DKNG",
             "PENN","MGM","WYNN","CZR","LVS","NCLH","CCL","RCL","MAR","HLT","H",
             "ABNB","EXPE","BKNG","UBER","LYFT","DASH","RBLX","SNAP","PINS","RDDT",
             "CELH","HALO","JAZZ","SUPN","PCRX","HRMY","DAWN","PODD","INSP","TNDM"]
    for t in extra:
        all_t.add(t)
    return sorted(all_t)


def should_exclude(info):
    sector     = info.get("sector",    "") or ""
    industry   = info.get("industry",  "") or ""
    quote_type = info.get("quoteType", "") or ""
    if sector in EXCLUDED_SECTORS:         return True, f"sector={sector}"
    if industry in EXCLUDED_INDUSTRIES:    return True, f"industry={industry}"
    if "REIT" in industry.upper():         return True, "REIT"
    if quote_type in {"ETF","MUTUALFUND"}: return True, f"quoteType={quote_type}"
    return False, ""


def safe_float(val):
    try:
        v = float(val)
        return None if math.isnan(v) or math.isinf(v) else v
    except: return None


def get_10yr_treasury():
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
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
    vals = [v for v in values if v is not None and v > 0]
    if len(vals) < 2: return None
    n = len(vals) - 1
    try: return round((vals[-1] / vals[0]) ** (1/n) - 1, 4)
    except: return None


def calc_stability(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 2: return None
    pairs = [(vals[i], vals[i+1]) for i in range(len(vals)-1)]
    increases = sum(1 for a, b in pairs if b > a)
    return round(increases / len(pairs), 2)


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
    if recent_trend > 0: return "likely_up"
    if recent_trend < 0: return "likely_down"
    return "unclear"


def get_ticker_data(sym):
    result = {
        "name": None, "sector": None, "industry": None, "marketCap": None,
        "excluded": False, "excludeReason": "",
        "current": None, "history": [], "avg5y": None,
        "trend": "insufficient", "proj2026": "unclear",
        "fcfNetIncomeRatio": None,
        "fcfPerShare": None, "fcfPerShareHistory": [],
        "fcfPSGrowth3yr": None, "fcfPSStability": None,
        "dividendYield": None, "buybackYield": None, "shareholderYield": None,
        "pFCF": None, "pFCFHistory": [], "pFCFAvg5y": None, "pFCFVsAvg": None,
        "fcfVsEPS": None, "eps": None, "fcfVsTreasury": None,
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

        shares_out = safe_float(info.get("sharesOutstanding"))
        market_cap = safe_float(info.get("marketCap"))
        div_yield  = safe_float(info.get("dividendYield"))
        price      = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        eps_ttm    = safe_float(info.get("trailingEps"))
        fcf_ttm    = safe_float(info.get("freeCashflow"))

        result["dividendYield"] = div_yield
        result["eps"]           = eps_ttm

        if fcf_ttm and market_cap and market_cap > 0:
            result["current"] = round(fcf_ttm / market_cap, 4)

        if fcf_ttm and shares_out and shares_out > 0:
            result["fcfPerShare"] = round(fcf_ttm / shares_out, 4)

        if result["fcfPerShare"] is not None and eps_ttm is not None:
            result["fcfVsEPS"] = result["fcfPerShare"] > eps_ttm

        if price and result["fcfPerShare"] and result["fcfPerShare"] > 0:
            result["pFCF"] = round(price / result["fcfPerShare"], 2)

        # Income statement for net income
        try:
            inc = t.income_stmt
            if inc is not None and not inc.empty:
                for row in ["Net Income","Net Income Common Stockholders",
                            "Net Income From Continuing Operations"]:
                    if row in inc.index:
                        net_inc = safe_float(inc.loc[row, inc.columns[0]])
                        if net_inc and net_inc != 0 and fcf_ttm:
                            result["fcfNetIncomeRatio"] = round(fcf_ttm / net_inc, 2)
                        break
        except: pass

        # Cash flow history
        try:
            cf = t.cashflow
            if cf is not None and not cf.empty:
                history = []; fcfps_hist = []; pfcf_hist = []

                for col in cf.columns[:5]:
                    try:
                        op_cf = None; capex = 0
                        for row in ["Operating Cash Flow","Total Cash From Operating Activities",
                                    "Cash Flow From Continuing Operating Activities"]:
                            if row in cf.index:
                                op_cf = safe_float(cf.loc[row, col]); break
                        for row in ["Capital Expenditure","Capital Expenditures",
                                    "Purchase Of Property Plant And Equipment"]:
                            if row in cf.index:
                                capex = safe_float(cf.loc[row, col]) or 0; break
                        if op_cf is None: continue
                        fcf_ann = op_cf - abs(capex)
                        year    = col.year
                        if shares_out:
                            hist_px = t.history(start=f"{year}-12-15", end=f"{year}-12-31", interval="1d")
                            if not hist_px.empty:
                                yr_price  = float(hist_px["Close"].iloc[-1])
                                yr_mktcap = yr_price * shares_out
                                if yr_mktcap > 0:
                                    history.append({"year": year, "fcfYield": round(fcf_ann / yr_mktcap, 4)})
                                fcfps = round(fcf_ann / shares_out, 4)
                                fcfps_hist.append({"year": year, "fcfPS": fcfps})
                                if fcfps > 0:
                                    pfcf_hist.append({"year": year, "pFCF": round(yr_price / fcfps, 2)})
                    except: continue

                history.sort(key=lambda x: x["year"])
                fcfps_hist.sort(key=lambda x: x["year"])
                pfcf_hist.sort(key=lambda x: x["year"])

                result["history"]            = history
                result["fcfPerShareHistory"] = fcfps_hist
                result["pFCFHistory"]        = pfcf_hist

                if history:
                    vals = [h["fcfYield"] for h in history if h["fcfYield"] is not None]
                    result["avg5y"] = round(sum(vals)/len(vals), 4) if vals else None

                if len(fcfps_hist) >= 3:
                    recent = [h["fcfPS"] for h in fcfps_hist[-3:]]
                    result["fcfPSGrowth3yr"] = calc_growth_rate(recent)
                    result["fcfPSStability"] = calc_stability(recent)

                if pfcf_hist:
                    pfcf_vals = [h["pFCF"] for h in pfcf_hist if h["pFCF"] and h["pFCF"] > 0]
                    if pfcf_vals:
                        result["pFCFAvg5y"] = round(sum(pfcf_vals)/len(pfcf_vals), 2)
                        if result["pFCF"] and result["pFCFAvg5y"]:
                            result["pFCFVsAvg"] = round(
                                (result["pFCF"] - result["pFCFAvg5y"]) / result["pFCFAvg5y"] * 100, 1)

                # Buyback yield
                if len(fcfps_hist) >= 2 and market_cap and market_cap > 0 and price and shares_out:
                    yr_old = fcfps_hist[0]["year"]; yr_new = fcfps_hist[-1]["year"]
                    try:
                        h_old = t.history(start=f"{yr_old}-01-01", end=f"{yr_old}-12-31", interval="3mo")
                        if not h_old.empty:
                            sh_chg = 0
                            try:
                                bs = t.balance_sheet
                                if bs is not None and not bs.empty:
                                    for row in ["Share Issued","Common Stock Equity"]:
                                        if row in bs.index and len(bs.columns) >= 2:
                                            old_sh = safe_float(bs.loc[row, bs.columns[-1]])
                                            new_sh = safe_float(bs.loc[row, bs.columns[0]])
                                            if old_sh and new_sh and old_sh > 0:
                                                sh_chg = (old_sh - new_sh) * price
                                                result["buybackYield"] = round(sh_chg / market_cap, 4)
                                            break
                            except: pass
                    except: pass
        except: pass

        # Shareholder yield
        sy = (result["current"] or 0) + (result["dividendYield"] or 0) + (result["buybackYield"] or 0)
        if result["current"] is not None:
            result["shareholderYield"] = round(sy, 4)

        result["trend"]    = calc_fcf_trend(result["history"])
        result["proj2026"] = calc_projected_2026(result["history"], result["current"])

    except Exception as e:
        result["error"] = str(e)[:80]
    return result


def inject_screener_into_html(data_obj):
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print("  index.html not found — skipping injection"); return

    json_str     = json.dumps(data_obj, separators=(',', ':'))
    marker_start = "/* SCREENER_DATA_START */"
    marker_end   = "/* SCREENER_DATA_END */"
    new_block    = f"{marker_start}\nwindow._SCREENER_DATA={json_str};\n{marker_end}"

    if marker_start in html and marker_end in html:
        pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
        html = re.sub(pattern, new_block, html, flags=re.DOTALL)
        print("  Updated SCREENER_DATA block in index.html")
    else:
        html = html.replace("/* FCF_DATA_START */", f"{new_block}\n/* FCF_DATA_START */")
        print("  Inserted SCREENER_DATA block into index.html")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  index.html updated ({len(json_str)/1e6:.1f} MB injected)")


def main():
    print("Fetching 10-year Treasury yield...")
    treasury_10yr = get_10yr_treasury()
    print(f"  10yr Treasury: {treasury_10yr*100:.2f}%" if treasury_10yr else "  Treasury: unavailable")

    tickers = get_russell3000_tickers()
    total   = len(tickers)
    print(f"\nProcessing {total} tickers...\n")

    results = {}; excluded = 0; success = 0; errors = 0

    for i, sym in enumerate(tickers):
        print(f"[{i+1}/{total}] {sym}...", end=" ", flush=True)
        data = get_ticker_data(sym)

        if data.get("excluded"):
            print(f"excluded ({data['excludeReason']})")
            excluded += 1; continue
        if data.get("error"):
            print(f"error: {data['error'][:50]}")
            errors += 1; continue

        if data["current"] is not None and treasury_10yr is not None:
            data["fcfVsTreasury"] = round(data["current"] - treasury_10yr, 4)

        cur = f"{data['current']*100:.2f}%" if data["current"] is not None else "n/a"
        sy  = f"{data['shareholderYield']*100:.2f}%" if data["shareholderYield"] is not None else "n/a"
        print(f"{(data.get('name') or '')[:22]:22} cur={cur} sy={sy} trend={data['trend']}")

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
    print("Injecting into index.html...")
    inject_screener_into_html(output)

if __name__ == "__main__":
    main()
