#!/usr/bin/env python3
import fetch_ashare_modified_jones_inputs_v1_0 as f

# Pure data-interface compatibility fix: Eastmoney no longer exposes CIP in this report.
# CIP is not used anywhere in the frozen Modified Jones specification.
f.REPORTS['balance']['columns'] = [c for c in f.REPORTS['balance']['columns'] if c != 'CIP']

if __name__ == '__main__':
    f.main()
