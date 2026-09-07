#!/usr/bin/env python3
import fetch_ashare_modified_jones_inputs_v1_0 as f

# Pure data-interface compatibility fix only.
# Ask Eastmoney for ALL raw columns, then the frozen normalizer selects the fields
# required by Modified Jones. This avoids semantic API failures when a named field
# is not exposed in a particular report schema/version.
for kind in ['balance','income','cashflow']:
    f.REPORTS[kind]['columns'] = 'ALL'

if __name__ == '__main__':
    f.main()
