from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

import run_report_based_coverage_audit as base

ROOT = Path(__file__).resolve().parent
base.OUT = ROOT / "output_report_audit_v3"
base.OUT.mkdir(exist_ok=True)

TOPSEARCH = "https://www.cninfo.com.cn/new/information/topSearch/query"


def lookup_one(code: str) -> tuple[str, str | None, str]:
    code = str(code).zfill(6)
    last = None
    for k in range(6):
        try:
            r = requests.post(
                TOPSEARCH,
                headers=base.HEADERS,
                data={"keyWord": code, "maxNum": "10"},
                timeout=22,
            )
            r.raise_for_status()
            rows = r.json()
            for x in rows if isinstance(rows, list) else []:
                if str(x.get("code") or "").zfill(6) == code and x.get("orgId"):
                    return code, str(x["orgId"]), str(x.get("zwjc") or "")
            last = RuntimeError(f"no exact topSearch match: {rows!r}")
        except Exception as e:
            last = e
        time.sleep(min(6, k + 1))
    return code, None, repr(last)


def build_orgid_map() -> dict[str, str]:
    df = pd.read_csv(base.SAMPLE, dtype={"firm_code": str})
    codes = sorted(set(df["firm_code"].str.zfill(6)))
    out: dict[str, str] = {}
    audit = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(lookup_one, c): c for c in codes}
        for fut in as_completed(futs):
            code, org, note = fut.result()
            ok = org is not None
            audit.append({"firm_code": code, "orgId": org or "", "ok": ok, "name_or_error": note})
            if org:
                out[code] = org
            print("ORGID", code, org, note)
    pd.DataFrame(audit).sort_values("firm_code").to_csv(base.OUT / "00_ORGID_AUDIT.csv", index=False, encoding="utf-8-sig")
    print("ORGID_SUCCESS", len(out), "/", len(codes))
    return out


ORGID_MAP = build_orgid_map()


def orgid_for(code: str, exchange: str) -> str:
    code = str(code).zfill(6)
    if code not in ORGID_MAP:
        raise LookupError(f"orgId unresolved for {code}")
    return ORGID_MAP[code]


def _query(code: str, exchange: str, year: int, category: str, searchkey: str) -> list[dict]:
    body = {
        "tabName": "fulltext",
        "pageSize": "30",
        "pageNum": "1",
        "column": "",
        "category": category,
        "plate": "",
        "searchkey": searchkey,
        "secid": "",
        "trade": "",
        "seDate": f"{year+1}-01-01~{year+1}-10-31",
        "stock": f"{code},{orgid_for(code, exchange)}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    o = base.request_json(body, retries=5)
    return o.get("announcements") or []


def query_annual_report(code: str, exchange: str, year: int) -> dict:
    anns = _query(code, exchange, year, "category_ndbg_szsh;", "")
    if not anns:
        anns = _query(code, exchange, year, "", f"{year}年年度报告")
    candidates = []
    for a in anns:
        t = base.clean_title(a.get("announcementTitle") or "")
        if f"{year}年年度报告" not in t:
            continue
        if "摘要" in t or "英文" in t or "取消" in t:
            continue
        score = 0
        if t in {f"{year}年年度报告", f"{year}年年度报告全文", f"{year}年年度报告正文"}:
            score += 6
        if "全文" in t or "正文" in t:
            score += 2
        if "修订" in t or "更新" in t:
            score += 1
        candidates.append((score, int(a.get("announcementTime") or 0), a, t))
    if not candidates:
        titles = [base.clean_title(a.get("announcementTitle") or "") for a in anns[:15]]
        raise LookupError(
            f"annual report not found: {code} {year}; orgId={orgid_for(code, exchange)}; n={len(anns)}; titles={titles}"
        )
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    a = candidates[0][2]
    return {
        "title": candidates[0][3],
        "url": base.STATIC_BASE + (a.get("adjunctUrl") or "").lstrip("/"),
        "announcement_time": a.get("announcementTime"),
    }


base.orgid_for = orgid_for
base.query_annual_report = query_annual_report

if __name__ == "__main__":
    base.main()
