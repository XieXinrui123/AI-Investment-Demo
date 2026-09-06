import io, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd
import requests

OUT=Path('rri_op_public_fast'); OUT.mkdir(exist_ok=True)
HF='https://huggingface.co/datasets/yifishbossman/financial-analyst-data-full/resolve/main'
UA={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}
EM='https://datacenter-web.eastmoney.com/api/data/v1/get'

def norm_code(x):
    s=re.sub(r'\D','',str(x)); return s[-6:].zfill(6)

def dl_parquet(rel):
    r=requests.get(f'{HF}/{rel}',timeout=180,headers={'User-Agent':'Mozilla/5.0'})
    r.raise_for_status(); return pd.read_parquet(io.BytesIO(r.content))

def annual_latest(df, date_cols):
    d=df.copy(); d['end_date']=pd.to_datetime(d['end_date'],errors='coerce')
    d=d[(d['end_date'].dt.month==12)&(d['end_date'].dt.day==31)].copy()
    d['fiscal_year']=d['end_date'].dt.year.astype('Int64')
    d=d[(d['fiscal_year']>=2014)&(d['fiscal_year']<=2025)].copy()
    sort=['ts_code','end_date']
    for c in date_cols:
        if c in d.columns:
            d[c]=pd.to_datetime(d[c],errors='coerce'); sort.append(c)
    return d.sort_values(sort).drop_duplicates(['ts_code','end_date'],keep='last')

def fetch_page(y,page):
    p={'sortColumns':'UPDATE_DATE,SECURITY_CODE','sortTypes':'-1,-1','pageSize':'500','pageNumber':str(page),'reportName':'RPT_LICO_FN_CPD','columns':'ALL','filter':f"(REPORTDATE='{y}-12-31')",'source':'WEB','client':'WEB'}
    err=None
    for k in range(4):
        try:
            r=requests.get(EM,params=p,timeout=20,headers=UA); r.raise_for_status(); j=r.json()
            result=j.get('result') or {}
            return y,page,int(result.get('pages') or 1),result.get('data') or []
        except Exception as e:
            err=e; time.sleep(.5*(k+1))
    raise err

print('Downloading open financial statements...',flush=True)
bal=annual_latest(dl_parquet('parquet/financial/balance_sheet.parquet'),['ann_date'])
pro=annual_latest(dl_parquet('parquet/financial/profit_sheet.parquet'),['ann_date','f_ann_date'])
print('annual balance',bal.shape,'profit',pro.shape,flush=True)
b=bal[['ts_code','fiscal_year','total_assets','total_liab','money_cap']].copy()
p=pro[['ts_code','fiscal_year','revenue','n_income']].copy()
fin=b.merge(p,on=['ts_code','fiscal_year'],how='outer')
fin['firm_code']=fin['ts_code'].map(norm_code)
fin=fin.rename(columns={'total_liab':'total_liabilities','money_cap':'cash','revenue':'operating_revenue','n_income':'net_profit'})

# Industry is used only at event year t (and post-year as finance fallback) in the frozen model.
# Fetch exact annual Eastmoney rows for 2015-2025, concurrently. Same source/fields as slow builder.
years=list(range(2015,2026)); first={}; page_counts={}; failures=[]
print('Fetching first industry pages...',flush=True)
with ThreadPoolExecutor(max_workers=11) as ex:
    futs={ex.submit(fetch_page,y,1):y for y in years}
    for f in as_completed(futs):
        y=futs[f]
        try:
            yy,pg,npages,rows=f.result(); first[y]=rows; page_counts[y]=npages
            print('year',y,'pages',npages,'first_rows',len(rows),flush=True)
        except Exception as e:
            failures.append({'year':y,'page':1,'error':repr(e)}); page_counts[y]=0

tasks=[]
for y,n in page_counts.items():
    for pg in range(2,n+1): tasks.append((y,pg))
rows_by_year={y:list(first.get(y,[])) for y in years}
print('Fetching remaining industry pages concurrently:',len(tasks),flush=True)
with ThreadPoolExecutor(max_workers=24) as ex:
    futs={ex.submit(fetch_page,y,pg):(y,pg) for y,pg in tasks}
    done=0
    for f in as_completed(futs):
        y,pg=futs[f]
        try:
            yy,pp,npages,rows=f.result(); rows_by_year[y].extend(rows)
        except Exception as e:
            failures.append({'year':y,'page':pg,'error':repr(e)})
        done+=1
        if done%25==0 or done==len(tasks): print('pages_done',done,'/',len(tasks),flush=True)

inds=[]
for y in years:
    d=pd.DataFrame(rows_by_year[y])
    if d.empty: continue
    # API sort is latest UPDATE_DATE first; first code occurrence is the latest annual record.
    x=pd.DataFrame({'firm_code':d['SECURITY_CODE'].map(norm_code),'fiscal_year':y,'industry_code':d.get('PUBLISHNAME',pd.Series(index=d.index,dtype=object))})
    x['industry_code']=x['industry_code'].astype('string').str.strip()
    x.loc[x['industry_code'].isin(['','None','nan','<NA>']),'industry_code']=pd.NA
    x=x.drop_duplicates(['firm_code','fiscal_year'],keep='first')
    x['industry_source']='Eastmoney_RPT_LICO_FN_CPD_PUBLISHNAME_exact_year'
    inds.append(x)
ind=pd.concat(inds,ignore_index=True) if inds else pd.DataFrame(columns=['firm_code','fiscal_year','industry_code','industry_source'])

fin=fin.merge(ind,on=['firm_code','fiscal_year'],how='left')
# Frozen ex-ante fallback: nearest historical same-firm +/-1 year, prior first.
ix={(r.firm_code,int(r.fiscal_year)):r.industry_code for r in ind.dropna(subset=['industry_code']).itertuples()}
def fill_ind(row):
    if pd.notna(row['industry_code']): return row['industry_code'],row.get('industry_source','exact')
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

rri=pd.read_csv('rri_op_input/RRI_FIRM_YEAR_232_v2.3m_OP_COMPAT.csv',dtype={'firm_code':str})
rri['firm_code']=rri['firm_code'].map(norm_code); rri['rri_year']=pd.to_numeric(rri['rri_year']).astype(int)
fidx=fin.set_index(['firm_code','fiscal_year']); audit=[]
for rr in rri.itertuples():
    z={'firm_code':rr.firm_code,'rri_year':rr.rri_year}
    for lab,yy in [('pre',rr.rri_year-1),('t',rr.rri_year),('post',rr.rri_year+1)]:
        try:
            q=fidx.loc[(rr.firm_code,yy)]; q=q.iloc[-1] if isinstance(q,pd.DataFrame) else q
            z[f'{lab}_core']=int(pd.notna(q['total_assets']) and pd.notna(q['total_liabilities']) and pd.notna(q['cash']) and pd.notna(q['operating_revenue']) and pd.notna(q['net_profit']))
            z[f'{lab}_industry']=q['industry_code']; z[f'{lab}_industry_source']=q['industry_source']
        except Exception:
            z[f'{lab}_core']=0; z[f'{lab}_industry']=None; z[f'{lab}_industry_source']=None
    audit.append(z)
qc=pd.DataFrame(audit); qc['pre_post_core']=qc.pre_core*qc.post_core; qc['pre_t_post_core']=qc.pre_core*qc.t_core*qc.post_core
qc.to_csv(OUT/'RRI_FINANCIAL_COVERAGE_AUDIT.csv',index=False,encoding='utf-8-sig')
print('RRI coverage N=',len(qc),'pre',int(qc.pre_core.sum()),'t',int(qc.t_core.sum()),'post',int(qc.post_core.sum()),'pre+post',int(qc.pre_post_core.sum()),'all3',int(qc.pre_t_post_core.sum()),flush=True)
print('industry failures',len(failures),'exact_t',int((qc.t_industry_source=='Eastmoney_RPT_LICO_FN_CPD_PUBLISHNAME_exact_year').sum()),flush=True)
