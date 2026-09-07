#!/usr/bin/env python3
import base64, json, re, zlib
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from numpy.linalg import matrix_rank

BASE=Path(__file__).resolve().parent
OUT=BASE/'analyst_attention_results'; OUT.mkdir(exist_ok=True)
RRI_PATH=BASE/'RRI_FIRM_YEAR_v2.3m_ACTIONS_INPUT.csv'
RRI_B64=BASE/'RRI_FIRM_YEAR_v2.3m_ACTIONS_INPUT.csv.zlib.b64'
ATT_PATH=BASE.parent/'external_attention/CSMAR_cleaned_data.csv'
DTA_PATH=BASE.parent/'external_controls/data/c_output/ControlVars_Y.dta'


def norm_code(x):
    if pd.isna(x): return None
    s=str(x).strip()
    if re.fullmatch(r'\d+(?:\.0+)?',s): return str(int(float(s))).zfill(6)[-6:]
    d=re.sub(r'\D','',s); return d[-6:].zfill(6) if d else None


def year_from(x):
    if pd.isna(x): return np.nan
    s=str(x).strip()
    if re.fullmatch(r'\d{4}(?:\.0+)?',s): return int(float(s))
    dt=pd.to_datetime(s,errors='coerce')
    return dt.year if pd.notna(dt) else np.nan


def load_attention():
    d=pd.read_csv(ATT_PATH,low_memory=False)
    need=['Stkcd','accper','AnaAttention']
    miss=[c for c in need if c not in d.columns]
    if miss: raise RuntimeError('attention source missing '+','.join(miss))
    a=d[need].copy(); a['firm_code']=a.Stkcd.map(norm_code); a['fiscal_year']=a.accper.map(year_from)
    a['AnaAttention']=pd.to_numeric(a.AnaAttention,errors='coerce')
    a=a[a.fiscal_year.between(2014,2025)].copy()
    dup=a.duplicated(['firm_code','fiscal_year'],keep=False)
    print('ATT_ROWS',len(a),'FIRMS',a.firm_code.nunique(),'YEARS',a.fiscal_year.min(),a.fiscal_year.max(),'DUP_ROWS',int(dup.sum()),'NONMISSING',int(a.AnaAttention.notna().sum()))
    if dup.any():
        chk=a[dup].groupby(['firm_code','fiscal_year']).AnaAttention.nunique(dropna=False)
        conflicting=int((chk>1).sum())
        print('ATT_DUP_CONFLICTING_KEYS',conflicting)
        if conflicting: raise RuntimeError('Conflicting duplicate firm-year analyst-attention rows')
        a=a.drop_duplicates(['firm_code','fiscal_year'],keep='first')
    return a[['firm_code','fiscal_year','AnaAttention']]


def load_fin_controls():
    d=pd.read_stata(DTA_PATH,convert_categoricals=False)
    need=['STKCD','YEAR','INDCD','INDNM','IS_FINANCE','ROA','LEV','SIZE']
    miss=[c for c in need if c not in d.columns]
    if miss: raise RuntimeError('financial controls missing '+','.join(miss))
    d=d[need].copy(); d['firm_code']=d.STKCD.map(norm_code); d['fiscal_year']=d.YEAR.map(year_from)
    for c in ['IS_FINANCE','ROA','LEV','SIZE']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[d.fiscal_year.between(2014,2025)].copy()
    d=d.sort_values(['firm_code','fiscal_year']).drop_duplicates(['firm_code','fiscal_year'],keep='last')
    d['industry_code']=d.INDCD.astype(str).str.strip(); d['industry_name']=d.INDNM.astype(str).str.strip()
    return d[['firm_code','fiscal_year','IS_FINANCE','ROA','LEV','SIZE','industry_code','industry_name']]


def build_event_panel(rri,att,fin):
    rri=rri.copy(); rri['firm_code']=rri.firm_code.map(norm_code); rri['rri_year']=pd.to_numeric(rri.rri_year,errors='coerce').astype(int)
    rri=rri.sort_values(['firm_code','rri_year']); rri['first_rri_firm_year']=(rri.groupby('firm_code').cumcount()==0).astype(int)
    aix=att.set_index(['firm_code','fiscal_year']); fix=fin.set_index(['firm_code','fiscal_year'])
    rows=[]
    for _,r in rri.iterrows():
        z=r.to_dict(); c=r.firm_code; t=int(r.rri_year)
        for label,yy in [('pre',t-1),('t',t),('post',t+1)]:
            try:
                q=aix.loc[(c,yy)]; q=q.iloc[-1] if isinstance(q,pd.DataFrame) else q
                z[f'att_{label}']=q.get('AnaAttention',np.nan)
            except Exception: z[f'att_{label}']=np.nan
            try:
                f=fix.loc[(c,yy)]; f=f.iloc[-1] if isinstance(f,pd.DataFrame) else f
                for v in ['IS_FINANCE','ROA','LEV','SIZE','industry_code','industry_name']: z[f'{v}_{label}']=f.get(v,np.nan)
            except Exception:
                for v in ['IS_FINANCE','ROA','LEV','SIZE','industry_code','industry_name']: z[f'{v}_{label}']=np.nan
        for label in ['pre','t','post']:
            x=pd.to_numeric(pd.Series([z.get(f'att_{label}')]),errors='coerce').iloc[0]
            z[f'ln_att_{label}']=np.log1p(x) if pd.notna(x) and x>=0 else np.nan
        z['delta_ln_att']=z['ln_att_post']-z['ln_att_pre'] if pd.notna(z['ln_att_post']) and pd.notna(z['ln_att_pre']) else np.nan
        rows.append(z)
    p=pd.DataFrame(rows)
    flag=pd.to_numeric(p.IS_FINANCE_t,errors='coerce').fillna(pd.to_numeric(p.IS_FINANCE_post,errors='coerce')).fillna(0)
    p['nonfinancial']=(flag!=1).astype(int)
    return p


def add_dummies(X,d,cols):
    for c in cols:
        X=pd.concat([X,pd.get_dummies(d[c].astype(str),prefix=c,drop_first=True,dtype=float)],axis=1)
    return X


def full_rank(w, cols):
    core=[c for c in ['RRI10','PriorAttention','Size','Leverage','ROA','LnQuestions'] if c in cols]
    other=sorted([c for c in cols if c not in core])
    A=np.ones((len(w),1)); rank=matrix_rank(A); kept=[]; dropped=[]
    for c in core:
        cand=np.column_stack([A,w[c].to_numpy(float)])
        nr=matrix_rank(cand)
        if nr<=rank: raise RuntimeError('core regressor redundant: '+c)
        A=cand; rank=nr; kept.append(c)
    for c in other:
        cand=np.column_stack([A,w[c].to_numpy(float)])
        nr=matrix_rank(cand)
        if nr>rank: A=cand; rank=nr; kept.append(c)
        else: dropped.append(c)
    return kept,dropped,rank


def fit(panel,kind='AA1',first=False):
    d=panel[panel.nonfinancial==1].copy()
    if first: d=d[d.first_rri_firm_year==1]
    outcome='delta_ln_att' if kind=='AA3' else 'ln_att_post'
    y=pd.to_numeric(d[outcome],errors='coerce')
    X=pd.DataFrame(index=d.index); X['RRI10']=pd.to_numeric(d.AnnualRRI10,errors='coerce')
    if kind in ['AA1','AA2']:
        X['PriorAttention']=pd.to_numeric(d.ln_att_pre,errors='coerce')
    if kind in ['AA1','AA2','AA3']:
        X['Size']=pd.to_numeric(d.SIZE_t,errors='coerce'); X['Leverage']=pd.to_numeric(d.LEV_t,errors='coerce'); X['ROA']=pd.to_numeric(d.ROA_t,errors='coerce'); X['LnQuestions']=np.log1p(pd.to_numeric(d.total_questions,errors='coerce'))
        X=add_dummies(X,d,['rri_year','event_type','industry_code_t'])
    w=pd.concat([y.rename('Y'),X,d[['firm_code']]],axis=1).dropna()
    raw=[c for c in w.columns if c not in ['Y','firm_code']]
    base={'spec':kind,'first_event_only':int(first),'N':len(w),'outcome':outcome}
    if len(w)<120 and kind!='AA0': return {**base,'coverage_gate_pass':False,'beta_RRI10':np.nan,'se_cluster':np.nan,'p_cluster':np.nan,'note':'coverage gate <120'}
    kept,dropped,rank=full_rank(w,raw)
    Xv=sm.add_constant(w[kept].to_numpy(float),has_constant='add')
    mod=sm.OLS(w.Y.to_numpy(float),Xv).fit(cov_type='cluster',cov_kwds={'groups':w.firm_code.astype(str).to_numpy()})
    i=(['const']+kept).index('RRI10')
    return {**base,'coverage_gate_pass':True,'beta_RRI10':float(mod.params[i]),'se_cluster':float(mod.bse[i]),'p_cluster':float(mod.pvalues[i]),'r2':float(mod.rsquared),'matrix_rank':int(matrix_rank(Xv)),'n_columns':int(Xv.shape[1]),'dropped_redundant':';'.join(dropped),'note':''}


def main():
    if not RRI_PATH.exists(): RRI_PATH.write_bytes(zlib.decompress(base64.b64decode(RRI_B64.read_text().strip())))
    rri=pd.read_csv(RRI_PATH,dtype={'firm_code':str}); att=load_attention(); fin=load_fin_controls(); panel=build_event_panel(rri,att,fin)
    panel.to_csv(OUT/'RRI_ANALYST_ATTENTION_EVENT_PANEL.csv',index=False,encoding='utf-8-sig')
    paired=(panel.nonfinancial==1)&panel.ln_att_pre.notna()&panel.ln_att_post.notna()
    coverage={'rri_firm_years':int(len(panel)),'paired_pre_post_nonfinancial':int(paired.sum()),'coverage_gate':120,'coverage_gate_pass':bool(paired.sum()>=120),'pre_nonmissing':int(panel.ln_att_pre.notna().sum()),'post_nonmissing':int(panel.ln_att_post.notna().sum()),'attention_source_year_min':int(att.fiscal_year.min()),'attention_source_year_max':int(att.fiscal_year.max())}
    (OUT/'RRI_ANALYST_ATTENTION_COVERAGE.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
    print('COVERAGE',json.dumps(coverage,ensure_ascii=False))
    if not coverage['coverage_gate_pass']:
        print('COVERAGE GATE FAIL — coefficients will not be interpreted.')
        return
    results=[fit(panel,'AA0'),fit(panel,'AA1'),fit(panel,'AA2',first=True),fit(panel,'AA3')]
    rr=pd.DataFrame(results); rr.to_csv(OUT/'RRI_ANALYST_ATTENTION_RESULTS.csv',index=False,encoding='utf-8-sig')
    print('RESULTS\n'+rr.to_string(index=False))

if __name__=='__main__': main()
