import json, math, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

OUT=Path('rri_aem_output'); OUT.mkdir(exist_ok=True)
URL='https://datacenter-web.eastmoney.com/api/data/v1/get'
HEAD={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}
YEARS=list(range(2013,2026))
FIN_PAT=re.compile('银行|证券|保险|金融|信托|期货')


def a_share(code):
    s=str(code).zfill(6)
    return len(s)==6 and s[0] in '036'


def fetch_all(report, filt, sort_cols='SECURITY_CODE', sort_types='1', page_size=500):
    rows=[]; page=1; pages=1
    while page<=pages:
        p={'reportName':report,'columns':'ALL','pageNumber':str(page),'pageSize':str(page_size),
           'sortColumns':sort_cols,'sortTypes':sort_types,'filter':filt,'source':'WEB','client':'WEB'}
        err=None
        for k in range(5):
            try:
                r=requests.get(URL,params=p,headers=HEAD,timeout=45); r.raise_for_status(); j=r.json()
                if not j.get('success') and j.get('result') is None: raise RuntimeError(str(j.get('message')))
                rr=j.get('result') or {}; pages=int(rr.get('pages') or 1); rows.extend(rr.get('data') or []); err=None; break
            except Exception as e:
                err=e; time.sleep(0.8*(k+1))
        if err is not None: raise err
        page+=1; time.sleep(.03)
    return pd.DataFrame(rows)


def get_year(y):
    date=f'{y}-12-31'
    specs={
      'bal':('RPT_DMSK_FN_BALANCE',f"(REPORT_DATE='{date}')",'SECURITY_CODE','1'),
      'inc':('RPT_DMSK_FN_INCOME',f"(REPORT_DATE='{date}')",'SECURITY_CODE','1'),
      'cf':('RPT_DMSK_FN_CASHFLOW',f"(REPORT_DATE='{date}')",'SECURITY_CODE','1'),
      'ind':('RPT_LICO_FN_CPD',f"(REPORTDATE='{date}')",'UPDATE_DATE,SECURITY_CODE','-1,-1')
    }
    got={}
    for k,(rep,fil,sc,st) in specs.items(): got[k]=fetch_all(rep,fil,sc,st)
    return y,got


def dedup_fin(d, cols):
    if d.empty: return pd.DataFrame(columns=cols)
    z=d.copy(); z['SECURITY_CODE']=z['SECURITY_CODE'].astype(str).str.zfill(6); z=z[z['SECURITY_CODE'].map(a_share)].copy()
    z['NOTICE_DATE_SORT']=pd.to_datetime(z.get('NOTICE_DATE'),errors='coerce')
    z['SECUCODE_SORT']=z.get('SECUCODE',pd.Series('',index=z.index)).astype(str)
    z=z.sort_values(['SECURITY_CODE','NOTICE_DATE_SORT','SECUCODE_SORT']).drop_duplicates('SECURITY_CODE',keep='last')
    for c in cols:
        if c not in z.columns: z[c]=np.nan
    return z[cols]


def qwin(s):
    x=pd.to_numeric(s,errors='coerce'); ok=x.dropna()
    if len(ok)<20: return x
    lo,hi=ok.quantile([.01,.99]); return x.clip(lo,hi)

print('FETCHING 2013-2025 Eastmoney statements + historical industries')
raw={}; failures=[]
with ThreadPoolExecutor(max_workers=5) as ex:
    fut={ex.submit(get_year,y):y for y in YEARS}
    for f in as_completed(fut):
        y=fut[f]
        try:
            yy,g=f.result(); raw[yy]=g
            print('year',yy,{k:len(v) for k,v in g.items()},flush=True)
        except Exception as e:
            failures.append({'year':y,'error':repr(e)}); print('FAIL',y,repr(e),flush=True)
if failures:
    pd.DataFrame(failures).to_csv(OUT/'FETCH_FAILURES.csv',index=False)
    raise RuntimeError(f'year fetch failures: {failures}')

panels=[]
for y in YEARS:
    g=raw[y]
    b=dedup_fin(g['bal'],['SECURITY_CODE','TOTAL_ASSETS','FIXED_ASSET','ACCOUNTS_RECE','MONETARYFUNDS','TOTAL_LIABILITIES','NOTICE_DATE'])
    i=dedup_fin(g['inc'],['SECURITY_CODE','TOTAL_OPERATE_INCOME','PARENT_NETPROFIT','NOTICE_DATE']).drop(columns='NOTICE_DATE')
    c=dedup_fin(g['cf'],['SECURITY_CODE','NETCASH_OPERATE','NOTICE_DATE']).drop(columns='NOTICE_DATE')
    ind=g['ind'].copy()
    if len(ind):
        ind['SECURITY_CODE']=ind['SECURITY_CODE'].astype(str).str.zfill(6); ind=ind[ind.SECURITY_CODE.map(a_share)].copy()
        if 'UPDATE_DATE' in ind: ind['UPDATE_DATE_SORT']=pd.to_datetime(ind['UPDATE_DATE'],errors='coerce')
        else: ind['UPDATE_DATE_SORT']=pd.NaT
        ind=ind.sort_values(['SECURITY_CODE','UPDATE_DATE_SORT'],ascending=[True,False]).drop_duplicates('SECURITY_CODE',keep='first')
        if 'PUBLISHNAME' not in ind: ind['PUBLISHNAME']=pd.NA
        ind=ind[['SECURITY_CODE','PUBLISHNAME']]
    else: ind=pd.DataFrame(columns=['SECURITY_CODE','PUBLISHNAME'])
    d=b.merge(i,on='SECURITY_CODE',how='outer').merge(c,on='SECURITY_CODE',how='outer').merge(ind,on='SECURITY_CODE',how='left')
    d['fiscal_year']=y
    d=d.rename(columns={'SECURITY_CODE':'firm_code','TOTAL_ASSETS':'total_assets','FIXED_ASSET':'ppe','ACCOUNTS_RECE':'ar',
                        'MONETARYFUNDS':'cash','TOTAL_LIABILITIES':'total_liabilities','TOTAL_OPERATE_INCOME':'revenue',
                        'PARENT_NETPROFIT':'net_income','NETCASH_OPERATE':'cfo','PUBLISHNAME':'industry'})
    for x in ['total_assets','ppe','ar','cash','total_liabilities','revenue','net_income','cfo']:
        d[x]=pd.to_numeric(d[x],errors='coerce')
    d['industry']=d['industry'].astype('string').str.strip(); d.loc[d['industry'].isin(['','None','nan','<NA>']),'industry']=pd.NA
    d['is_financial']=d['industry'].fillna('').str.contains(FIN_PAT)
    panels.append(d[['firm_code','fiscal_year','industry','is_financial','total_assets','ppe','ar','cash','total_liabilities','revenue','net_income','cfo']])

p=pd.concat(panels,ignore_index=True).sort_values(['firm_code','fiscal_year']).drop_duplicates(['firm_code','fiscal_year'],keep='last')
p.to_csv(OUT/'EASTMONEY_ANNUAL_PANEL_2013_2025.csv',index=False,encoding='utf-8-sig')

# Build Modified Jones inputs without RRI.
p['lag_assets']=p.groupby('firm_code')['total_assets'].shift(1)
p['lag_revenue']=p.groupby('firm_code')['revenue'].shift(1)
p['lag_ar']=p.groupby('firm_code')['ar'].shift(1)
p['d_revenue']=p['revenue']-p['lag_revenue']; p['d_ar']=p['ar']-p['lag_ar']
p['ta']=p['net_income']-p['cfo']
p['ta_scaled']=p['ta']/p['lag_assets']
p['inv_assets']=1.0/p['lag_assets']
p['drevdar_scaled']=(p['d_revenue']-p['d_ar'])/p['lag_assets']
p['ppe_scaled']=p['ppe']/p['lag_assets']
p.loc[(p['lag_assets']<=0)|(~np.isfinite(p['lag_assets'])),['ta_scaled','inv_assets','drevdar_scaled','ppe_scaled']]=np.nan
for col in ['ta_scaled','inv_assets','drevdar_scaled','ppe_scaled']:
    p[col]=p.groupby('fiscal_year',group_keys=False)[col].transform(qwin)

p['DA']=np.nan; p['ABS_DA']=np.nan; p['peer_n']=np.nan; peer=[]
for (yr,ind),idx in p[(p.fiscal_year>=2014)&(~p.is_financial)&p.industry.notna()].groupby(['fiscal_year','industry']).groups.items():
    cols=['ta_scaled','inv_assets','drevdar_scaled','ppe_scaled']
    z=p.loc[idx,cols].dropna()
    n=len(z); rec={'fiscal_year':yr,'industry':ind,'complete_peer_n':n,'eligible':int(n>=20)}
    if n>=20:
        X=z[['inv_assets','drevdar_scaled','ppe_scaled']].to_numpy(float); yv=z['ta_scaled'].to_numpy(float)
        coef=np.linalg.lstsq(X,yv,rcond=None)[0]; resid=yv-X@coef
        p.loc[z.index,'DA']=resid; p.loc[z.index,'ABS_DA']=np.abs(resid); p.loc[z.index,'peer_n']=n
        rec.update({'a1':coef[0],'a2':coef[1],'a3':coef[2]})
    peer.append(rec)
peer=pd.DataFrame(peer); peer.to_csv(OUT/'MODIFIED_JONES_PEER_CELLS.csv',index=False,encoding='utf-8-sig')
da=p[p.fiscal_year.between(2014,2025)][['firm_code','fiscal_year','industry','is_financial','DA','ABS_DA','peer_n','total_assets','total_liabilities','cash','revenue','net_income']].copy()
da.to_csv(OUT/'MODIFIED_JONES_DA_2014_2025.csv',index=False,encoding='utf-8-sig')

# Coverage audit ONLY; no RRI coefficient is estimated here.
rri=pd.read_csv('rri_op/RRI_FIRM_YEAR_232_MIN.csv',dtype={'firm_code':str}); rri['firm_code']=rri.firm_code.str.zfill(6); rri['rri_year']=rri.rri_year.astype(int)
lookup=da.set_index(['firm_code','fiscal_year']); base=p.set_index(['firm_code','fiscal_year'])
rows=[]
for rr in rri.itertuples():
    rec={'firm_code':rr.firm_code,'rri_year':rr.rri_year,'AnnualRRI10':rr.AnnualRRI10,'event_type':rr.event_type,'total_questions':rr.total_questions}
    for lab,yy in [('pre',rr.rri_year-1),('post',rr.rri_year+1)]:
        try:
            q=lookup.loc[(rr.firm_code,yy)]; q=q.iloc[-1] if isinstance(q,pd.DataFrame) else q
            rec[f'abs_da_{lab}']=q.ABS_DA; rec[f'peer_n_{lab}']=q.peer_n; rec[f'industry_{lab}']=q.industry
        except Exception: rec[f'abs_da_{lab}']=np.nan; rec[f'peer_n_{lab}']=np.nan; rec[f'industry_{lab}']=pd.NA
    try:
        q=base.loc[(rr.firm_code,rr.rri_year)]; q=q.iloc[-1] if isinstance(q,pd.DataFrame) else q
        rec['industry_t']=q.industry; rec['is_financial_t']=bool(q.is_financial)
        rec['size_t']=np.log(q.total_assets) if pd.notna(q.total_assets) and q.total_assets>0 else np.nan
        rec['leverage_t']=q.total_liabilities/q.total_assets if pd.notna(q.total_liabilities) and pd.notna(q.total_assets) and q.total_assets>0 else np.nan
        rec['roa_t']=q.net_income/q.total_assets if pd.notna(q.net_income) and pd.notna(q.total_assets) and q.total_assets>0 else np.nan
        rec['cash_t']=q.cash/q.total_assets if pd.notna(q.cash) and pd.notna(q.total_assets) and q.total_assets>0 else np.nan
        prev=base.loc[(rr.firm_code,rr.rri_year-1)]; prev=prev.iloc[-1] if isinstance(prev,pd.DataFrame) else prev
        rec['sales_growth_t']=q.revenue/prev.revenue-1 if pd.notna(q.revenue) and pd.notna(prev.revenue) and prev.revenue!=0 else np.nan
    except Exception:
        for v in ['industry_t','is_financial_t','size_t','leverage_t','roa_t','cash_t','sales_growth_t']: rec[v]=np.nan
    rec['ln_questions']=math.log1p(rr.total_questions)
    rows.append(rec)
a=pd.DataFrame(rows)
controls=['size_t','leverage_t','roa_t','sales_growth_t','cash_t','ln_questions']
a['has_pre_da']=a.abs_da_pre.notna(); a['has_post_da']=a.abs_da_post.notna(); a['has_both_da']=a.has_pre_da&a.has_post_da
a['has_controls']=a[controls].notna().all(axis=1)&a.industry_t.notna()&(~a.is_financial_t.fillna(True).astype(bool))
a['main_complete']=a.has_both_da&a.has_controls
first_year=rri.groupby('firm_code').rri_year.min(); a['first_event']=a.apply(lambda x:x.rri_year==first_year.get(x.firm_code),axis=1)
a.to_csv(OUT/'RRI_AEM_COVERAGE_AUDIT.csv',index=False,encoding='utf-8-sig')
summary={
 'rri_firm_years':int(len(a)), 'unique_firms':int(a.firm_code.nunique()),
 'pre_da':int(a.has_pre_da.sum()), 'post_da':int(a.has_post_da.sum()), 'both_da':int(a.has_both_da.sum()),
 'controls_complete_nonfinancial':int(a.has_controls.sum()), 'main_complete':int(a.main_complete.sum()),
 'first_event_main_complete':int((a.main_complete&a.first_event).sum()),
 'eligible_peer_cells':int(peer.eligible.sum()), 'total_peer_cells':int(len(peer)),
 'da_nonmissing_rows':int(da.ABS_DA.notna().sum()),
 'coverage_only_no_rri_coefficient_estimated':True
}
(OUT/'RRI_AEM_COVERAGE_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('COVERAGE SUMMARY'); print(json.dumps(summary,ensure_ascii=False,indent=2))
