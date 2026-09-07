#!/usr/bin/env python3
import json, re, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE=Path(__file__).resolve().parent
OUT=BASE/'results'; OUT.mkdir(exist_ok=True)
RRI_PATH=BASE/'RRI_FIRM_YEAR_v2.3m_ACTIONS_INPUT.csv'
B64_PATH=BASE/'RRI_FIRM_YEAR_v2.3m_ACTIONS_INPUT.csv.zlib.b64'
FIN_URL='https://raw.githubusercontent.com/gaosiyuan1995/dshw-p02b/main/data/clean/CSMAR_cleaned_data.csv'
INFO_URL='https://raw.githubusercontent.com/gaosiyuan1995/dshw-p02b/main/data/clean/firm_year_clean.csv'

def dl(url,path):
    print('DOWNLOAD',url); urllib.request.urlretrieve(url,path); print('DOWNLOADED',path,path.stat().st_size)

def norm_code(x):
    s=re.sub(r'\D','',str(x)); return s[-6:].zfill(6)

def first_col(df,names):
    lower={str(c).strip().lower():c for c in df.columns}
    for n in names:
        if n.lower() in lower: return lower[n.lower()]
    return None

def standardize_fin(raw,info):
    print('FIN_COLS',list(raw.columns)); print('INFO_COLS',list(info.columns))
    amap={'firm_code':['firm_code','code','stkcd','symbol'],'fiscal_year':['fiscal_year','year'],'total_assets':['total_assets','total_asset'],'total_liabilities':['total_liabilities','total_liability'],'cash':['cash','monetary_fund','cash_and_equivalents'],'operating_revenue':['operating_revenue','revenue'],'net_profit':['net_profit','net_income'],'industry_code':['industry_code'],'industry_name':['industry_name']}
    out=pd.DataFrame(index=raw.index)
    for dst,aliases in amap.items():
        c=first_col(raw,aliases)
        if c is not None: out[dst]=raw[c]
    if 'fiscal_year' not in out:
        c=first_col(raw,['EndDate','accper','report_date'])
        if c is not None: out['fiscal_year']=pd.to_datetime(raw[c],errors='coerce').dt.year
    if 'firm_code' not in out: raise RuntimeError('No stock code column in finance source')
    need=['fiscal_year','total_assets','total_liabilities','cash','operating_revenue','net_profit']; miss=[x for x in need if x not in out]
    if miss: raise RuntimeError('Finance source missing raw fields: '+','.join(miss))
    out['firm_code']=out['firm_code'].map(norm_code); out['fiscal_year']=pd.to_numeric(out['fiscal_year'],errors='coerce').astype('Int64')
    for c in ['total_assets','total_liabilities','cash','operating_revenue','net_profit']: out[c]=pd.to_numeric(out[c],errors='coerce')
    if 'industry_code' not in out or out['industry_code'].isna().all():
        ic=first_col(info,['code','firm_code','Stkcd','Symbol']); iy=first_col(info,['year','fiscal_year']); ico=first_col(info,['industry_code']); ina=first_col(info,['industry_name'])
        z=pd.DataFrame({'firm_code':info[ic].map(norm_code),'fiscal_year':pd.to_numeric(info[iy],errors='coerce').astype('Int64')})
        if ico: z['industry_code']=info[ico].astype(str)
        if ina: z['industry_name']=info[ina].astype(str)
        out=out.merge(z.drop_duplicates(['firm_code','fiscal_year']),on=['firm_code','fiscal_year'],how='left')
    if 'industry_code' not in out: out['industry_code']='UNKNOWN'
    if 'industry_name' not in out: out['industry_name']=''
    return out.dropna(subset=['fiscal_year']).sort_values(['firm_code','fiscal_year']).drop_duplicates(['firm_code','fiscal_year'],keep='last').reset_index(drop=True)

def winsorize_by_year(df,cols):
    d=df.copy()
    for c in cols:
        def f(s):
            x=pd.to_numeric(s,errors='coerce')
            if x.notna().sum()<10:return x
            return x.clip(x.quantile(.01),x.quantile(.99))
        d[c]=d.groupby('fiscal_year',group_keys=False)[c].transform(f)
    return d

def prep_fin(d):
    d=d.copy(); d['lag_assets']=d.groupby('firm_code')['total_assets'].shift(1); d['lag_revenue']=d.groupby('firm_code')['operating_revenue'].shift(1)
    d['roa']=d.net_profit/d.total_assets; d['sales_growth']=d.operating_revenue/d.lag_revenue-1
    avg=(d.total_assets+d.lag_assets)/2; d['asset_turnover']=d.operating_revenue/avg; d['operating_margin']=d.net_profit/d.operating_revenue
    d['size']=np.log(d.total_assets.where(d.total_assets>0)); d['leverage']=d.total_liabilities/d.total_assets; d['cash_ratio']=d.cash/d.total_assets
    d.loc[(d.lag_revenue.abs()<1e-12)|(~np.isfinite(d.sales_growth)),'sales_growth']=np.nan
    d.loc[(avg<=0)|(~np.isfinite(d.asset_turnover)),'asset_turnover']=np.nan
    d.loc[(d.operating_revenue.abs()<1e-12)|(~np.isfinite(d.operating_margin)),'operating_margin']=np.nan
    for c in ['roa','leverage','cash_ratio']: d.loc[~np.isfinite(d[c]),c]=np.nan
    txt=d.industry_code.astype(str)+' '+d.industry_name.astype(str); kw='银行|保险|证券|多元金融|信托|金融服务|期货|券商'
    d['finance_industry']=(txt.str.contains(kw,regex=True,na=False)|d.industry_code.astype(str).str.upper().str.startswith('J')).astype(int)
    return winsorize_by_year(d,['roa','sales_growth','asset_turnover','operating_margin','leverage','cash_ratio'])

def build_panel(fin,rri):
    rri=rri.copy(); rri.firm_code=rri.firm_code.map(norm_code); rri.rri_year=pd.to_numeric(rri.rri_year).astype(int); rri=rri.sort_values(['firm_code','rri_year']); rri['first_rri_firm_year']=(rri.groupby('firm_code').cumcount()==0).astype(int)
    ix=fin.set_index(['firm_code','fiscal_year']); vars_=['roa','sales_growth','asset_turnover','operating_margin','size','leverage','cash_ratio','industry_code','industry_name','finance_industry','total_assets','operating_revenue','net_profit']; rows=[]
    for _,rr in rri.iterrows():
        z=rr.to_dict(); c=rr.firm_code; t=int(rr.rri_year)
        for label,yy in [('pre',t-1),('t',t),('post',t+1)]:
            try:
                f=ix.loc[(c,yy)]; f=f.iloc[-1] if isinstance(f,pd.DataFrame) else f
                for v in vars_: z[f'{v}_{label}']=f.get(v,np.nan)
            except Exception:
                for v in vars_: z[f'{v}_{label}']=np.nan
        for y in ['roa','sales_growth','asset_turnover','operating_margin']:
            a=pd.to_numeric(pd.Series([z.get(y+'_pre')]),errors='coerce').iloc[0]; b=pd.to_numeric(pd.Series([z.get(y+'_post')]),errors='coerce').iloc[0]; z['delta_'+y]=b-a if pd.notna(a) and pd.notna(b) else np.nan
        rows.append(z)
    p=pd.DataFrame(rows); flag=pd.to_numeric(p.finance_industry_t,errors='coerce').fillna(pd.to_numeric(p.finance_industry_post,errors='coerce')).fillna(0); p['nonfinancial']=(flag!=1).astype(int); return p

def add_dummies(X,d,cols):
    for c in cols:
        if c in d: X=pd.concat([X,pd.get_dummies(d[c].astype(str),prefix=c,drop_first=True,dtype=float)],axis=1)
    return X

def fit(panel,outcome,prior,model,rri_col='AnnualRRI10',first=False,change=False):
    d=panel[panel.nonfinancial==1].copy(); d=d[d.first_rri_firm_year==1] if first else d
    X=pd.DataFrame(index=d.index); X['RRI10']=pd.to_numeric(d[rri_col],errors='coerce')
    if not change and model in ['P1','P2','P3']: X['PriorOutcome']=pd.to_numeric(d[prior],errors='coerce')
    if model in ['P2','P3','D2']:
        X['Size']=pd.to_numeric(d.size_t,errors='coerce'); X['Leverage']=pd.to_numeric(d.leverage_t,errors='coerce'); X['Cash']=pd.to_numeric(d.cash_ratio_t,errors='coerce'); X['LnQuestions']=np.log1p(pd.to_numeric(d.total_questions,errors='coerce')); X=add_dummies(X,d,['rri_year','event_type'])
    if model in ['P3','D2']: X=add_dummies(X,d,['industry_code_t'])
    y=pd.to_numeric(d[outcome],errors='coerce'); w=pd.concat([y.rename('Y'),X,d[['firm_code']]],axis=1).dropna(); base={'outcome':outcome,'model':model,'rri_variable':rri_col,'first_event_only':int(first),'N':len(w)}
    if len(w)<max(35,X.shape[1]+8): return {**base,'beta_RRI10':np.nan,'se_cluster':np.nan,'p_cluster':np.nan,'r2':np.nan,'note':'insufficient N relative to specification'}
    cols=[c for c in w if c not in ['Y','firm_code']]; Xv=sm.add_constant(w[cols].to_numpy(float),has_constant='add'); mod=sm.OLS(w.Y.to_numpy(float),Xv).fit(cov_type='cluster',cov_kwds={'groups':w.firm_code.astype(str).to_numpy()}); names=['const']+cols; i=names.index('RRI10')
    return {**base,'beta_RRI10':float(mod.params[i]),'se_cluster':float(mod.bse[i]),'p_cluster':float(mod.pvalues[i]),'r2':float(mod.rsquared),'n_regressors':len(mod.params),'matrix_rank':int(np.linalg.matrix_rank(Xv)),'note':''}

def main():
    import base64,zlib
    if not RRI_PATH.exists(): RRI_PATH.write_bytes(zlib.decompress(base64.b64decode(B64_PATH.read_text().strip())))
    finp=BASE/'public_finance.csv'; infop=BASE/'public_info.csv'; dl(FIN_URL,finp); dl(INFO_URL,infop)
    fin=prep_fin(standardize_fin(pd.read_csv(finp,low_memory=False),pd.read_csv(infop,low_memory=False))); rri=pd.read_csv(RRI_PATH,dtype={'firm_code':str}); panel=build_panel(fin,rri); panel.to_csv(OUT/'RRI_OPERATING_PERFORMANCE_PANEL_PUBLIC.csv',index=False)
    res=[]
    for m in ['P0','P1','P2','P3']: res.append(fit(panel,'roa_post','roa_pre',m))
    res.append(fit(panel,'roa_post','roa_pre','P3',first=True))
    for alt in ['AnnualRRI_median_event','AnnualRRI_min_event']:
        col=alt+'_10'; panel[col]=pd.to_numeric(panel[alt],errors='coerce')/10; res.append(fit(panel,'roa_post','roa_pre','P3',rri_col=col))
    for out,pre in [('sales_growth_post','sales_growth_pre'),('asset_turnover_post','asset_turnover_pre'),('operating_margin_post','operating_margin_pre')]: res.append(fit(panel,out,pre,'P3'))
    for out in ['delta_roa','delta_sales_growth','delta_asset_turnover','delta_operating_margin']: res.append(fit(panel,out,None,'D2',change=True))
    rr=pd.DataFrame(res); rr.to_csv(OUT/'RRI_OPERATING_PERFORMANCE_RESULTS_PUBLIC.csv',index=False)
    cov=[]
    for y in ['roa','sales_growth','asset_turnover','operating_margin']:
        valid=(panel.nonfinancial==1)&pd.to_numeric(panel[y+'_pre'],errors='coerce').notna()&pd.to_numeric(panel[y+'_post'],errors='coerce').notna(); cov.append({'outcome':y,'paired_pre_post_nonfinancial_n':int(valid.sum()),'pct_of_232':float(valid.mean())})
    pd.DataFrame(cov).to_csv(OUT/'RRI_OPERATING_PERFORMANCE_COVERAGE_PUBLIC.csv',index=False)
    meta={'rri_rows':len(rri),'finance_rows':len(fin),'finance_year_min':int(fin.fiscal_year.min()),'finance_year_max':int(fin.fiscal_year.max()),'source_finance':FIN_URL,'source_info':INFO_URL,'note':'Public-data execution of frozen operating-performance design; source cleaned from CSMAR by third-party public repository.'}; (OUT/'RUN_METADATA.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nCOVERAGE\n',pd.DataFrame(cov).to_string(index=False)); print('\nRESULTS\n',rr.to_string(index=False)); print('\nMETA',meta)

if __name__=='__main__': main()
