#!/usr/bin/env python3
import fetch_ashare_modified_jones_inputs_v1_0 as f

# Pure data-interface compatibility fixes only.
# 1) Ask Eastmoney for ALL raw columns; the frozen normalizer then selects the
#    fields required by Modified Jones.
# 2) Eastmoney's annual results table exposes industry as PUBLISHNAME.
# 3) RPT_DMSK_FN_INCOME exposes listed-company net income as PARENT_NETPROFIT
#    (net income attributable to common/parent shareholders). We map that raw
#    field to the generic `net_profit` variable used in the frozen accrual formula.
# No Modified Jones equation, peer rule, RRI variable, sample rule, or F2 model is changed.
for kind in ['balance','income','cashflow']:
    f.REPORTS[kind]['columns'] = 'ALL'

_original_choose = f.choose_industry_column

def choose_industry_column_compat(df):
    if 'PUBLISHNAME' in df.columns and df['PUBLISHNAME'].notna().sum() > 0:
        return 'PUBLISHNAME'
    return _original_choose(df)

f.choose_industry_column = choose_industry_column_compat

_original_normalize = f.normalize_year

def normalize_year_compat(year, bal, inc, cf, ind):
    out = _original_normalize(year, bal, inc, cf, ind)
    if 'parent_net_profit' in out.columns and out['parent_net_profit'].notna().sum() > 0:
        out['net_profit'] = out['parent_net_profit']
    return out

f.normalize_year = normalize_year_compat

if __name__ == '__main__':
    f.main()
