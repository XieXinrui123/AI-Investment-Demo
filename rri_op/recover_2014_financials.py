import re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE=Path('rri_op_public_fast/OPEN_FINANCIAL_PANEL_2014_2025.csv')
RRI=Path('rri_op_input/RRI_FIRM_YEAR_232_v2.3m_OP_COMPAT.csv')
OUT=Path('rri_op_2014_recovery'); OUT.mkdir(exist_ok=True)
UA={'User-Agent':'Mozilla/5.0','Referer':'https://emweb.securities.eastmoney.com/'}
ROOT='https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis'

def norm_code(x):
    s=re.sub(r'\D','',str(x)); return s[-6:].zfill(6)

def symbol(code):
    c=norm_code(code); return ('SH' if c.startswith(('5','6','9')) else 'SZ')+c

def get_json(url,params,tries=4):
    err=None
    for k in range(tries):
        try:
            r=requests.get(url,params=params,timeout=20,headers=UA); r.raise_for_status(); return r.json()
        except Exception as e:
            err=e; time.sleep(.5*(k+1))
    raise err

def get_ctype(sym):
    err=None
    for k in range(4):
        try:
            r=requests.get(f'{ROOT}/Index',params={'type':'web','code':sym.lower()},timeout=20,headers=UA); r.raise_for_status()
            s=BeautifulSoup(r.text,'lxml'); x=s.find(attrs={'id':'hidctype'})
            if x and x.get('value'): return str(x['value'])
        except Exception as e:
            err=e; time.sleep(.5*(k+1))
    # deterministic fallback order used only if the HTML hidden field is unavailable
    for ct in ['4','3','2','1']:
        try:
            j=get_json(f'{ROOT}/zcfzbAjaxNew',{'companyType':ct,'reportDateType':'0','reportType':'1','dates':'2014-12-31','code':sym},tries=1)
            if j.get('data'): return ct
        except Exception: pass
    raise RuntimeError(f'companyType unresolved {sym}: {err!r}')

def fetch_pair(code):
    c=norm_code(code); sym=symbol(c); ct=get_ctype(sym)
    dates='2014-12-31,2015-12-31'
    bal=get_json(f'{ROOT}/zcfzbAjaxNew',{'companyType':ct,'reportDateType':'0','reportType':'1','dates':dates,'code':sym}).get('data') or []
    inc=get_json(f'{ROOT}/lrbAjaxNew',{'companyType':ct,'reportDateType':'0','reportType':'1','dates':dates,'code':sym}).get('data') or []
    def by_year(rows,y):
        for r in rows:
            if str(r.get('REPORT_DATE','')).startswith(str(y)): return r
        return None
    out={'firm_code':c,'symbol':sym,'company_type':ct,'bal_rows':len(bal),'inc_rows':len(inc)}
    for y in [2014,2015]:
        b=by_year(bal,y); q=by_year(inc,y)
        out[f'{y}_total_assets']=None if b is None else b.get('TOTAL_ASSETS')
        out[f'{y}_total_liabilities']=None if b is None else b.get('TOTAL_LIABILITIES')
        out[f'{y}_cash']=None if b is None else b.get('MONETARYFUNDS')
        out[f'{y}_operating_revenue']=None if q is None else q.get('TOTAL_OPERATE_INCOME')
        out[f'{y}_net_profit']=None if q is None else q.get('NETPROFIT')
        out[f'{y}_notice_date_bal']=None if b is None else b.get('NOTICE_DATE')
        out[f'{y}_notice_date_inc']=None if q is None else q.get('NOTICE_DATE')
        out[f'{y}_update_date_bal']=None if b is None else b.get('UPDATE_DATE')
        out[f'{y}_update_date_inc']=None if q is None else q.get('UPDATE_DATE')
    return out

rri=pd.read_csv(RRI,dtype={'firm_code':str}); rri['firm_code']=rri['firm_code'].map(norm_code)
codes=sorted(rri.loc[pd.to_numeric(rri.rri_year,errors='coerce')==2015,'firm_code'].unique())
print('2015 cohort codes',len(codes),flush=True)
rows=[]; failures=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    futs={ex.submit(fetch_pair,c):c for c in codes}
    for i,f in enumerate(as_completed(futs),1):
        c=futs[f]
        try: rows.append(f.result())
        except Exception as e: failures.append({'firm_code':c,'error':repr(e)})
        if i%10==0 or i==len(futs): print('done',i,'/',len(futs),'failures',len(failures),flush=True)
raw=pd.DataFrame(rows).sort_values('firm_code')
raw.to_csv(OUT/'EASTMONEY_2014_2015_RAW_EXTRACT.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(failures).to_csv(OUT/'EASTMONEY_2014_RECOVERY_FAILURES.csv',index=False,encoding='utf-8-sig')

base=pd.read_csv(BASE,dtype={'firm_code':str}); base['firm_code']=base['firm_code'].map(norm_code)
vars_=['total_assets','total_liabilities','cash','operating_revenue','net_profit']
# 2015 overlap concordance audit versus HF/Tushare-derived public panel.
base15=base[base.fiscal_year==2015].set_index('firm_code')
conc=[]
for _,r in raw.iterrows():
    c=r.firm_code
    if c not in base15.index: continue
    b=base15.loc[c]; b=b.iloc[-1] if isinstance(b,pd.DataFrame) else b
    z={'firm_code':c}
    for v in vars_:
        em=pd.to_numeric(pd.Series([r.get(f'2015_{v}')]),errors='coerce').iloc[0]
        hf=pd.to_numeric(pd.Series([b.get(v)]),errors='coerce').iloc[0]
        z[f'em_{v}']=em; z[f'hf_{v}']=hf
        z[f'rel_diff_{v}']=abs(em-hf)/max(abs(hf),1.0) if pd.notna(em) and pd.notna(hf) else np.nan
    conc.append(z)
conc=pd.DataFrame(conc); conc.to_csv(OUT/'SOURCE_CONCORDANCE_2015.csv',index=False,encoding='utf-8-sig')
summary=[]
for v in vars_:
    x=pd.to_numeric(conc[f'rel_diff_{v}'],errors='coerce').dropna()
    summary.append({'variable':v,'N':len(x),'median_rel_diff':x.median() if len(x) else np.nan,'p95_rel_diff':x.quantile(.95) if len(x) else np.nan,'max_rel_diff':x.max() if len(x) else np.nan,'share_within_1pct':(x<=.01).mean() if len(x) else np.nan})
pd.DataFrame(summary).to_csv(OUT/'SOURCE_CONCORDANCE_2015_SUMMARY.csv',index=False,encoding='utf-8-sig')
print('concordance summary'); print(pd.DataFrame(summary).to_string(index=False),flush=True)

# Build 2014 recovery rows. Require all five frozen core fields.
base15_ind=base15['industry_code'].to_dict() if 'industry_code' in base15.columns else {}
rec=[]
for _,r in raw.iterrows():
    vals={v:pd.to_numeric(pd.Series([r.get(f'2014_{v}')]),errors='coerce').iloc[0] for v in vars_}
    ok=all(pd.notna(vals[v]) for v in vars_)
    if not ok: continue
    c=r.firm_code
    rec.append({'firm_code':c,'fiscal_year':2014,'industry_code':base15_ind.get(c,'UNKNOWN'),**vals,'industry_source':'eventyear_2015_industry_carried_for_required_schema_only','financial_source':'Eastmoney_F10_NewFinanceAnalysis_2014'})
rec=pd.DataFrame(rec); rec.to_csv(OUT/'RECOVERED_2014_ROWS.csv',index=False,encoding='utf-8-sig')
print('recovered complete 2014 rows',len(rec),'of',len(codes),flush=True)

patched=base[~((base.fiscal_year==2014)&(base.firm_code.isin(set(rec.firm_code))))].copy()
patched=pd.concat([patched,rec],ignore_index=True,sort=False)
patched=patched.sort_values(['firm_code','fiscal_year']).drop_duplicates(['firm_code','fiscal_year'],keep='last')
patched.to_csv(OUT/'OPEN_FINANCIAL_PANEL_2014_2025_WITH_2014_RECOVERY.csv',index=False,encoding='utf-8-sig')
