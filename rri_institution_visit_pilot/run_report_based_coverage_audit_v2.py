from __future__ import annotations

import re
import time
from pathlib import Path

import requests

import run_report_based_coverage_audit as base

ROOT = Path(__file__).resolve().parent
base.OUT = ROOT / "output_report_audit_v2"
base.OUT.mkdir(exist_ok=True)

STOCK_MAP_URLS = [
    "https://www.cninfo.com.cn/new/data/szse_stock.json",
    "http://www.cninfo.com.cn/new/data/szse_stock.json",
]


def load_orgid_map() -> dict[str, str]:
    last = None
    for url in STOCK_MAP_URLS:
        for k in range(4):
            try:
                r = requests.get(url, headers={"User-Agent": base.HEADERS["User-Agent"]}, timeout=30)
                r.raise_for_status()
                o = r.json()
                rows = o.get("stockList") or []
                m = {str(x.get("code") or "").zfill(6): x.get("orgId") for x in rows if x.get("code") and x.get("orgId")}
                if len(m) < 1000:
                    raise RuntimeError(f"orgId map suspiciously small: {len(m)}")
                print("ORGID_MAP", len(m), "from", url)
                return m
            except Exception as e:
                last = e
                print("ORGID_MAP_RETRY", url, k + 1, repr(e))
                time.sleep(k + 1)
    raise RuntimeError(f"cannot load CNINFO orgId map: {last!r}")


ORGID_MAP = load_orgid_map()


def orgid_for(code: str, exchange: str) -> str:
    code = str(code).zfill(6)
    org = ORGID_MAP.get(code)
    if org:
        return org
    # Fallback only; primary mapping is CNINFO official stock list.
    return ("gssh0" if exchange == "SSE" else "gssz0") + code


def _query_once(code: str, exchange: str, year: int, *, category: str, searchkey: str) -> list[dict]:
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
    # First use the annual-report category. If the site category is inconsistent for an old/delisted firm,
    # fall back to unrestricted title search while keeping stock/orgId and filing-year window fixed.
    anns = _query_once(code, exchange, year, category="category_ndbg_szsh;", searchkey="")
    if not anns:
        anns = _query_once(code, exchange, year, category="", searchkey=f"{year}年年度报告")

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
        titles = [base.clean_title(a.get("announcementTitle") or "") for a in anns[:12]]
        raise LookupError(f"annual report not found: {code} {year}; orgId={orgid_for(code, exchange)}; n={len(anns)}; titles={titles}")

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    a = candidates[0][2]
    t = candidates[0][3]
    return {
        "title": t,
        "url": base.STATIC_BASE + (a.get("adjunctUrl") or "").lstrip("/"),
        "announcement_time": a.get("announcementTime"),
    }


base.orgid_for = orgid_for
base.query_annual_report = query_annual_report

if __name__ == "__main__":
    base.main()
