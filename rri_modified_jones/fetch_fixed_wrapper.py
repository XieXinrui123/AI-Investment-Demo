#!/usr/bin/env python3
import fetch_ashare_modified_jones_inputs_v1_0 as f

# Pure data-interface compatibility fixes only.
# 1) Ask Eastmoney for ALL raw columns, then the frozen normalizer selects the fields
#    required by Modified Jones.
# 2) Eastmoney's annual results table exposes the industry name as PUBLISHNAME.
#    This is the same raw field that AKShare historically maps to “所处行业”.
for kind in ['balance','income','cashflow']:
    f.REPORTS[kind]['columns'] = 'ALL'

_original_choose = f.choose_industry_column

def choose_industry_column_compat(df):
    if 'PUBLISHNAME' in df.columns and df['PUBLISHNAME'].notna().sum() > 0:
        return 'PUBLISHNAME'
    return _original_choose(df)

f.choose_industry_column = choose_industry_column_compat

if __name__ == '__main__':
    f.main()
