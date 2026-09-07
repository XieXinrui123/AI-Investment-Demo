#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch full A-share annual inputs for the frozen RRI -> Financial Reporting Quality test.

Data source: Eastmoney datacenter public API.
Annual years: configurable, default 2013-2025.
Universe: Shanghai/Shenzhen A-shares; Beijing excluded.

Required Modified Jones fields:
- TOTAL_ASSETS
- TOTAL_LIABILITIES
- MONETARYFUNDS
- ACCOUNTS_RECE
- FIXED_ASSET
- TOTAL_OPERATE_INCOME
- NETPROFIT
- NETCASH_OPERATE
- annual industry from RPT_LICO_FN_CPD

This script only fetches/normalizes data. It does NOT read RRI outcomes or run regressions.
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
import numpy as np
import pandas as pd
import requests

BASE = "https://datacenter-web.eastmoney.com/api/data/v1/get"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"

REPORTS = {
    "balance": {"reportName": "RPT_DMSK_FN_BALANCE", "date_field": "REPORT_DATE", "columns": ["SECURITY_CODE","SECURITY_NAME_ABBR","REPORT_DATE","TOTAL_ASSETS","TOTAL_LIABILITIES","MONETARYFUNDS","ACCOUNTS_RECE","FIXED_ASSET","CIP"]},
    "income": {"reportName": "RPT_DMSK_FN_INCOME", "date_field": "REPORT_DATE", "columns": ["SECURITY_CODE","SECURITY_NAME_ABBR","REPORT_DATE","TOTAL_OPERATE_INCOME","NETPROFIT","PARENT_NETPROFIT"]},
    "cashflow": {"reportName": "RPT_DMSK_FN_CASHFLOW", "date_field": "REPORT_DATE", "columns": ["SECURITY_CODE","SECURITY_NAME_ABBR","REPORT_DATE","NETCASH_OPERATE"]},
    "industry": {"reportName": "RPT_LICO_FN_CPD", "date_field": "REPORTDATE", "columns": "ALL"},
}

def norm_code(x):
    s = re.sub(r"\D", "", str(x or ""))
    return s[-6:].zfill(6) if s else ""

def is_hs_a(code):
    c = norm_code(code)
    return c.startswith(("000","001","002","003","300","301")) or c.startswith(("600","601","603","605","688","689"))

def get_json(session, params, retries=5, timeout=25):
    last = None
    for k in range(retries):
        try:
            r = session.get(BASE, params=params, timeout=timeout)
            r.raise_for_status()
            obj = r.json()
            if not obj.get("success", False) and obj.get("result") is None:
                raise RuntimeError(f"Eastmoney API error: {obj}")
            return obj
        except Exception as e:
            last = e
            time.sleep(min(1.5 * (k+1), 8))
    raise RuntimeError(f"Eastmoney failed after {retries} retries: {last}")

def fetch_report_year(session, kind, year, cache_dir, page_size=500):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = cache_dir / f"{kind}_{year}.csv"
    if cp.exists():
        return pd.read_csv(cp, dtype={"SECURITY_CODE":str})
    spec = REPORTS[kind]
    date = f"{year}-12-31"
    if kind == "industry":
        filt = f"(REPORTDATE='{date}')"
        sort_cols = "UPDATE_DATE,SECURITY_CODE"
    else:
        filt = '(SECURITY_TYPE_CODE in ("058001001","058001008"))' '(TRADE_MARKET_CODE!="069001017")' f"({spec['date_field']}='{date}')"
        sort_cols = "NOTICE_DATE,SECURITY_CODE"
    cols = spec["columns"] if isinstance(spec["columns"], str) else ",".join(spec["columns"])
    params = {"sortColumns": sort_cols,"sortTypes": "-1,-1","pageSize": str(page_size),"pageNumber": "1","reportName": spec["reportName"],"columns": cols,"filter": filt,"source": "WEB","client": "WEB"}
    first = get_json(session, params)
    result = first.get("result") or {}
    pages = int(result.get("pages") or 0)
    rows = list(result.get("data") or [])
    for page in range(2, pages + 1):
        params["pageNumber"] = str(page)
        obj = get_json(session, params)
        rows.extend(((obj.get("result") or {}).get("data") or []))
        time.sleep(0.08)
    df = pd.DataFrame(rows)
    if df.empty:
        print(f"WARN {kind} {year}: empty")
        df.to_csv(cp, index=False, encoding="utf-8-sig")
        return df
    if "SECURITY_CODE" in df.columns:
        df["SECURITY_CODE"] = df["SECURITY_CODE"].astype(str).map(norm_code)
        df = df[df["SECURITY_CODE"].map(is_hs_a)].copy()
    df.to_csv(cp, index=False, encoding="utf-8-sig")
    print(f"{kind} {year}: {len(df):,} rows")
    return df

def choose_industry_column(df):
    preferred = ["INDUSTRY","INDUSTRY_NAME","INDUSTRY_NAME_ABBR","INDUSTRY_BOARD","INDUSTRY_NEW","INDUSTRY_NAME_NEW"]
    for c in preferred:
        if c in df.columns and df[c].notna().sum() > 0:
            return c
    candidates = [c for c in df.columns if "INDUSTRY" in str(c).upper()]
    scored = []
    for c in candidates:
        s = df[c].dropna().astype(str)
        if len(s): scored.append((s.str.len().median(), c))
    if scored: return sorted(scored, reverse=True)[0][1]
    raise RuntimeError(f"Could not identify industry column. Columns include: {list(df.columns)}")

def first_existing(df, candidates):
    for c in candidates:
        if c in df.columns: return c
    return None

def normalize_year(year, bal, inc, cf, ind):
    def pick(df, mapping):
        out = pd.DataFrame()
        if df is None or df.empty: return out
        for src, dst in mapping.items(): out[dst] = df[src] if src in df.columns else np.nan
        return out
    b = pick(bal, {"SECURITY_CODE":"firm_code","SECURITY_NAME_ABBR":"firm_name","TOTAL_ASSETS":"total_assets","TOTAL_LIABILITIES":"total_liabilities","MONETARYFUNDS":"cash","ACCOUNTS_RECE":"accounts_receivable","FIXED_ASSET":"fixed_assets","CIP":"construction_in_progress"})
    i = pick(inc, {"SECURITY_CODE":"firm_code","SECURITY_NAME_ABBR":"firm_name_income","TOTAL_OPERATE_INCOME":"operating_revenue","NETPROFIT":"net_profit","PARENT_NETPROFIT":"parent_net_profit"})
    c = pick(cf, {"SECURITY_CODE":"firm_code","SECURITY_NAME_ABBR":"firm_name_cash","NETCASH_OPERATE":"net_operating_cashflow"})
    if ind is None or ind.empty:
        d = pd.DataFrame(columns=["firm_code","industry_name"])
    else:
        code_col = first_existing(ind, ["SECURITY_CODE","SECURITYCODE"])
        if not code_col: raise RuntimeError(f"Industry table lacks stock code: {list(ind.columns)}")
        industry_col = choose_industry_column(ind)
        d = pd.DataFrame({"firm_code": ind[code_col].astype(str).map(norm_code),"industry_name": ind[industry_col]})
        d = d[d["firm_code"].map(is_hs_a)]
        d["industry_name"] = d["industry_name"].replace({"":np.nan,"nan":np.nan,"None":np.nan})
    pieces = [x for x in [b,i,c] if not x.empty]
    if not pieces: return pd.DataFrame()
    out = pieces[0]
    for x in pieces[1:]: out = out.merge(x, on="firm_code", how="outer")
    out = out.merge(d.drop_duplicates("firm_code"), on="firm_code", how="left")
    out["fiscal_year"] = int(year)
    if "firm_name" not in out.columns: out["firm_name"] = np.nan
    for alt in ["firm_name_income","firm_name_cash"]:
        if alt in out.columns: out["firm_name"] = out["firm_name"].fillna(out[alt])
    out = out.drop(columns=[c for c in ["firm_name_income","firm_name_cash"] if c in out], errors="ignore")
    num = ["total_assets","total_liabilities","cash","accounts_receivable","fixed_assets","construction_in_progress","operating_revenue","net_profit","parent_net_profit","net_operating_cashflow"]
    for col in num:
        if col in out: out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out[out["firm_code"].map(is_hs_a)].copy()
    return out.sort_values("firm_code").drop_duplicates(["firm_code","fiscal_year"], keep="last")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--start-year", type=int, default=2013); ap.add_argument("--end-year", type=int, default=2025); ap.add_argument("--outdir", default="ashare_modified_jones_inputs"); args = ap.parse_args()
    outdir = Path(args.outdir); cache = outdir / "cache"; outdir.mkdir(parents=True, exist_ok=True)
    session = requests.Session(); session.headers.update({"User-Agent": UA,"Referer": "https://data.eastmoney.com/","Accept": "application/json,text/plain,*/*"})
    all_years = []; status = []
    for y in range(args.start_year, args.end_year + 1):
        try:
            bal = fetch_report_year(session, "balance", y, cache); inc = fetch_report_year(session, "income", y, cache); cf = fetch_report_year(session, "cashflow", y, cache); ind = fetch_report_year(session, "industry", y, cache)
            panel = normalize_year(y, bal, inc, cf, ind); panel.to_csv(outdir/f"annual_{y}.csv", index=False, encoding="utf-8-sig"); all_years.append(panel); status.append({"fiscal_year":y,"status":"OK","rows":len(panel)})
        except Exception as e:
            print(f"ERROR {y}: {e}"); status.append({"fiscal_year":y,"status":"ERROR","error":str(e)})
    pd.DataFrame(status).to_csv(outdir/"FETCH_STATUS.csv", index=False, encoding="utf-8-sig")
    if not all_years: raise SystemExit("No years fetched.")
    full = pd.concat(all_years, ignore_index=True).drop_duplicates(["firm_code","fiscal_year"], keep="last")
    path = outdir/f"FULL_A_SHARE_MODIFIED_JONES_INPUTS_{args.start_year}_{args.end_year}.csv"; full.to_csv(path, index=False, encoding="utf-8-sig")
    req = ["total_assets","accounts_receivable","fixed_assets","operating_revenue","net_profit","net_operating_cashflow","industry_name"]
    qc = {"rows": int(len(full)),"firms": int(full["firm_code"].nunique()),"years": sorted(full["fiscal_year"].dropna().astype(int).unique().tolist()),"coverage": {c: float(full[c].notna().mean()) if c in full else 0.0 for c in req}}
    (outdir/"FETCH_QC.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8"); print(json.dumps(qc, ensure_ascii=False, indent=2)); print(path)

if __name__ == "__main__": main()
