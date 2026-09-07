#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, time
from pathlib import Path
import pandas as pd
import requests

BASE='https://datacenter-web.eastmoney.com/api/data/v1/get'
UA='Mozilla/5.0 Chrome/124 Safari/537.36'


def fetch_report(session, report_name, columns, code, start_date, end_date, page_size=500, retries=5):
    filt = f'(IS_SOURCE="1")(SECURITY_CODE="{code}")(RECEIVE_START_DATE>="{start_date}")(RECEIVE_START_DATE<="{end_date}")'
    if report_name == 'RPT_ORG_SURVEYNEW':
        filt = f'(NUMBERNEW="1")' + filt
        sort_columns='NOTICE_DATE,SUM,RECEIVE_START_DATE,SECURITY_CODE'
        sort_types='-1,-1,-1,1'
    else:
        sort_columns='NOTICE_DATE,RECEIVE_START_DATE,SECURITY_CODE,NUMBERNEW'
        sort_types='-1,-1,1,-1'
    params={
        'sortColumns':sort_columns,'sortTypes':sort_types,'pageSize':str(page_size),'pageNumber':'1',
        'reportName':report_name,'columns':columns,'source':'WEB','client':'WEB','filter':filt
    }
    if report_name == 'RPT_ORG_SURVEY':
        params['quoteType']='0'
    last=None
    for attempt in range(retries):
        try:
            r=session.get(BASE,params=params,timeout=30)
            r.raise_for_status()
            obj=r.json()
            result=obj.get('result')
            if result is None:
                # Eastmoney may return null result for a valid empty query.
                return pd.DataFrame(), True, None
            pages=int(result.get('pages') or 0)
            rows=list(result.get('data') or [])
            for page in range(2,pages+1):
                params['pageNumber']=str(page)
                rr=session.get(BASE,params=params,timeout=30); rr.raise_for_status(); oo=rr.json()
                rows.extend(((oo.get('result') or {}).get('data') or []))
                time.sleep(0.05)
            return pd.DataFrame(rows), True, None
        except Exception as e:
            last=str(e); time.sleep(1.2*(attempt+1))
    return pd.DataFrame(), False, last


def window_counts(df, date_col, response_date, org_col=None):
    if df.empty or date_col not in df.columns:
        return {'pre_rows':0,'post_rows':0,'day0_rows':0,'unique_org_pre':0,'unique_org_post':0,'date_parse_rate':1.0}
    z=df.copy(); z['_d']=pd.to_datetime(z[date_col],errors='coerce')
    parse_rate=float(z['_d'].notna().mean()) if len(z) else 1.0
    pre=z[(z['_d']>=response_date-pd.Timedelta(days=90))&(z['_d']<=response_date-pd.Timedelta(days=1))]
    post=z[(z['_d']>=response_date+pd.Timedelta(days=1))&(z['_d']<=response_date+pd.Timedelta(days=90))]
    day0=z[z['_d']==response_date]
    out={'pre_rows':len(pre),'post_rows':len(post),'day0_rows':len(day0),'unique_org_pre':0,'unique_org_post':0,'date_parse_rate':parse_rate}
    if org_col and org_col in z.columns:
        out['unique_org_pre']=int(pre[org_col].dropna().astype(str).nunique())
        out['unique_org_post']=int(post[org_col].dropna().astype(str).nunique())
    return out


def main():
    here=Path(__file__).resolve().parent
    sample=pd.read_csv(here/'PILOT_SAMPLE_30.csv',dtype={'firm_code':str})
    assert len(sample)==30
    outdir=here/'output'; outdir.mkdir(exist_ok=True)
    session=requests.Session(); session.headers.update({'User-Agent':UA,'Referer':'https://data.eastmoney.com/jgdy/'})
    raw_sum=[]; raw_det=[]; cov=[]
    detail_cols='SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NOTICE_DATE,RECEIVE_START_DATE,RECEIVE_OBJECT,RECEIVE_PLACE,RECEIVE_WAY_EXPLAIN,INVESTIGATORS,RECEPTIONIST,ORG_TYPE'

    for _,e in sample.iterrows():
        code=str(e.firm_code).zfill(6); rd=pd.Timestamp(e.response_date)
        start=(rd-pd.Timedelta(days=90)).strftime('%Y-%m-%d'); end=(rd+pd.Timedelta(days=90)).strftime('%Y-%m-%d')
        s,s_ok,s_err=fetch_report(session,'RPT_ORG_SURVEYNEW','ALL',code,start,end)
        d,d_ok,d_err=fetch_report(session,'RPT_ORG_SURVEY',detail_cols,code,start,end,page_size=100)
        if not s.empty:
            s.insert(0,'event_id',e.event_id); raw_sum.append(s)
        if not d.empty:
            d.insert(0,'event_id',e.event_id); raw_det.append(d)
        sc=window_counts(s,'RECEIVE_START_DATE',rd)
        dc=window_counts(d,'RECEIVE_START_DATE',rd,'RECEIVE_OBJECT')
        sum_inst_pre=sum_inst_post=0.0
        if not s.empty and 'SUM' in s.columns:
            ss=s.copy(); ss['_d']=pd.to_datetime(ss['RECEIVE_START_DATE'],errors='coerce'); ss['SUM']=pd.to_numeric(ss['SUM'],errors='coerce').fillna(0)
            sum_inst_pre=float(ss.loc[(ss['_d']>=rd-pd.Timedelta(days=90))&(ss['_d']<=rd-pd.Timedelta(days=1)),'SUM'].sum())
            sum_inst_post=float(ss.loc[(ss['_d']>=rd+pd.Timedelta(days=1))&(ss['_d']<=rd+pd.Timedelta(days=90)),'SUM'].sum())
        mismatch = bool((sc['pre_rows']+sc['post_rows']>0) and (dc['pre_rows']+dc['post_rows']==0))
        primary_usable=bool(s_ok and sc['date_parse_rate']>=0.95)
        detail_usable=bool(d_ok and dc['date_parse_rate']>=0.95 and not mismatch)
        cov.append({
            **{k:e[k] for k in ['event_id','firm_code','firm_name','exchange','response_date','EventRRI_mean','rri_q','period','event_type']},
            'summary_api_ok':s_ok,'detail_api_ok':d_ok,'summary_error':s_err,'detail_error':d_err,
            'visits_pre':sc['pre_rows'],'visits_post':sc['post_rows'],'summary_day0_rows':sc['day0_rows'],
            'institution_participations_pre':sum_inst_pre,'institution_participations_post':sum_inst_post,
            'detail_rows_pre':dc['pre_rows'],'detail_rows_post':dc['post_rows'],
            'unique_institutions_pre':dc['unique_org_pre'],'unique_institutions_post':dc['unique_org_post'],
            'summary_date_parse_rate':sc['date_parse_rate'],'detail_date_parse_rate':dc['date_parse_rate'],
            'summary_detail_mismatch':mismatch,'primary_usable':primary_usable,'detail_usable':detail_usable,
            'any_activity_pre':bool(sc['pre_rows']>0),'any_activity_post':bool(sc['post_rows']>0)
        })
        time.sleep(0.1)

    raw_summary=pd.concat(raw_sum,ignore_index=True) if raw_sum else pd.DataFrame()
    raw_detail=pd.concat(raw_det,ignore_index=True) if raw_det else pd.DataFrame()
    coverage=pd.DataFrame(cov)
    raw_summary.to_csv(outdir/'02_RAW_SURVEY_SUMMARY.csv',index=False,encoding='utf-8-sig')
    raw_detail.to_csv(outdir/'03_RAW_SURVEY_DETAIL.csv',index=False,encoding='utf-8-sig')
    coverage.to_csv(outdir/'04_EVENT_COVERAGE.csv',index=False,encoding='utf-8-sig')

    n=len(coverage); pu=int(coverage.primary_usable.sum()); du=int(coverage.detail_usable.sum())
    proj=round(226*pu/n)
    by_period=coverage.groupby('period')['primary_usable'].agg(['sum','count']).reset_index().to_dict('records')
    by_exchange=coverage.groupby('exchange')['primary_usable'].agg(['sum','count']).reset_index().to_dict('records')
    gate=bool(pu>=27 and all(x['sum']>=8 for x in by_period) and all(x['sum']>=13 for x in by_exchange) and proj>=100)
    summary={
        'pilot_n':n,'primary_usable_n':pu,'detail_usable_n':du,'primary_usable_rate':pu/n,
        'projected_primary_usable_of_226':proj,'events_with_any_pre_activity':int(coverage.any_activity_pre.sum()),
        'events_with_any_post_activity':int(coverage.any_activity_post.sum()),
        'events_with_activity_both_windows':int((coverage.any_activity_pre & coverage.any_activity_post).sum()),
        'median_visits_pre':float(coverage.visits_pre.median()),'median_visits_post':float(coverage.visits_post.median()),
        'total_summary_rows':int(len(raw_summary)),'total_detail_rows':int(len(raw_detail)),
        'by_period':by_period,'by_exchange':by_exchange,
        'gate_rule':'PASS if primary usable >=27/30, each period >=8/10, each exchange >=13/15, and projected usable >=100/226',
        'coverage_gate':'PASS' if gate else 'FAIL',
        'note':'Zero visits are valid observed zeros when the API query succeeds; coverage is not defined as nonzero activity.'
    }
    (outdir/'05_COVERAGE_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    md=f'''# RRI → Institutional Visit Coverage Pilot\n\n**Coverage gate: {summary['coverage_gate']}**\n\n- Pilot events: {n}\n- Primary usable: {pu}/{n} ({pu/n:.1%})\n- Detailed institution-level usable: {du}/{n} ({du/n:.1%})\n- Projected primary usable out of 226: {proj}\n- Any PRE activity: {summary['events_with_any_pre_activity']}/{n}\n- Any POST activity: {summary['events_with_any_post_activity']}/{n}\n- Activity in both windows: {summary['events_with_activity_both_windows']}/{n}\n- Raw summary rows: {len(raw_summary)}\n- Raw detailed institution rows: {len(raw_detail)}\n\nImportant: a successful query with zero visits is treated as an observed zero, not missing coverage. No RRI coefficient is estimated in this pilot.\n'''
    (outdir/'06_COVERAGE_GATE.md').write_text(md,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(coverage[['event_id','firm_code','period','exchange','visits_pre','visits_post','unique_institutions_pre','unique_institutions_post','primary_usable','detail_usable']].to_string(index=False))

if __name__=='__main__': main()
