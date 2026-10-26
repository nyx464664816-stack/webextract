"""Small sample on the LIVE free path (20 calls/IP/day): at most 14 calls, stops at the first HTTP 402 (free quota gone) or any non-200.
   Header X-Billing: free. Used to check that live output equals sandbox output and to record live latency.   python run_live_free.py"""
import json, sys, time, requests
from common import *
IDS = ["example", "books-home", "books-product", "quotes", "wsio-tables", "sts-forms", "httpbin-html"]
(RAW / "live").mkdir(parents=True, exist_ok=True); rows = []; n = 0
for u in [x for x in URLS if x["id"] in IDS]:
    for ep in ("markdown", "extract"):
        if n >= 14: break
        t0 = time.perf_counter(); r = requests.get(f"{BASE}/v1/{ep}", params={"url": u["url"]}, headers={"User-Agent": UA, "X-Billing": "free"}, timeout=90); ms = round((time.perf_counter() - t0) * 1000); n += 1
        row = {"ts": now(), "id": u["id"], "endpoint": ep, "status": r.status_code, "ms": ms, "free_remaining": r.headers.get("x-free-remaining")}
        if r.status_code == 200: (RAW / "live" / f"{u['id']}.{ep}.json").write_text(json.dumps(r.json(), ensure_ascii=False))
        rows.append(row); print(row)
        json.dump(rows, open(RES / "live_free.json", "w"), indent=1)
        if r.status_code != 200: sys.exit("stopped: HTTP %s" % r.status_code)
        time.sleep(3)
