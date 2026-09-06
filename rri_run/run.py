import base64,gzip,io,json,math,re,time,sys
from pathlib import Path
import numpy as np,pandas as pd,requests
import statsmodels.formula.api as smf
B64='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'
PRE=(-90,-1); POST=(1,90); MIN=3
REPORT='https://reportapi.eastmoney.com/report/list'; PRICE='https://push2his.eastmoney.com/api/qt/stock/kline/get'
UA='Mozilla/5.0'
out=Path('rri_run/results'); out.mkdir(parents=True,exist_ok=True)
def code(x):
 s=re.sub(r'\D','',str(x or '')); return s[-6:].zfill(6) if s else ''
def txt(x): return '' if pd.isna(x) else re.sub(r'\s+',' ',str(x)).strip()
def getj(sess,url,params,timeout=15,retries=3):
 e=None
 for i in range(retries):
  try:
   r=sess.get(url,params=params,timeout=timeout); r.raise_for_status(); return r.json()
  except Exception as z: e=z; time.sleep(1+i)
 raise RuntimeError(f'{url} failed: {e}')
def reports(sess,c,b,e):
 rows=[]
 for p in range(1,31):
  q={'industryCode':'*','pageSize':'100','industry':'*','rating':'*','ratingChange':'*','beginTime':b,'endTime':e,'pageNo':str(p),'fields':'','qType':'0','orgCode':'','code':c,'rcode':'','p':str(p),'pageNum':str(p),'pageNumber':str(p)}
  d=getj(sess,REPORT,q).get('data') or []; rows+=d
  if len(d)<100: break
  time.sleep(.1)
 return rows
def long_forecasts(raw):
 z=[]
 for r in raw:
  c=code(r.get('stockCode') or r.get('code') or r.get('secuCode') or r.get('_query_stock_code'))
  d=pd.to_datetime(r.get('publishDate'),errors='coerce')
  if not c or pd.isna(d): continue
  bid=txt(r.get('orgCode')); bn=txt(r.get('orgSName') or r.get('orgName')); bid=bid or 'NAME:'+bn.lower()
  for fy,k in [(d.year,'predictThisYearEps'),(d.year+1,'predictNextYearEps'),(d.year+2,'predictNextTwoYearEps')]:
   v=pd.to_numeric(r.get(k),errors='coerce')
   if pd.notna(v): z.append([c,d.normalize(),bid,bn,txt(r.get('researcher')),int(fy),float(v),txt(r.get('infoCode')),txt(r.get('title'))])
 q=pd.DataFrame(z,columns=['stock_code','forecast_date','broker_id','broker_name','researcher','forecast_fiscal_year','forecast_EPS','source_record_id','report_title'])
 return q.drop_duplicates(['stock_code','forecast_date','broker_id','forecast_fiscal_year','source_record_id']) if len(q) else q
def prices(sess,ev):
 z=[]
 for c,g in ev.groupby('firm_code'):
  beg=(g.response_date.min()-pd.Timedelta(days=45)).strftime('%Y%m%d'); end=g.response_date.max().strftime('%Y%m%d'); m='1' if c.startswith(('5','6','9')) else '0'
  q={'secid':f'{m}.{c}','klt':'101','fqt':'0','beg':beg,'end':end,'lmt':'1000000','fields1':'f1,f2,f3,f4,f5,f6','fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'}
  try: kl=(getj(sess,PRICE,q).get('data') or {}).get('klines') or []
  except Exception as e: print('PRICE_FAIL',c,e); continue
  for s in kl:
   a=str(s).split(',')
   if len(a)>=3:
    try: z.append([c,pd.Timestamp(a[0]),float(a[2])])
    except: pass
  time.sleep(.05)
 return pd.DataFrame(z,columns=['stock_code','trade_date','close_raw'])
def lastbroker(d):
 return d.sort_values(['broker_id','forecast_date','source_record_id']).groupby('broker_id',as_index=False).tail(1) if len(d) else d
def panel(ev,fc,px):
 z=[]
 for _,e in ev.iterrows():
  a=fc[(fc.stock_code==e.firm_code)&(fc.forecast_fiscal_year==int(e.target_fy))].copy(); rel=(a.forecast_date-e.response_date).dt.days if len(a) else pd.Series(dtype=float)
  pre=lastbroker(a[(rel>=PRE[0])&(rel<=PRE[1])]) if len(a) else a; post=lastbroker(a[(rel>=POST[0])&(rel<=POST[1])]) if len(a) else a
  p=px[(px.stock_code==e.firm_code)&(px.trade_date<e.response_date)].sort_values('trade_date'); p0=float(p.iloc[-1].close_raw) if len(p) else np.nan
  pn=pre.broker_id.nunique() if len(pre) else 0; qn=post.broker_id.nunique() if len(post) else 0
  mt=pre[['broker_id','forecast_EPS']].merge(post[['broker_id','forecast_EPS']],on='broker_id',suffixes=('_pre','_post')) if len(pre) and len(post) else pd.DataFrame()
  mn=mt.broker_id.nunique() if len(mt) else 0; po=pn>=MIN and np.isfinite(p0); qo=qn>=MIN and np.isfinite(p0); mo=mn>=MIN and np.isfinite(p0)
  r=e.to_dict(); r.update(price0=p0,pre_brokers=pn,post_brokers=qn,matched_brokers=mn,pre_usable=int(po),post_usable=int(qo),matched_usable=int(mo),BrokerDisp_PRE=float(pre.forecast_EPS.std(ddof=1)/p0) if po else np.nan,BrokerDisp_POST=float(post.forecast_EPS.std(ddof=1)/p0) if qo else np.nan,BrokerRevisionDisp=float((mt.forecast_EPS_post-mt.forecast_EPS_pre).std(ddof=1)/p0) if mo else np.nan); z.append(r)
 q=pd.DataFrame(z); contam=q.contamination_90d.astype(str).str.upper().isin(['YES','Y','1','TRUE'])
 q['primary_eligible']=((q.pre_usable==1)&(q.post_usable==1)&~contam).astype(int); q['revision_eligible']=((q.matched_usable==1)&~contam).astype(int); return q
def fits(q):
 q=q.copy(); q['RRI10']=pd.to_numeric(q.EventRRI_mean)/10; q['ln_nq']=np.log1p(pd.to_numeric(q.n_questions)); q['response_year']=q.response_date.dt.year.astype(int); q=q.sort_values(['firm_code','response_date','event_id']); q['first_event_firm']=(~q.duplicated('firm_code')).astype(int)
 specs=[('A0',q[q.primary_eligible==1],'BrokerDisp_POST ~ RRI10 + BrokerDisp_PRE'),('A1',q[q.primary_eligible==1],'BrokerDisp_POST ~ RRI10 + BrokerDisp_PRE + ln_nq + C(response_year)+C(event_type)+C(exchange)'),('R1_FIRST_EVENT',q[(q.primary_eligible==1)&(q.first_event_firm==1)],'BrokerDisp_POST ~ RRI10 + BrokerDisp_PRE + ln_nq + C(response_year)+C(event_type)+C(exchange)'),('M1_REVISION',q[q.revision_eligible==1],'BrokerRevisionDisp ~ RRI10 + BrokerDisp_PRE + ln_nq + C(response_year)+C(event_type)+C(exchange)')]
 o=[]
 for n,d,f in specs:
  y=f.split('~')[0].strip(); d=d.dropna(subset=['RRI10','firm_code',y])
  if len(d)<20: o.append({'model':n,'N':len(d),'status':'INSUFFICIENT_N','formula':f}); continue
  try:
   m=smf.ols(f,data=d).fit(cov_type='cluster',cov_kwds={'groups':d.firm_code}); o.append({'model':n,'N':int(m.nobs),'status':'OK','beta_RRI10':float(m.params.RRI10),'se_RRI10':float(m.bse.RRI10),'p_RRI10':float(m.pvalues.RRI10),'r2':float(m.rsquared),'formula':f})
  except Exception as e: o.append({'model':n,'N':len(d),'status':'ERROR:'+str(e),'formula':f})
 return pd.DataFrame(o)
try:
 ev=pd.read_csv(io.BytesIO(gzip.decompress(base64.b64decode(B64))),dtype={'firm_code':str}); ev.firm_code=ev.firm_code.map(code); ev.response_date=pd.to_datetime(ev.response_date); ev.pre_start=pd.to_datetime(ev.pre_start); ev.post_end=pd.to_datetime(ev.post_end)
 s=requests.Session(); s.headers.update({'User-Agent':UA,'Referer':'https://data.eastmoney.com/','Accept':'application/json,text/javascript,*/*'})
 getj(s,REPORT,{'industryCode':'*','pageSize':'1','industry':'*','rating':'*','ratingChange':'*','beginTime':'2024-01-01','endTime':'2024-01-02','pageNo':'1','fields':'','qType':'0','orgCode':'','code':'600000','rcode':'','p':'1','pageNum':'1','pageNumber':'1'},timeout=8,retries=2)
 raw=[]
 for i,(c,g) in enumerate(ev.groupby('firm_code'),1):
  rr=reports(s,c,g.pre_start.min().strftime('%Y-%m-%d'),g.post_end.max().strftime('%Y-%m-%d'))
  for r in rr: r=dict(r); r['_query_stock_code']=c; raw.append(r)
  print(f'REPORTS {i}/{ev.firm_code.nunique()} {c} {len(rr)}')
 pd.DataFrame(raw).to_csv(out/'RRI_PUBLIC_BROKER_REPORTS_RAW.csv',index=False,encoding='utf-8-sig')
 fc=long_forecasts(raw); fc.to_csv(out/'RRI_PUBLIC_BROKER_FORECASTS_LONG.csv',index=False,encoding='utf-8-sig')
 px=prices(s,ev); px.to_csv(out/'RRI_PUBLIC_RAW_PRICES.csv',index=False,encoding='utf-8-sig')
 q=panel(ev,fc,px); q.to_csv(out/'RRI_PUBLIC_BROKER_EVENT_PANEL.csv',index=False,encoding='utf-8-sig')
 n=int(q.primary_eligible.sum()); nr=int(q.revision_eligible.sum()); status='USABLE_DEVELOPMENT_SCREEN' if n>=100 else ('UNDERPOWERED_DESCRIPTIVE_ONLY' if n>=60 else 'SOURCE_COVERAGE_FAILURE_NO_COEFFICIENT_INTERPRETATION')
 cov=pd.DataFrame([['Events',len(q)],['Any PRE broker forecast',int((q.pre_brokers>0).sum())],['Any POST broker forecast',int((q.post_brokers>0).sum())],['PRE usable >=3 brokers',int((q.pre_usable==1).sum())],['POST usable >=3 brokers',int((q.post_usable==1).sum())],['Primary contamination-free sample',n],['Matched revision sample',nr],['Primary coverage status',status]],columns=['metric','value']); cov.to_csv(out/'RRI_PUBLIC_BROKER_COVERAGE.csv',index=False,encoding='utf-8-sig')
 rg=fits(q); rg.to_csv(out/'RRI_PUBLIC_BROKER_REGRESSION_RESULTS.csv',index=False,encoding='utf-8-sig')
 def rr(nm):
  x=rg[rg.model==nm]; return x.iloc[0].to_dict() if len(x) else {}
 a0,a1,r1=rr('A0'),rr('A1'),rr('R1_FIRST_EVENT'); cond={'coverage_ge_100':n>=100,'A1_beta_negative':a1.get('beta_RRI10',np.nan)<0,'A1_p_lt_0_10':a1.get('p_RRI10',np.nan)<.1,'A0_beta_negative':a0.get('beta_RRI10',np.nan)<0,'R1_beta_negative':r1.get('beta_RRI10',np.nan)<0}; dec='DATA_SOURCE_COVERAGE_FAILURE' if n<60 else ('GO_OBTAIN_LICENSED_ANALYST_LEVEL_DATA' if all(cond.values()) else 'NO_GO_PUBLIC_PROXY_DO_NOT_FISH')
 d={'decision':dec,'conditions':cond,'primary_n':n,'note':'Public broker proxy only; frozen design unchanged.'}; (out/'RRI_PUBLIC_BROKER_SCREEN_DECISION.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 (out/'RRI_PUBLIC_BROKER_RUN_STATUS.json').write_text(json.dumps({'status':'COMPLETE','raw_reports':len(raw),'forecast_rows':len(fc),'price_rows':len(px),'primary_n':n,'decision':dec,'frozen_design_changed':False},ensure_ascii=False,indent=2))
 print(cov.to_string(index=False)); print(rg.to_string(index=False)); print(json.dumps(d,ensure_ascii=False,indent=2))
except Exception as e:
 (out/'RRI_PUBLIC_BROKER_RUN_STATUS.json').write_text(json.dumps({'status':'EXECUTION_FAILURE','error_type':type(e).__name__,'error':str(e),'frozen_design_changed':False},ensure_ascii=False,indent=2)); raise
