from pathlib import Path

src=Path('rri_op_input/test_rri_operating_performance_v1_0.py')
out=Path('rri_op_input/test_rri_operating_performance_v1_1_fullrank.py')
s=src.read_text(encoding='utf-8')

anchor='''def add_dummies(X, d, cols):\n    for c in cols:\n        if c not in d.columns:\n            continue\n        dum = pd.get_dummies(\n            d[c].astype(str), prefix=c, drop_first=True, dtype=float\n        )\n        X = pd.concat([X, dum], axis=1)\n    return X\n'''
helper='''def add_dummies(X, d, cols):\n    for c in cols:\n        if c not in d.columns:\n            continue\n        dum = pd.get_dummies(\n            d[c].astype(str), prefix=c, drop_first=True, dtype=float\n        )\n        X = pd.concat([X, dum], axis=1)\n    return X\n\ndef full_rank_design(work, cols):\n    # Implementation-only fix: retain all continuous/core regressors and select\n    # a deterministic non-aliased basis for fixed-effect dummies. This does not\n    # change the fixed-effect span or the frozen economic specification.\n    dummy_prefixes=(\"rri_year_\",\"event_type_\",\"industry_code_t_\")\n    core=[c for c in cols if not c.startswith(dummy_prefixes)]\n    dummies=sorted([c for c in cols if c.startswith(dummy_prefixes)])\n    selected=[]\n    Xv=np.ones((len(work),1),dtype=float)\n    rank=np.linalg.matrix_rank(Xv)\n    for c in core:\n        cand=np.column_stack([Xv,work[c].to_numpy(float)])\n        newrank=np.linalg.matrix_rank(cand)\n        if newrank==rank:\n            raise ValueError(f\"Required core regressor is aliased: {c}\")\n        selected.append(c); Xv=cand; rank=newrank\n    for c in dummies:\n        cand=np.column_stack([Xv,work[c].to_numpy(float)])\n        newrank=np.linalg.matrix_rank(cand)\n        if newrank>rank:\n            selected.append(c); Xv=cand; rank=newrank\n    return selected, Xv\n'''
if anchor not in s: raise SystemExit('add_dummies anchor not found')
s=s.replace(anchor,helper,1)
old='''    cols = [c for c in work.columns if c not in (\"Y\",\"firm_code\")]\n    Xv = sm.add_constant(work[cols].to_numpy(float), has_constant=\"add\")\n    fit = sm.OLS(work[\"Y\"].to_numpy(float), Xv).fit(\n'''
new='''    cols = [c for c in work.columns if c not in (\"Y\",\"firm_code\")]\n    cols, Xv = full_rank_design(work, cols)\n    fit = sm.OLS(work[\"Y\"].to_numpy(float), Xv).fit(\n'''
if s.count(old)!=2: raise SystemExit(f'expected 2 design blocks, found {s.count(old)}')
s=s.replace(old,new)
s=s.replace('''            \"pct_of_233\": float(valid.mean())''','''            \"pct_of_232\": float(valid.mean())''')
out.write_text(s,encoding='utf-8')
print('patched',src,'->',out)
