import base64, io, json, time, zlib
from pathlib import Path
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent
EVENT_B64=ROOT/'RRI_EVENT_MASTER_236.csv.zlib.b64'
OUT=ROOT/'analyst_probe_results'
OUT.mkdir(exist_ok=True)


def load_events():
    raw=zlib.decompress(base64.b64decode(EVENT_B64.read_text().strip()))
    df=pd.read_csv(io.BytesIO(raw),dtype={'firm_code':str})
    for c in ['response_date','pre_start','pre_end','post_start','post_end']:
        df[c]=pd.to_datetime(df[c])
    df['firm_code']=df['firm_code'].str.zfill(6)
    return df


def fetch_reports(code, session):
    url='https://reportapi.eastmoney.com/report/list'
    params={
        'industryCode':'*','pageSize':'5000','industry':'*','rating':'*','ratingChange':'*',
        'beginTime':'2000-01-01','endTime':'2027-01-01','pageNo':'1','fields':'','qType':'0',
        'orgCode':'','code':code,'rcode':'','p':'1','pageNum':'1','pageNumber':'1'
    }
    headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/report/stock.jshtml'}
    r=session.get(url,params=params,headers=headers,timeout=45)
    print('HTTP',code,r.status_code,r.url)
    r.raise_for_status()
    js=r.json()
    rows=js.get('data') or []
    total_page=int(js.get('TotalPage') or 1)
    if total_page>1:
        for pg in range(2,total_page+1):
            params.update({'pageNo':str(pg),'p':str(pg),'pageNum':str(pg),'pageNumber':str(pg)})
            rr=session.get(url,params=params,headers=headers,timeout=45); rr.raise_for_status()
            rows.extend((rr.json().get('data') or []))
    return js,rows


def analyst_key(r):
    for k in ['authorID','researcher','author']:
        v=r.get(k)
        if v not in [None,'',[],{}]:
            if isinstance(v,(list,dict)): return json.dumps(v,ensure_ascii=False,sort_keys=True)
            return str(v)
    org=r.get('orgCode') or r.get('orgSName') or r.get('orgName')
    return 'ORG:'+str(org) if org else None


def main():
    ev=load_events().sort_values('response_date')
    # Probe the 30 latest clean events first: most relevant to public API coverage and enough to inspect semantics.
    probe=ev.tail(30).copy()
    codes=probe['firm_code'].drop_duplicates().tolist()
    session=requests.Session()
    allrows=[]; meta=[]
    for i,code in enumerate(codes,1):
        try:
            js,rows=fetch_reports(code,session)
            meta.append({'firm_code':code,'currentYear':js.get('currentYear'),'TotalPage':js.get('TotalPage'),'TotalCount':js.get('TotalCount'),'n_rows':len(rows)})
            for r in rows:
                z={k:r.get(k) for k in ['stockCode','stockName','publishDate','infoCode','orgCode','orgName','orgSName','author','researcher','authorID','predictThisYearEps','predictNextYearEps','predictNextTwoYearEps','predictLastYearEps','actualLastYearEps','actualLastTwoYearEps']}
                z['analyst_key']=analyst_key(r); allrows.append(z)
            print('FETCHED',i,'/',len(codes),code,'rows=',len(rows),'currentYear=',js.get('currentYear'))
        except Exception as e:
            meta.append({'firm_code':code,'error':repr(e),'n_rows':0})
            print('ERROR',code,repr(e))
        time.sleep(0.15)
    pd.DataFrame(meta).to_csv(OUT/'eastmoney_probe_firm_meta.csv',index=False,encoding='utf-8-sig')
    rdf=pd.DataFrame(allrows)
    if rdf.empty:
        raise RuntimeError('No Eastmoney report rows returned')
    rdf['stockCode']=rdf['stockCode'].astype(str).str.zfill(6)
    rdf['publishDate']=pd.to_datetime(rdf['publishDate'],errors='coerce')
    rdf.to_csv(OUT/'eastmoney_probe_raw_rows.csv',index=False,encoding='utf-8-sig')
    print('RAW_COLUMNS',list(rdf.columns))
    print('RAW_SAMPLE')
    print(rdf.sort_values('publishDate').tail(20).to_string(index=False)[:20000])
    cov=[]
    fcols=['predictThisYearEps','predictNextYearEps','predictNextTwoYearEps']
    for _,e in probe.iterrows():
        x=rdf[rdf.stockCode.eq(e.firm_code)].copy()
        pre=x[x.publishDate.between(e.pre_start,e.pre_end)]
        post=x[x.publishDate.between(e.post_start,e.post_end)]
        def n_forecast(a):
            if a.empty:return 0
            return int(a[fcols].notna().any(axis=1).sum())
        cov.append({
            'event_id':e.event_id,'firm_code':e.firm_code,'firm_name':e.firm_name,'response_date':e.response_date.date(),
            'target_fy':int(e.target_fy),'contamination_90d':e.contamination_90d,
            'pre_reports':len(pre),'post_reports':len(post),
            'pre_distinct_analyst_keys':pre.analyst_key.dropna().nunique(),
            'post_distinct_analyst_keys':post.analyst_key.dropna().nunique(),
            'pre_rows_any_eps':n_forecast(pre),'post_rows_any_eps':n_forecast(post),
            'pre_min_date':pre.publishDate.min(),'pre_max_date':pre.publishDate.max(),
            'post_min_date':post.publishDate.min(),'post_max_date':post.publishDate.max(),
        })
    cdf=pd.DataFrame(cov)
    cdf.to_csv(OUT/'eastmoney_probe_event_coverage.csv',index=False,encoding='utf-8-sig')
    summary={
        'events_probed':len(cdf),
        'events_any_pre_or_post_reports':int(((cdf.pre_reports+cdf.post_reports)>0).sum()),
        'events_pre_3_analyst_keys':int((cdf.pre_distinct_analyst_keys>=3).sum()),
        'events_post_3_analyst_keys':int((cdf.post_distinct_analyst_keys>=3).sum()),
        'events_both_3_analyst_keys':int(((cdf.pre_distinct_analyst_keys>=3)&(cdf.post_distinct_analyst_keys>=3)).sum()),
        'events_both_3_and_clean90':int(((cdf.pre_distinct_analyst_keys>=3)&(cdf.post_distinct_analyst_keys>=3)&cdf.contamination_90d.astype(str).str.upper().eq('NO')).sum()),
        'events_any_eps_both_sides':int(((cdf.pre_rows_any_eps>0)&(cdf.post_rows_any_eps>0)).sum()),
    }
    (OUT/'eastmoney_probe_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('COVERAGE_SUMMARY',json.dumps(summary,ensure_ascii=False))
    print(cdf.to_string(index=False)[:30000])

if __name__=='__main__':
    main()
