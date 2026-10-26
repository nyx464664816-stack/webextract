"""Compute every number from the raw results. python analyze.py -> results/summary.json and RESULTS.md
   Rules: one result per (url, endpoint, rep) = the first attempt that was not an HTTP 429 pacing wait. Success = HTTP 200 and non-empty markdown.
   Latency (ms) = successful runs only. Percentile = nearest rank. Completeness = checks passed / checks that apply (see `checks` below)."""
import json, re, statistics, collections
from common import *
gt = json.load(open(RES / "ground_truth.json"))
alnum = lambda s: re.sub(r"[^0-9a-z]", "", str(s or "").lower())
def checks(ep, d, g):
    md = alnum(d.get("markdown")); c = {}
    if g.get("h1"): c["h1_in_markdown"] = alnum(g["h1"]) in md
    if g.get("p_longest"): c["longest_paragraph_in_markdown"] = alnum(g["p_longest"]) in md
    for i, t in enumerate(g["tables"]): c[f"table{i}_cells_in_markdown"] = all(alnum(x) in md for x in t["cells"])
    if ep == "extract":
        if g.get("title"): c["metadata_title"] = norm((d.get("metadata") or {}).get("title")) == g["title"]
        c["tables_count"] = len(d.get("tables") or []) == len(g["tables"])
        c["tables_row_counts"] = [len(t.get("rows", [])) for t in d.get("tables") or []] == [t["rows"] for t in g["tables"]]
        if g.get("product_name"):
            p = d.get("product") or {}; c["product_name"] = alnum(p.get("name")) == alnum(g["product_name"]); c["product_price"] = p.get("price") == g["price"]
    return c
def stats(ms):
    return {"n": len(ms), "median_ms": round(statistics.median(ms)), "p95_ms": pct(ms, 95), "min_ms": min(ms), "max_ms": max(ms)} if ms else {"n": 0}
rows = {}
for line in open(RES / "sandbox_runs.jsonl"):
    r = json.loads(line)
    if r.get("pacing") or r.get("status") == 429: continue
    rows.setdefault((r["id"], r["endpoint"], r["rep"]), r)
out = {"generated": now(), "sandbox": {}, "per_url": {}}
for ep in ("markdown", "extract"):
    rs = [r for k, r in rows.items() if k[1] == ep]; ok_ms = []; passed = total = 0; fails = []; full = 0
    for r in rs:
        f = RAW / "sandbox" / f"{r['id']}.{ep}.{r['rep']}.json"; ok = False
        if r["status"] == 200 and f.exists():
            d = json.load(open(f)); ok = bool((d.get("markdown") or "").strip())
            if ok:
                ok_ms.append(r["ms"]); c = checks(ep, d, gt[r["id"]]); passed += sum(c.values()); total += len(c); full += all(c.values())
                for k, v in c.items():
                    if not v: fails.append(f"{r['id']}:{k}")
        if not ok: fails.append(f"{r['id']}:HTTP {r['status']} {r.get('error') or ''} {(r.get('body_head') or '')[:70]}")
    out["sandbox"][ep] = {"runs": len(rs), "success": len(ok_ms), "success_rate": round(len(ok_ms) / len(rs), 4) if rs else None, **stats(ok_ms),
        "checks_passed": passed, "checks_total": total, "completeness": round(passed / total, 4) if total else None, "runs_with_all_checks_passing": full, "problems": sorted(collections.Counter(fails).items())}
    for u in URLS:
        us = [r for k, r in rows.items() if k[0] == u["id"] and k[1] == ep]; ms = [r["ms"] for r in us if r["status"] == 200]
        out["per_url"].setdefault(u["id"], {})[ep] = {"runs": len(us), "ok": len(ms), **stats(ms)}
for name in ("quotes", "failures", "live_free"):
    try: out[name] = json.load(open(RES / f"{name}.json"))
    except FileNotFoundError: pass
if "quotes" in out:
    q = out["quotes"]; out["quotes_summary"] = {ep: stats([x["ms"] for x in q if x["endpoint"] == ep and x["status"] == 402]) | {"statuses": sorted({x["status"] for x in q if x["endpoint"] == ep})} for ep in ("markdown", "extract")}
json.dump(out, open(RES / "summary.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k in ("sandbox", "quotes_summary")}, indent=1, ensure_ascii=False))
# ---- live free-path sample vs sandbox (appended) ----
lf = out.get("live_free")
if lf:
    cmp = []; lms = {"markdown": [], "extract": []}
    for r in lf:
        if r["status"] != 200: continue
        ep = r["endpoint"]; d = json.load(open(RAW / "live" / f"{r['id']}.{ep}.json")); c = checks(ep, d, gt[r["id"]]); lms[ep].append(r["ms"])
        sb = RAW / "sandbox" / f"{r['id']}.{ep}.1.json"; same = None
        if sb.exists():
            s = json.load(open(sb)); same = {"markdown_identical": s.get("markdown") == d.get("markdown")}
            if ep == "extract":
                strip = lambda x: {k: v for k, v in x.items() if k not in ("fetched_at", "latency_ms", "request_id")}
                same["json_identical_except_fetched_at"] = strip(s) == strip(d)
        cmp.append({"id": r["id"], "endpoint": ep, "checks_passed": sum(c.values()), "checks_total": len(c), **(same or {})})
    out["live_free_summary"] = {"calls": len(lf), "ok_200": sum(r["status"] == 200 for r in lf), "statuses": dict(collections.Counter(r["status"] for r in lf)),
        "latency": {ep: stats(v) for ep, v in lms.items()}, "per_call": cmp}
    json.dump(out, open(RES / "summary.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out["live_free_summary"], indent=1, ensure_ascii=False))
