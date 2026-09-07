#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json, time
import pandas as pd
import requests

URL='https://datacenter-web.eastmoney.com/api/data/v1/get'


def fetch_one(row):
    code=str(row.firm_code).zfill(6); rd=pd.Timestamp(row.response_date)
    start=(rd-pd.Timedelta(days=90)).strftime('%Y-%m-%d'); end=(rd+pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    filt=f'(NUMBERNEW="1")(IS_SOURCE="1")(SECURITY_CODE="{code}")(RECEIVE_START_DATE>=\'{start}\')(RECEIVE_START_DATE<=\'{end}\')'
    params={'sortColumns':'NOTICE_DATE,SUM,RECEIVE_START_DATE,SECURITY_CODE','sortTypes':'-1,-1,-1,1','pageSize':'500','pageNumber':'1','reportName':'RPT_ORG_SURVEYNEW','columns':'ALL','source':'WEB','client':'WEB','filter':filt}
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 Chrome/124 Safari/537.36','Referer':'https://data.eastmoney.com/jgdy/'})
    last=None
    for attempt in range(3):
      try:
        o=s.get(URL,params=params,timeout=20).json()
        if o.get('success') is False:
          if int(o.get('code') or 0)==9201:
            data=[]; api_ok=True; err=None; break
          raise RuntimeError(f"code={o.get('code')} message={o.get('message')}")
        r=o.get('result') or {}; data=list(r.get('data') or []); pages=int(r.get('pages') or 0)
        for p in range(2,pages+1):
          params['pageNumber']=str(p); oo=s.get(URL,params=params,timeout=20).json()
          if oo.get('success') is False: raise RuntimeError(f"page={p} code={oo.get('code')} message={oo.get('message')}")
          data.extend(((oo.get('result') or {}).get('data') or []))
        api_ok=True; err=None; break
      except Exception as e:
        last=str(e); time.sleep(0.5*(attempt+1))
    else:
      data=[]; api_ok=False; err=last
    d=pd.DataFrame(data)
    if d.empty:
      vp=vq=ip=iq=0; parse=1.0
    else:
      dates=pd.to_datetime(d.get('RECEIVE_START_DATE'),errors='coerce'); parse=float(dates.notna().mean())
      sums=pd.to_numeric(d.get('SUM'),errors='coerce').fillna(0) if 'SUM' in d else pd.Series([0]*len(d),index=d.index)
      pre=(dates>=rd-pd.Timedelta(days=90))&(dates<=rd-pd.Timedelta(days=1))
      post=(dates>=rd+pd.Timedelta(days=1))&(dates<=rd+pd.Timedelta(days=90))
      vp=int(pre.sum()); vq=int(post.sum()); ip=float(sums[pre].sum()); iq=float(sums[post].sum())
    return {
      'event_id':row.event_id,'firm_code':code,'firm_name':row.firm_name,'exchange':row.exchange,'response_date':row.response_date,
      'rri_q':int(row.rri_q),'period':row.period,'event_type':row.event_type,
      'api_ok':api_ok,'error':err,'date_parse_rate':parse,
      'visits_pre':vp,'visits_post':vq,'institution_participations_pre':ip,'institution_participations_post':iq,
      'any_pre':vp>0,'any_post':vq>0
    }, data


def main():
    here=Path(__file__).resolve().parent; out=here/'output_fast'; out.mkdir(exist_ok=True)
    sample=pd.read_csv(here/'PILOT_SAMPLE_30.csv',dtype={'firm_code':str})
    rows=[]; raw=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
      fs={ex.submit(fetch_one,r):r.event_id for _,r in sample.iterrows()}
      for f in as_completed(fs):
        rec,data=f.result(); rows.append(rec)
        for x in data: x=dict(x); x['event_id']=rec['event_id']; raw.append(x)
    c=pd.DataFrame(rows).sort_values('event_id'); r=pd.DataFrame(raw)
    c.to_csv(out/'EVENT_COVERAGE.csv',index=False,encoding='utf-8-sig'); r.to_csv(out/'RAW_SURVEY_SUMMARY.csv',index=False,encoding='utf-8-sig')
    ok=int(c.api_ok.sum()); pre=int(c.any_pre.sum()); post=int(c.any_post.sum()); both=int((c.any_pre&c.any_post).sum())
    s={'pilot_n':30,'api_ok_n':ok,'any_pre_n':pre,'any_post_n':post,'both_windows_activity_n':both,
       'zero_both_windows_n':int((~c.any_pre&~c.any_post).sum()),'total_visits_pre':int(c.visits_pre.sum()),'total_visits_post':int(c.visits_post.sum()),
       'total_institution_participations_pre':float(c.institution_participations_pre.sum()),'total_institution_participations_post':float(c.institution_participations_post.sum()),
       'median_visits_pre':float(c.visits_pre.median()),'median_visits_post':float(c.visits_post.median()),'raw_rows':len(r)}
    # Feasibility rule is about usable variation, not significance: require at least 10/30 events with post activity and >=8/30 with activity in both windows.
    s['activity_gate_rule']='PASS if API ok >=27/30, post activity >=10/30, and both-window activity >=8/30'
    s['activity_gate']='PASS' if ok>=27 and post>=10 and both>=8 else 'FAIL'
    (out/'SUMMARY.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(s,ensure_ascii=False,indent=2)); print(c.to_string(index=False))

if __name__=='__main__': main()
