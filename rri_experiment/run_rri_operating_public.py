#!/usr/bin/env python3
import base64, json, re, zlib
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE=Path(__file__).resolve().parent
OUT=BASE/'results'; OUT.mkdir(exist_ok=True)
RRI_PATH=BASE/'RRI_FIRM_YEAR_v2.3m_ACTIONS_INPUT.csv'
B64_PATH=BASE/'RRI_FIRM_YEAR_v2.3m_ACTIONS_INPUT.csv.zlib.b64'
DTA_PATH=BASE.parent/'external_controls/data/c_output/ControlVars_Y.dta'
BAL_DIR=BASE/'zenodo_balance'

def norm_code(x):
    s=re.sub(r'\D','',str(x)); return s[-6:].zfill(6)

def read_balance_files():
    files=sorted(BAL_DIR.glob('*.csv'))
    if not files: raise RuntimeError('No Zenodo balance CSVs found')
    parts=[]
    for p in files:
        d=pd.read_csv(p,encoding='gb18030',low_memory=False)
        print('BALANCE_FILE',p.name,'rows',len(d),'cols',len(d.columns))
        parts.append(d)
    b=pd.concat(parts,ignore_index=True)
    cmap={'A股股票代码_A_StkCd':'firm_code','报表类型_ReportType':'report_type','截止日期_EndDt':'end_date','调整代码()_AdjCd':'adj_code','货币资金/现金及存放中央银行款项(元)_CashEqv':'cash_raw','资产总计(元)_TotAss':'assets_raw'}
    miss=[c for c in cmap if c not in b.columns]
    if miss: raise RuntimeError('Zenodo balance fields missing: '+','.join(miss))
    b=b[list(cmap)].rename(columns=cmap)
    b=b[b['report_type'].astype(str).str.upper().eq('Q4')].copy()
    b['firm_code']=b['firm_code'].map(norm_code)
    b['fiscal_year']=pd.to_datetime(b['end_date'],errors='coerce').dt.year.astype('Int64')
    for c in ['adj_code','cash_raw','assets_raw']: b[c]=pd.to_numeric(b[c],errors='coerce')
    b=b[(b.fiscal_year.between(2014,2025)) & (b.assets_raw>0)].copy()
    b['cash_ratio_external']=b.cash_raw/b.assets_raw
    b.loc[~np.isfinite(b.cash_ratio_external),'cash_ratio_external']=np.nan
    b['prefer_original']=(b.adj_code.fillna(999999)==0).astype(int)
    b=b.sort_values(['firm_code','fiscal_year','prefer_original','adj_code'],ascending=[True,True,False,True])
    print('BALANCE_Q4_ROWS',len(b),'DUP_ROWS_BEFORE_RULE',int(b.duplicated(['firm_code','fiscal_year'],keep=False).sum()))
    b=b.drop_duplicates(['firm_code','fiscal_year'],keep='first')
    return b[['firm_code','fiscal_year','cash_ratio_external']]

def build_financial_panel():
    if not DTA_PATH.exists(): raise RuntimeError('Annual public DTA missing: '+str(DTA_PATH))
    d=pd.read_stata(DTA_PATH,convert_categoricals=False)
    need=['STKCD','YEAR','INDCD','INDNM','IS_FINANCE','ROA','GROWTH','LEV','SIZE','TAT']
    miss=[c for c in need if c not in d.columns]
    if miss: raise RuntimeError('Annual DTA fields missing: '+','.join(miss))
    d=d[need].copy(); d['firm_code']=d.STKCD.map(norm_code); d['fiscal_year']=pd.to_datetime(d.YEAR,errors='coerce').dt.year.astype('Int64')
    for c in ['ROA','GROWTH','LEV','SIZE','TAT','IS_FINANCE']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[d.fiscal_year.between(2014,2025)].copy()
    d['total_assets']=np.exp(d.SIZE); d['total_liabilities']=d.LEV*d.total_assets; d['operating_revenue']=d.TAT*d.total_assets; d['net_profit']=d.ROA*d.total_assets
    d['industry_code']=d.INDCD.astype(str).str.strip(); d['industry_name']=d.INDNM.astype(str).str.strip(); d['external_finance_flag']=(d.IS_FINANCE==1).astype(int)
    cash=read_balance_files(); d=d.merge(cash,on=['firm_code','fiscal_year'],how='left'); d['cash']=d.cash_ratio_external*d.total_assets
    d=d.sort_values(['firm_code','fiscal_year']).drop_duplicates(['firm_code','fiscal_year'],keep='last').reset_index(drop=True)
    d['revenue_lag_audit']=d.groupby('firm_code').operating_revenue.shift(1); d['growth_reconstructed']=d.operating_revenue/d.revenue_lag_audit-1
    z=d[['GROWTH','growth_reconstructed']].replace([np.inf,-np.inf],np.nan).dropna(); corr=float(z.corr().iloc[0,1]) if len(z)>2 else np.nan; mae=float((z.GROWTH-z.growth_reconstructed).abs().mean()) if len(z) else np.nan
    audit={'annual_dta_rows_2014_2025':int(len(d)),'annual_dta_firms':int(d.firm_code.nunique()),'cash_ratio_nonmissing_rows':int(d.cash_ratio_external.notna().sum()),'cash_ratio_coverage':float(d.cash_ratio_external.notna().mean()),'growth_reconstruction_n':int(len(z)),'growth_reconstruction_corr':corr,'growth_reconstruction_mae':mae}
    print('RECONSTRUCTION_AUDIT',json.dumps(audit,ensure_ascii=False)); (OUT/'FINANCIAL_RECONSTRUCTION_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    return d

def winsorize_by_year(df, cols, lo=.01, hi=.99):
    d=df.copy()
    for c in cols:
        def f(s):
            x=pd.to_numeric(s,errors='coerce')
            if x.notna().sum()<10:return x
            a,b=x.quantile(lo),x.quantile(hi);return x.clip(a,b)
        d[c]=d.groupby('fiscal_year',group_keys=False)[c].transform(f)
    return d

def prep_fin(d):
    d=d.copy().sort_values(['firm_code','fiscal_year']); d['lag_assets']=d.groupby('firm_code').total_assets.shift(1); d['lag_revenue']=d.groupby('firm_code').operating_revenue.shift(1)
    d['roa']=d.net_profit/d.total_assets; d['sales_growth']=d.operating_revenue/d.lag_revenue-1; avg=(d.total_assets+d.lag_assets)/2; d['asset_turnover']=d.operating_revenue/avg; d['operating_margin']=d.net_profit/d.operating_revenue
    d['size']=np.log(d.total_assets.where(d.total_assets>0)); d['leverage']=d.total_liabilities/d.total_assets; d['cash_ratio']=d.cash/d.total_assets
    d.loc[(d.lag_revenue.abs()<1e-12)|(~np.isfinite(d.sales_growth)),'sales_growth']=np.nan; d.loc[(avg<=0)|(~np.isfinite(d.asset_turnover)),'asset_turnover']=np.nan; d.loc[(d.operating_revenue.abs()<1e-12)|(~np.isfinite(d.operating_margin)),'operating_margin']=np.nan
    for c in ['roa','leverage','cash_ratio']: d.loc[~np.isfinite(d[c]),c]=np.nan
    txt=d.industry_code.astype(str)+' '+d.industry_name.astype(str); kw='银行|保险|证券|多元金融|信托|金融服务|期货|券商|金融'; d['finance_industry']=((d.external_finance_flag==1)|txt.str.contains(kw,regex=True,na=False)).astype(int)
    return winsorize_by_year(d,['roa','sales_growth','asset_turnover','operating_margin','leverage','cash_ratio'])

def build_panel(fin,rri):
    rri=rri.copy();rri.firm_code=rri.firm_code.map(norm_code);rri.rri_year=pd.to_numeric(rri.rri_year).astype(int);rri=rri.sort_values(['firm_code','rri_year']);rri['first_rri_firm_year']=(rri.groupby('firm_code').cumcount()==0).astype(int)
    ix=fin.set_index(['firm_code','fiscal_year']);vars_=['roa','sales_growth','asset_turnover','operating_margin','size','leverage','cash_ratio','industry_code','industry_name','finance_industry','total_assets','operating_revenue','net_profit'];rows=[]
    for _,rr in rri.iterrows():
        z=rr.to_dict();c=rr.firm_code;t=int(rr.rri_year)
        for label,yy in [('pre',t-1),('t',t),('post',t+1)]:
            try:
                f=ix.loc[(c,yy)]; f=f.iloc[-1] if isinstance(f,pd.DataFrame) else f
                for v in vars_:z[f'{v}_{label}']=f.get(v,np.nan)
            except Exception:
                for v in vars_:z[f'{v}_{label}']=np.nan
        for y in ['roa','sales_growth','asset_turnover','operating_margin']:
            a=pd.to_numeric(pd.Series([z.get(y+'_pre')]),errors='coerce').iloc[0];b=pd.to_numeric(pd.Series([z.get(y+'_post')]),errors='coerce').iloc[0];z['delta_'+y]=b-a if pd.notna(a) and pd.notna(b) else np.nan
        rows.append(z)
    p=pd.DataFrame(rows);flag=pd.to_numeric(p.finance_industry_t,errors='coerce').fillna(pd.to_numeric(p.finance_industry_post,errors='coerce')).fillna(0);p['nonfinancial']=(flag!=1).astype(int);return p

def add_dummies(X,d,cols):
    for c in cols:
        if c in d:X=pd.concat([X,pd.get_dummies(d[c].astype(str),prefix=c,drop_first=True,dtype=float)],axis=1)
    return X

def fit(panel,outcome,prior,model,rri_col='AnnualRRI10',first=False,change=False):
    d=panel[panel.nonfinancial==1].copy(); d=d[d.first_rri_firm_year==1] if first else d
    X=pd.DataFrame(index=d.index);X['RRI10']=pd.to_numeric(d[rri_col],errors='coerce')
    if not change and model in ['P1','P2','P3']:X['PriorOutcome']=pd.to_numeric(d[prior],errors='coerce')
    if model in ['P2','P3','D2']:
        X['Size']=pd.to_numeric(d.size_t,errors='coerce');X['Leverage']=pd.to_numeric(d.leverage_t,errors='coerce');X['Cash']=pd.to_numeric(d.cash_ratio_t,errors='coerce');X['LnQuestions']=np.log1p(pd.to_numeric(d.total_questions,errors='coerce'));X=add_dummies(X,d,['rri_year','event_type'])
    if model in ['P3','D2']:X=add_dummies(X,d,['industry_code_t'])
    y=pd.to_numeric(d[outcome],errors='coerce');w=pd.concat([y.rename('Y'),X,d[['firm_code']]],axis=1).dropna();base={'outcome':outcome,'model':model,'rri_variable':rri_col,'first_event_only':int(first),'N':int(len(w))}
    if len(w)<max(35,X.shape[1]+8):return {**base,'beta_RRI10':np.nan,'se_cluster':np.nan,'p_cluster':np.nan,'r2':np.nan,'note':'insufficient N relative to specification'}
    cols=[c for c in w if c not in ['Y','firm_code']];Xv=sm.add_constant(w[cols].to_numpy(float),has_constant='add');mod=sm.OLS(w.Y.to_numpy(float),Xv).fit(cov_type='cluster',cov_kwds={'groups':w.firm_code.astype(str).to_numpy()});names=['const']+cols;i=names.index('RRI10')
    return {**base,'beta_RRI10':float(mod.params[i]),'se_cluster':float(mod.bse[i]),'p_cluster':float(mod.pvalues[i]),'r2':float(mod.rsquared),'n_regressors':len(mod.params),'matrix_rank':int(np.linalg.matrix_rank(Xv)),'note':''}

def main():
    if not RRI_PATH.exists():RRI_PATH.write_bytes(zlib.decompress(base64.b64decode(B64_PATH.read_text().strip())))
    rri=pd.read_csv(RRI_PATH,dtype={'firm_code':str});fin=prep_fin(build_financial_panel());panel=build_panel(fin,rri);panel.to_csv(OUT/'RRI_OPERATING_PERFORMANCE_PANEL_PUBLIC.csv',index=False,encoding='utf-8-sig')
    res=[]
    for m in ['P0','P1','P2','P3']:res.append(fit(panel,'roa_post','roa_pre',m))
    res.append(fit(panel,'roa_post','roa_pre','P3',first=True))
    for alt in ['AnnualRRI_median_event','AnnualRRI_min_event']:
        col=alt+'_10';panel[col]=pd.to_numeric(panel[alt],errors='coerce')/10;res.append(fit(panel,'roa_post','roa_pre','P3',rri_col=col))
    for out,pre in [('sales_growth_post','sales_growth_pre'),('asset_turnover_post','asset_turnover_pre'),('operating_margin_post','operating_margin_pre')]:res.append(fit(panel,out,pre,'P3'))
    for out in ['delta_roa','delta_sales_growth','delta_asset_turnover','delta_operating_margin']:res.append(fit(panel,out,None,'D2',change=True))
    rr=pd.DataFrame(res);rr.to_csv(OUT/'RRI_OPERATING_PERFORMANCE_RESULTS_PUBLIC.csv',index=False,encoding='utf-8-sig')
    cov=[]
    for y in ['roa','sales_growth','asset_turnover','operating_margin']:
        valid=(panel.nonfinancial==1)&pd.to_numeric(panel[y+'_pre'],errors='coerce').notna()&pd.to_numeric(panel[y+'_post'],errors='coerce').notna();cov.append({'outcome':y,'paired_pre_post_nonfinancial_n':int(valid.sum()),'pct_of_232':float(valid.mean())})
    pd.DataFrame(cov).to_csv(OUT/'RRI_OPERATING_PERFORMANCE_COVERAGE_PUBLIC.csv',index=False,encoding='utf-8-sig')
    meta={'rri_rows':len(rri),'finance_rows':len(fin),'finance_year_min':int(fin.fiscal_year.min()),'finance_year_max':int(fin.fiscal_year.max()),'event_year_cash_nonmissing':int(pd.to_numeric(panel.cash_ratio_t,errors='coerce').notna().sum()),'source_annual_controls':'renzhongxing9/Ashare-control-vars ControlVars_Y.dta (public CSMAR-derived)','source_cash':'Zenodo record 20032245 annual balance sheets','governance':'Frozen outcomes/specifications unchanged; no coefficient-dependent redesign.'}
    (OUT/'RUN_METADATA.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nCOVERAGE\n',pd.DataFrame(cov).to_string(index=False));print('\nRESULTS\n',rr.to_string(index=False));print('\nMETA',json.dumps(meta,ensure_ascii=False))
if __name__=='__main__':main()
