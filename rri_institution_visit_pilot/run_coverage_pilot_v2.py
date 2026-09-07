#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import pandas as pd
import requests
import run_coverage_pilot as base


def fetch_report_v2(session, report_name, columns, code, start_date, end_date, page_size=500, retries=5):
    # Eastmoney requires quoted dates with single quotes in filter expressions.
    filt = f'(IS_SOURCE="1")(SECURITY_CODE="{code}")(RECEIVE_START_DATE>=\'{start_date}\')(RECEIVE_START_DATE<=\'{end_date}\')'
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
            r=session.get(base.BASE,params=params,timeout=30); r.raise_for_status(); obj=r.json()
            if obj.get('success') is False:
                raise RuntimeError(f"Eastmoney code={obj.get('code')} message={obj.get('message')}")
            result=obj.get('result')
            if result is None:
                return pd.DataFrame(), True, None
            pages=int(result.get('pages') or 0)
            rows=list(result.get('data') or [])
            for page in range(2,pages+1):
                params['pageNumber']=str(page)
                rr=session.get(base.BASE,params=params,timeout=30); rr.raise_for_status(); oo=rr.json()
                if oo.get('success') is False:
                    raise RuntimeError(f"Eastmoney page={page} code={oo.get('code')} message={oo.get('message')}")
                rows.extend(((oo.get('result') or {}).get('data') or [])); time.sleep(0.05)
            return pd.DataFrame(rows), True, None
        except Exception as e:
            last=str(e); time.sleep(1.2*(attempt+1))
    return pd.DataFrame(), False, last


base.fetch_report = fetch_report_v2
base.main()
