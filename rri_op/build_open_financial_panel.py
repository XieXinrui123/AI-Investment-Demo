import io, json, re, time
from pathlib import Path
import numpy as np
import pandas as pd
import requests

OUT=Path('rri_op_public')
OUT.mkdir(exist_ok=True)
HF='https://huggingface.co/datasets/yifishbossman/financial-analyst-data-full/resolve/main'
UA={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}

def norm_code(x):
    s=re.sub(r'\D','',str(x)); return s[-6:].zfill(6)

def dl_parquet(rel):
    u=f'{HF}/{rel}'
    r=requests.get(u,timeout=180,headers={'User-Agent':'Mozilla/5.0'})
    r.raise_for_status()
    return pd.read_parquet(io.BytesIO(r.content))

def annual_latest(df, date_cols):
    d=df.copy()
    d['end_date']=pd.to_datetime(d['end_date'],errors='coerce')
    d=d[(d['end_date'].dt.month==12)&(d['end_date'].dt.day==31)].copy()
    d['fiscal_year']=d['end_date'].dt.year.astype('Int64')
    d=d[(d['fiscal_year']>=2014)&(d['fiscal_year']<=2025)].copy()
    sort=['ts_code','end_date']
    for c in date_cols:
        if c in d.columns:
            d[c]=pd.to_datetime(d[c],errors='coerce')
            sort.append(c)
    d=d.sort_values(sort).drop_duplicates(['ts_code','end_date'],keep='last')
    return d

def get_year_industry(y):
    u='https://datacenter-web.eastmoney.com/api/data/v1/get'
    p={'sortColumns':'UPDATE_DATE,SECURITY_CODE','sortTypes':'-1,-1','pageSize':'500','pageNumber':'1','reportName':'RPT_LICO_FN_CPD','columns':'ALL','filter':f"(REPORTDATE='{y}-12-31')",'source':'WEB','client':'WEB'}
    allrows=[]; pages=1
    for page in range(1,40):
        p['pageNumber']=str(page)
        last=None
        for attempt in range(3):
            try:
                r=requests.get(u,params=p,timeout=25,headers=UA)
                r.raise_for_status(); j=r.json(); last=None; break
            except Exception as e:
                last=e; time.sleep(1+attempt)
        if last is not None: raise last
        result=j.get('result') or {}
        if page==1: pages=int(result.get('pages') or 1)
        rows=result.get('data') or []
        allrows.extend(rows)
        if page>=pages: break
        time.sleep(.12)
    d=pd.DataFrame(allrows)
    if d.empty: return pd.DataFrame(columns=['firm_code','fiscal_year','industry_code','industry_source'])
    out=pd.DataFrame({'firm_code':d['SECURITY_CODE'].map(norm_code),'fiscal_year':y,'industry_code':d.get('PUBLISHNAME',pd.Series(index=d.index,dtype=object))})
    out['industry_code']=out['industry_code'].astype('string').str.strip()
    out.loc[out['industry_code'].isin(['','None','nan','<NA>']),'industry_code']=pd.NA
    out['industry_source']='Eastmoney_RPT_LICO_FN_CPD_PUBLISHNAME'
    return out.drop_duplicates(['firm_code','fiscal_year'],keep='first')

print('Downloading open financial statements...')
bal=annual_latest(dl_parquet('parquet/financial/balance_sheet.parquet'),['ann_date'])
pro=annual_latest(dl_parquet('parquet/financial/profit_sheet.parquet'),['ann_date','f_ann_date'])
print('annual balance',bal.shape,'profit',pro.shape)

b=bal[['ts_code','fiscal_year','total_assets','total_liab','money_cap']].copy()
p=pro[['ts_code','fiscal_year','revenue','n_income']].copy()
fin=b.merge(p,on=['ts_code','fiscal_year'],how='outer')
fin['firm_code']=fin['ts_code'].map(norm_code)
fin=fin.rename(columns={'total_liab':'total_liabilities','money_cap':'cash','revenue':'operating_revenue','n_income':'net_profit'})

print('Fetching historical industries...')
inds=[]; failures=[]
for y in range(2014,2026):
    try:
        x=get_year_industry(y); inds.append(x); print(y,len(x),'industry rows')
    except Exception as e:
        failures.append({'fiscal_year':y,'error':repr(e)}); print('INDUSTRY FAIL',y,repr(e))
ind=pd.concat(inds,ignore_index=True) if inds else pd.DataFrame(columns=['firm_code','fiscal_year','industry_code','industry_source'])

fin=fin.merge(ind,on=['firm_code','fiscal_year'],how='left')
# Pre-result deterministic fallback: nearest historical industry within +/-1 year, prior year first.
ix={(r.firm_code,int(r.fiscal_year)):r.industry_code for r in ind.dropna(subset=['industry_code']).itertuples()}
def fill_ind(row):
    if pd.notna(row['industry_code']): return row['industry_code'], row.get('industry_source','Eastmoney')
    c=row['firm_code']; y=int(row['fiscal_year'])
    for yy,tag in [(y-1,'nearest_prior_1y'),(y+1,'nearest_next_1y')]:
        v=ix.get((c,yy))
        if v is not None and pd.notna(v): return v,tag
    return 'UNKNOWN','unresolved_unknown'
filled=fin.apply(fill_ind,axis=1,result_type='expand'); filled.columns=['industry_code_filled','industry_source_filled']
fin['industry_code']=filled['industry_code_filled']; fin['industry_source']=filled['industry_source_filled']

keep=['firm_code','fiscal_year','industry_code','total_assets','total_liabilities','cash','operating_revenue','net_profit','industry_source']
fin=fin[keep].sort_values(['firm_code','fiscal_year']).drop_duplicates(['firm_code','fiscal_year'],keep='last')
fin.to_csv(OUT/'OPEN_FINANCIAL_PANEL_2014_2025.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(failures).to_csv(OUT/'INDUSTRY_FETCH_FAILURES.csv',index=False,encoding='utf-8-sig')

# RRI-window coverage audit before regressions.
rri=pd.read_csv('rri_op_input/RRI_FIRM_YEAR_232_v2.3m_OP_COMPAT.csv',dtype={'firm_code':str})
rri['firm_code']=rri['firm_code'].map(norm_code); rri['rri_year']=pd.to_numeric(rri['rri_year']).astype(int)
fidx=fin.set_index(['firm_code','fiscal_year'])
rows=[]
for rr in rri.itertuples():
    z={'firm_code':rr.firm_code,'rri_year':rr.rri_year}
    for lab,yy in [('pre',rr.rri_year-1),('t',rr.rri_year),('post',rr.rri_year+1)]:
        try:
            q=fidx.loc[(rr.firm_code,yy)]
            if isinstance(q,pd.DataFrame): q=q.iloc[-1]
            z[f'{lab}_core']=int(pd.notna(q['total_assets']) and pd.notna(q['total_liabilities']) and pd.notna(q['cash']) and pd.notna(q['operating_revenue']) and pd.notna(q['net_profit']))
            z[f'{lab}_industry']=q['industry_code']; z[f'{lab}_industry_source']=q['industry_source']
        except Exception:
            z[f'{lab}_core']=0; z[f'{lab}_industry']=None; z[f'{lab}_industry_source']=None
    rows.append(z)
qc=pd.DataFrame(rows)
qc['pre_post_core']=qc['pre_core']*qc['post_core']; qc['pre_t_post_core']=qc['pre_core']*qc['t_core']*qc['post_core']
qc.to_csv(OUT/'RRI_FINANCIAL_COVERAGE_AUDIT.csv',index=False,encoding='utf-8-sig')
print('RRI coverage N=',len(qc),'pre',int(qc.pre_core.sum()),'t',int(qc.t_core.sum()),'post',int(qc.post_core.sum()),'pre+post',int(qc.pre_post_core.sum()),'all3',int(qc.pre_t_post_core.sum()))
print('industry source at t:',qc['t_industry_source'].value_counts(dropna=False).to_dict())
