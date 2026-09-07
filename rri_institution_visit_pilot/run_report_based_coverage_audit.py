from __future__ import annotations

import io
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "PILOT_SAMPLE_30.csv"
OUT = ROOT / "output_report_audit"
OUT.mkdir(exist_ok=True)

CNINFO_QUERY = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC_BASE = "https://static.cninfo.com.cn/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
}

IR_KEYWORDS = (
    "接待调研",
    "接待时间",
    "实地调研",
    "投资者关系活动",
    "调研的基本情况",
    "接待对象",
    "接待方式",
    "特定对象调研",
)
ZERO_PATTERNS = (
    r"报告期内未发生接待调研.{0,20}活动",
    r"报告期内没有接待调研.{0,20}活动",
    r"报告期内未发生投资者关系活动",
    r"报告期内无接待调研.{0,20}活动",
    r"本报告期未发生接待调研.{0,20}活动",
    r"本报告期无接待调研.{0,20}活动",
)
DATE_RE = re.compile(r"(?P<y>20\d{2})\s*年\s*(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日")
METHOD_RE = re.compile(r"实地调研|电话沟通|电话会议|网络方式|现场参观|其他|策略会|路演|业绩说明会|特定对象调研")
OBJ_RE = re.compile(r"机构|个人|其他")


def compact(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def orgid_for(code: str, exchange: str) -> str:
    code = str(code).zfill(6)
    if exchange == "SZSE":
        return "gssz0" + code
    if exchange == "SSE":
        return "gssh0" + code
    raise ValueError(exchange)


def plate_for(exchange: str) -> str:
    return "sz" if exchange == "SZSE" else "sh"


def request_json(body: dict, retries: int = 6) -> dict:
    last = None
    for k in range(retries):
        try:
            r = requests.post(CNINFO_QUERY, headers=HEADERS, data=body, timeout=35)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(min(8, 1.5 * (k + 1)))
    raise RuntimeError(f"CNINFO query failed after retries: {last!r}")


def request_bytes(url: str, retries: int = 5) -> bytes:
    last = None
    for k in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=90)
            r.raise_for_status()
            b = r.content
            if len(b) < 10000:
                raise RuntimeError(f"PDF too small: {len(b)}")
            return b
        except Exception as e:
            last = e
            time.sleep(min(8, 1.5 * (k + 1)))
    raise RuntimeError(f"PDF download failed after retries: {last!r}")


def clean_title(t: str) -> str:
    return re.sub(r"</?em>", "", t or "").strip()


def query_annual_report(code: str, exchange: str, year: int) -> dict:
    # Annual report for fiscal year y is normally filed in y+1; allow late/revised filings.
    start = f"{year+1}-01-01"
    end = f"{year+1}-10-31"
    body = {
        "tabName": "fulltext",
        "pageSize": "30",
        "pageNum": "1",
        "column": "szse",
        "category": "category_ndbg_szsh;",
        "plate": plate_for(exchange),
        "searchkey": "",
        "secid": "",
        "trade": "",
        "seDate": f"{start}~{end}",
        "stock": f"{code},{orgid_for(code, exchange)}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    o = request_json(body)
    anns = o.get("announcements") or []
    candidates = []
    for a in anns:
        t = clean_title(a.get("announcementTitle") or "")
        if f"{year}年年度报告" not in t:
            continue
        if "摘要" in t or "英文" in t or "取消" in t:
            continue
        # Prefer full/body reports over ancillary filings.
        score = 0
        if t in {f"{year}年年度报告", f"{year}年年度报告全文", f"{year}年年度报告正文"}:
            score += 5
        if "修订" in t or "更新" in t:
            score += 2
        if "全文" in t or "正文" in t:
            score += 1
        candidates.append((score, int(a.get("announcementTime") or 0), a, t))
    if not candidates:
        raise LookupError(f"annual report not found: {code} {year}; announcements={len(anns)}")
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    a = candidates[0][2]
    t = candidates[0][3]
    url = STATIC_BASE + (a.get("adjunctUrl") or "").lstrip("/")
    return {"title": t, "url": url, "announcement_time": a.get("announcementTime")}


def parse_report_pdf(pdf_bytes: bytes, fiscal_year: int) -> dict:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts = []
    hit_pages = []
    for i in range(doc.page_count):
        txt = doc.load_page(i).get_text("text") or ""
        page_texts.append(txt)
        if any(k in txt for k in IR_KEYWORDS):
            hit_pages.append(i)

    # Add neighboring pages because tables frequently spill over page boundaries.
    selected = sorted({j for i in hit_pages for j in (i - 1, i, i + 1) if 0 <= j < len(page_texts)})
    selected_text = "\n".join(page_texts[j] for j in selected)
    flat = compact(selected_text)
    full_flat = compact("\n".join(page_texts))

    explicit_zero = any(re.search(p, full_flat) for p in ZERO_PATTERNS)
    rows = []

    # Work page by page to keep row context local. Look ahead from each date to infer method/object type.
    for j in selected:
        txt = page_texts[j]
        c = compact(txt)
        matches = list(DATE_RE.finditer(c))
        for idx, m in enumerate(matches):
            y, mo, d = int(m.group("y")), int(m.group("m")), int(m.group("d"))
            if y != fiscal_year:
                continue
            try:
                dt = pd.Timestamp(year=y, month=mo, day=d)
            except Exception:
                continue
            nxt = matches[idx + 1].start() if idx + 1 < len(matches) else min(len(c), m.end() + 260)
            ctx = c[m.end(): min(nxt, m.end() + 260)]
            method_m = METHOD_RE.search(ctx)
            obj_m = OBJ_RE.search(ctx)
            method = method_m.group(0) if method_m else ""
            obj = obj_m.group(0) if obj_m else ""

            # Only accept dates inside an investor-relations context. Strongest case is explicit object type.
            local_before = c[max(0, m.start() - 220):m.start()]
            ir_context = any(k in local_before + ctx for k in ("接待", "调研", "投资者关系", "沟通", "采访"))
            if not ir_context and not obj:
                continue
            rows.append({
                "visit_date": dt.strftime("%Y-%m-%d"),
                "method": method,
                "object_type": obj,
                "page": j + 1,
                "context": (local_before[-120:] + c[m.start():min(len(c), m.end()+220)])[:420],
            })

    # Deduplicate exact extraction duplicates, but preserve same-day duplicate events when contexts differ materially.
    seen = set()
    dedup = []
    for r in rows:
        key = (r["visit_date"], r["method"], r["object_type"], r["page"], r["context"][:180])
        if key not in seen:
            seen.add(key)
            dedup.append(r)

    institutional = [r for r in dedup if r["object_type"] == "机构"]
    return {
        "pages": doc.page_count,
        "hit_pages": [x + 1 for x in hit_pages],
        "selected_pages": [x + 1 for x in selected],
        "explicit_zero": bool(explicit_zero),
        "all_rows": dedup,
        "institutional_rows": institutional,
        "selected_text_chars": len(selected_text),
    }


def process_code_year(code: str, exchange: str, year: int) -> tuple[dict, list[dict]]:
    base = {"firm_code": code, "exchange": exchange, "fiscal_year": year}
    try:
        rep = query_annual_report(code, exchange, year)
        b = request_bytes(rep["url"])
        parsed = parse_report_pdf(b, year)
        rows = []
        for r in parsed["institutional_rows"]:
            rows.append({**base, **r, "report_title": rep["title"], "report_url": rep["url"]})
        # Complete-year status requires either explicit zero OR an identifiable IR section/table.
        # When institutional rows exist, the report is usable by construction.
        ir_section_present = bool(parsed["hit_pages"])
        complete = bool(parsed["explicit_zero"] or ir_section_present)
        status = {
            **base,
            "report_found": True,
            "report_title": rep["title"],
            "report_url": rep["url"],
            "pdf_bytes": len(b),
            "pages": parsed["pages"],
            "ir_hit_pages": ";".join(map(str, parsed["hit_pages"])),
            "explicit_zero": parsed["explicit_zero"],
            "n_institution_rows": len(rows),
            "n_all_candidate_rows": len(parsed["all_rows"]),
            "year_usable": complete,
            "error": "",
        }
        return status, rows
    except Exception as e:
        return {**base, "report_found": False, "report_title": "", "report_url": "", "pdf_bytes": 0,
                "pages": 0, "ir_hit_pages": "", "explicit_zero": False, "n_institution_rows": 0,
                "n_all_candidate_rows": 0, "year_usable": False, "error": repr(e)}, []


def main() -> None:
    df = pd.read_csv(SAMPLE, dtype={"firm_code": str})
    df["firm_code"] = df["firm_code"].str.zfill(6)
    for c in ["response_date", "pre_start", "pre_end", "post_start", "post_end"]:
        df[c] = pd.to_datetime(df[c])

    needed = set()
    for _, r in df.iterrows():
        years = range(r.pre_start.year, r.post_end.year + 1)
        for y in years:
            needed.add((r.firm_code, r.exchange, int(y)))

    statuses, visits = [], []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(process_code_year, *x): x for x in sorted(needed)}
        for fut in as_completed(futs):
            x = futs[fut]
            try:
                st, vs = fut.result()
            except Exception as e:
                st = {"firm_code": x[0], "exchange": x[1], "fiscal_year": x[2], "report_found": False,
                      "year_usable": False, "error": repr(e)}
                vs = []
            statuses.append(st)
            visits.extend(vs)
            print("REPORT", st.get("firm_code"), st.get("fiscal_year"), "usable", st.get("year_usable"),
                  "inst", st.get("n_institution_rows"), "zero", st.get("explicit_zero"), "err", st.get("error"))

    st_df = pd.DataFrame(statuses).sort_values(["firm_code", "fiscal_year"])
    v_df = pd.DataFrame(visits)
    if not v_df.empty:
        v_df["visit_date"] = pd.to_datetime(v_df["visit_date"])
        v_df = v_df.sort_values(["firm_code", "visit_date", "page"])

    status_map = {(str(r.firm_code).zfill(6), int(r.fiscal_year)): bool(r.year_usable) for _, r in st_df.iterrows()}
    event_rows = []
    for _, r in df.iterrows():
        code = r.firm_code
        years_needed = list(range(r.pre_start.year, r.post_end.year + 1))
        years_ok = {y: status_map.get((code, y), False) for y in years_needed}
        usable = all(years_ok.values())
        if v_df.empty:
            firmv = pd.DataFrame(columns=["visit_date"])
        else:
            firmv = v_df[v_df["firm_code"] == code]
        pre = firmv[(firmv["visit_date"] >= r.pre_start) & (firmv["visit_date"] <= r.pre_end)] if usable else firmv.iloc[0:0]
        post = firmv[(firmv["visit_date"] >= r.post_start) & (firmv["visit_date"] <= r.post_end)] if usable else firmv.iloc[0:0]
        event_rows.append({
            "event_id": r.event_id,
            "firm_code": code,
            "firm_name": r.firm_name,
            "exchange": r.exchange,
            "response_date": r.response_date.strftime("%Y-%m-%d"),
            "rri_q": int(r.rri_q),
            "period": r.period,
            "event_type": r.event_type,
            "pre_start": r.pre_start.strftime("%Y-%m-%d"),
            "pre_end": r.pre_end.strftime("%Y-%m-%d"),
            "post_start": r.post_start.strftime("%Y-%m-%d"),
            "post_end": r.post_end.strftime("%Y-%m-%d"),
            "years_needed": ";".join(map(str, years_needed)),
            "year_status": ";".join(f"{y}:{'OK' if years_ok[y] else 'MISS'}" for y in years_needed),
            "report_based_usable": usable,
            "visits_pre": int(len(pre)) if usable else math.nan,
            "visits_post": int(len(post)) if usable else math.nan,
            "any_pre": bool(len(pre)) if usable else False,
            "any_post": bool(len(post)) if usable else False,
        })

    ev = pd.DataFrame(event_rows)
    usable = ev[ev.report_based_usable]
    by_period = ev.groupby("period")["report_based_usable"].agg(["sum", "count"]).reset_index().to_dict("records")
    by_exchange = ev.groupby("exchange")["report_based_usable"].agg(["sum", "count"]).reset_index().to_dict("records")
    usable_n = int(ev.report_based_usable.sum())
    variation_n = int(((usable.visits_pre.fillna(0) > 0) | (usable.visits_post.fillna(0) > 0)).sum()) if usable_n else 0
    both_nonzero = int(((usable.visits_pre.fillna(0) > 0) & (usable.visits_post.fillna(0) > 0)).sum()) if usable_n else 0

    coverage_gate = (
        usable_n >= 27
        and all(int(x["sum"]) >= 8 for x in by_period)
        and all(int(x["sum"]) >= 13 for x in by_exchange)
    )
    variation_gate = variation_n >= 8

    summary = {
        "pilot_n": int(len(ev)),
        "unique_code_year_reports_needed": int(len(needed)),
        "report_years_usable": int(st_df.year_usable.fillna(False).sum()),
        "report_years_total": int(len(st_df)),
        "event_usable_n": usable_n,
        "event_usable_rate": usable_n / len(ev),
        "events_any_activity_either_window": variation_n,
        "events_activity_both_windows": both_nonzero,
        "total_institutional_visits_pre": int(usable.visits_pre.fillna(0).sum()) if usable_n else 0,
        "total_institutional_visits_post": int(usable.visits_post.fillna(0).sum()) if usable_n else 0,
        "median_visits_pre": float(usable.visits_pre.median()) if usable_n else None,
        "median_visits_post": float(usable.visits_post.median()) if usable_n else None,
        "by_period": by_period,
        "by_exchange": by_exchange,
        "coverage_gate_rule": "PASS if usable >=27/30, each period >=8/10, each exchange >=13/15",
        "coverage_gate": "PASS" if coverage_gate else "FAIL",
        "variation_gate_rule": "PASS if >=8 usable events have nonzero institutional visits in PRE or POST",
        "variation_gate": "PASS" if variation_gate else "FAIL",
        "note": "No RRI coefficient is estimated in this audit. Annual reports are used retrospectively as the source of complete-year investor-relations activity tables; explicit no-activity statements are valid zeros, missing/unparseable reports are missing.",
    }

    st_df.to_csv(OUT / "01_REPORT_YEAR_STATUS.csv", index=False, encoding="utf-8-sig")
    if v_df.empty:
        pd.DataFrame(columns=["firm_code","exchange","fiscal_year","visit_date","method","object_type","page","context","report_title","report_url"]).to_csv(OUT / "02_INSTITUTION_VISITS.csv", index=False, encoding="utf-8-sig")
    else:
        v_df.to_csv(OUT / "02_INSTITUTION_VISITS.csv", index=False, encoding="utf-8-sig")
    ev.to_csv(OUT / "03_EVENT_COVERAGE.csv", index=False, encoding="utf-8-sig")
    (OUT / "04_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# Report-based Institutional Visit Coverage Audit",
        "",
        f"- Coverage gate: **{summary['coverage_gate']}**",
        f"- Variation gate: **{summary['variation_gate']}**",
        f"- Event usable: {usable_n}/30 ({usable_n/30:.1%})",
        f"- Unique firm-year annual reports required: {len(needed)}",
        f"- Usable report-years: {summary['report_years_usable']}/{summary['report_years_total']}",
        f"- Events with any PRE/POST institutional activity: {variation_n}",
        f"- Events with activity in both windows: {both_nonzero}",
        f"- Total institutional visits PRE / POST: {summary['total_institutional_visits_pre']} / {summary['total_institutional_visits_post']}",
        "",
        "No RRI regression was opened in this audit.",
    ]
    (OUT / "05_COVERAGE_GATE.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(ev[["event_id","firm_code","firm_name","period","exchange","report_based_usable","visits_pre","visits_post","year_status"]].to_string(index=False))


if __name__ == "__main__":
    main()
