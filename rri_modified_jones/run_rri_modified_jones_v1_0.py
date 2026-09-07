#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

MIN_CELL_N = 20
FINANCE_KEYWORDS = ["银行","保险","证券","多元金融","信托","金融服务","期货","券商"]

def norm_code(x):
    s = re.sub(r"\D","",str(x or "")); return s[-6:].zfill(6) if s else ""
def is_finance(name):
    s = str(name); return any(k in s for k in FINANCE_KEYWORDS)
def winsor_by_year(df, cols, p=.01):
    z=df.copy()
    for c in cols:
        if c not in z: continue
        z[c]=z.groupby("fiscal_year")[c].transform(lambda s:s.clip(s.quantile(p),s.quantile(1-p)))
    return z

def construct_da(full):
    x=full.copy(); x["firm_code"]=x["firm_code"].astype(str).map(norm_code); x["fiscal_year"]=pd.to_numeric(x["fiscal_year"],errors="coerce").astype("Int64")
    nums=["total_assets","total_liabilities","cash","accounts_receivable","fixed_assets","operating_revenue","net_profit","net_operating_cashflow"]
    for c in nums: x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.sort_values(["firm_code","fiscal_year"]); g=x.groupby("firm_code",sort=False)
    x["lag_assets"]=g["total_assets"].shift(1); x["lag_revenue"]=g["operating_revenue"].shift(1); x["lag_receivables"]=g["accounts_receivable"].shift(1)
    x["TA"]=(x["net_profit"]-x["net_operating_cashflow"])/x["lag_assets"]; x["inv_assets"]=1.0/x["lag_assets"]
    x["drev_scaled"]=(x["operating_revenue"]-x["lag_revenue"])/x["lag_assets"]; x["drec_scaled"]=(x["accounts_receivable"]-x["lag_receivables"])/x["lag_assets"]; x["ppe_scaled"]=x["fixed_assets"]/x["lag_assets"]
    x["size"]=np.log(x["total_assets"].where(x["total_assets"]>0)); x["leverage"]=x["total_liabilities"]/x["total_assets"]; x["cash_ratio"]=x["cash"]/x["total_assets"]; x["roa"]=x["net_profit"]/x["total_assets"]
    x["finance_industry"]=x["industry_name"].map(is_finance).astype(int); x=x[(x["finance_industry"]==0)&(x["lag_assets"]>0)].copy()
    controls=x[["firm_code","fiscal_year","size","leverage","cash_ratio","roa","industry_name"]].copy()
    x=winsor_by_year(x,["TA","inv_assets","drev_scaled","drec_scaled","ppe_scaled"],.01)
    out=[]; cell_rows=[]
    for (yr,ind),d in x.groupby(["fiscal_year","industry_name"],dropna=True):
        d=d.dropna(subset=["TA","inv_assets","drev_scaled","drec_scaled","ppe_scaled"]).copy(); n=len(d)
        if n<MIN_CELL_N: cell_rows.append({"fiscal_year":yr,"industry_name":ind,"N":n,"status":"DROP_N_LT_20"}); continue
        X=sm.add_constant(d[["inv_assets","drev_scaled","ppe_scaled"]],has_constant="add")
        if np.linalg.matrix_rank(X.to_numpy())<X.shape[1]: cell_rows.append({"fiscal_year":yr,"industry_name":ind,"N":n,"status":"DROP_RANK_DEFICIENT"}); continue
        m=sm.OLS(d["TA"],X).fit(); nda=m.params["const"]+m.params["inv_assets"]*d["inv_assets"]+m.params["drev_scaled"]*(d["drev_scaled"]-d["drec_scaled"])+m.params["ppe_scaled"]*d["ppe_scaled"]
        d["NDA_ModJones"]=nda; d["DA"]=d["TA"]-d["NDA_ModJones"]; d["AbsDA"]=d["DA"].abs(); d["peer_cell_n"]=n; out.append(d)
        cell_rows.append({"fiscal_year":yr,"industry_name":ind,"N":n,"status":"OK","a0":m.params["const"],"a1_inv_assets":m.params["inv_assets"],"a2_drev":m.params["drev_scaled"],"a3_ppe":m.params["ppe_scaled"],"r2":m.rsquared})
    if not out: return pd.DataFrame(),pd.DataFrame(cell_rows),controls
    return pd.concat(out,ignore_index=True),pd.DataFrame(cell_rows),controls

def merge_rri(rri,da,controls):
    r=rri.copy(); r["firm_code"]=r["firm_code"].astype(str).map(norm_code)
    for c in ["rri_year","pre_outcome_year","control_year","outcome_year"]: r[c]=pd.to_numeric(r[c],errors="coerce").astype(int)
    r["RRI10"]=pd.to_numeric(r["AnnualRRI_mean"],errors="coerce")/10.0; r["ln_nq"]=np.log1p(pd.to_numeric(r["total_questions"],errors="coerce"))
    if "first_rri_firm_year" not in r.columns:
        r=r.sort_values(["firm_code","rri_year"]).copy(); r["first_rri_firm_year"]=(~r.duplicated("firm_code")).astype(int)
    pre=da[["firm_code","fiscal_year","DA","AbsDA"]].rename(columns={"fiscal_year":"pre_outcome_year","DA":"DA_pre","AbsDA":"AbsDA_pre"})
    post=da[["firm_code","fiscal_year","DA","AbsDA"]].rename(columns={"fiscal_year":"outcome_year","DA":"DA_post","AbsDA":"AbsDA_post"})
    ctl=controls[["firm_code","fiscal_year","size","leverage","cash_ratio","roa","industry_name"]].rename(columns={"fiscal_year":"control_year","size":"size_t","leverage":"leverage_t","cash_ratio":"cash_t","roa":"roa_t","industry_name":"industry_name_t"})
    return r.merge(pre,on=["firm_code","pre_outcome_year"],how="left").merge(post,on=["firm_code","outcome_year"],how="left").merge(ctl,on=["firm_code","control_year"],how="left")

def fit_cluster(name,df,formula,outcome):
    d=df.dropna(subset=[outcome,"RRI10","firm_code"]).copy()
    if len(d)<30 or d["RRI10"].nunique()<5: return {"model":name,"N":len(d),"status":"INSUFFICIENT_N","formula":formula}
    try:
        m=smf.ols(formula,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["firm_code"]}); ci=m.conf_int().loc["RRI10"]
        return {"model":name,"N":int(m.nobs),"status":"OK","formula":formula,"beta_RRI10":float(m.params["RRI10"]),"se_cluster":float(m.bse["RRI10"]),"p_cluster":float(m.pvalues["RRI10"]),"ci95_low":float(ci.iloc[0]),"ci95_high":float(ci.iloc[1]),"r2":float(m.rsquared)}
    except Exception as e: return {"model":name,"N":len(d),"status":f"ERROR:{e}","formula":formula}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--financial",required=True); ap.add_argument("--rri",required=True); ap.add_argument("--outdir",default="rri_modified_jones_results"); args=ap.parse_args()
    outdir=Path(args.outdir); outdir.mkdir(parents=True,exist_ok=True); full=pd.read_csv(args.financial,dtype={"firm_code":str}); rri=pd.read_csv(args.rri,dtype={"firm_code":str})
    required=["firm_code","fiscal_year","industry_name","total_assets","total_liabilities","cash","accounts_receivable","fixed_assets","operating_revenue","net_profit","net_operating_cashflow"]
    missing=[c for c in required if c not in full.columns]
    if missing: raise ValueError(f"Financial input missing: {missing}")
    da,cells,controls=construct_da(full); cells.to_csv(outdir/"01_MODIFIED_JONES_PEER_CELLS.csv",index=False,encoding="utf-8-sig"); da.to_csv(outdir/"02_FULL_MARKET_DISCRETIONARY_ACCRUALS.csv",index=False,encoding="utf-8-sig")
    panel=merge_rri(rri,da,controls); panel.to_csv(outdir/"03_RRI_EARNINGS_MANAGEMENT_PANEL.csv",index=False,encoding="utf-8-sig")
    coverage=pd.DataFrame([["RRI firm-years",len(panel)],["AbsDA pre available",int(panel["AbsDA_pre"].notna().sum())],["AbsDA post available",int(panel["AbsDA_post"].notna().sum())],["Primary pre+post available",int(panel[["AbsDA_pre","AbsDA_post"]].notna().all(axis=1).sum())],["F2 complete cases",int(panel[["AbsDA_pre","AbsDA_post","size_t","leverage_t","cash_t","roa_t","industry_name_t","event_type"]].notna().all(axis=1).sum())],["Valid full-market peer cells",int((cells["status"]=="OK").sum())]],columns=["metric","value"]); coverage.to_csv(outdir/"04_COVERAGE.csv",index=False,encoding="utf-8-sig")
    f0="AbsDA_post ~ RRI10"; f1="AbsDA_post ~ RRI10 + AbsDA_pre"; f2="AbsDA_post ~ RRI10 + AbsDA_pre + size_t + leverage_t + cash_t + roa_t + ln_nq + C(rri_year) + C(industry_name_t) + C(event_type)"
    results=[fit_cluster("F0",panel,f0,"AbsDA_post"),fit_cluster("F1",panel,f1,"AbsDA_post"),fit_cluster("F2_PRIMARY",panel,f2,"AbsDA_post")]
    first=panel[pd.to_numeric(panel.get("first_rri_firm_year",0),errors="coerce").fillna(0).eq(1)].copy(); results.append(fit_cluster("R1_FIRST_RRI",first,f2,"AbsDA_post"))
    med=panel.copy(); med["RRI10"]=pd.to_numeric(med["AnnualRRI_median_event"],errors="coerce")/10.0; results.append(fit_cluster("R2_MEDIAN_RRI",med,f2,"AbsDA_post"))
    signed=f2.replace("AbsDA_post","DA_post").replace("AbsDA_pre","DA_pre"); results.append(fit_cluster("S1_SIGNED_DA",panel,signed,"DA_post"))
    res=pd.DataFrame(results); res.to_csv(outdir/"05_REGRESSION_RESULTS.csv",index=False,encoding="utf-8-sig"); pr=res[res["model"]=="F2_PRIMARY"]; primary=pr.iloc[0].to_dict() if len(pr) else {}
    status={"schema":"RRI_MODIFIED_JONES_STATUS_v1.0","primary_model":"F2_PRIMARY","prediction":"beta_RRI10 < 0","primary_N":int(primary.get("N",0) or 0),"beta_RRI10":primary.get("beta_RRI10"),"p_cluster":primary.get("p_cluster"),"frozen_design_changed":False,"interpretation_rule":"F0/F1/secondary models cannot rescue a failed F2 primary result."}; (outdir/"06_STATUS.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    print(coverage.to_string(index=False)); print(res.to_string(index=False)); print(json.dumps(status,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
