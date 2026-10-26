"""Unpaid requests to the LIVE paid endpoints: HTTP status, response time and the x402 price quote. No payment, no free-tier call used
   (no X-Billing: free header). python run_quotes.py [REPS=5] -> results/quotes.json"""
import base64, json, sys, time, requests
from common import *
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
URL = "https://example.com/"; out = []
for ep in ("markdown", "extract"):
    for rep in range(REPS):
        t0 = time.perf_counter(); r = requests.get(f"{BASE}/v1/{ep}", params={"url": URL}, headers={"User-Agent": UA}, timeout=30); ms = round((time.perf_counter() - t0) * 1000)
        row = {"endpoint": ep, "rep": rep + 1, "status": r.status_code, "ms": ms}
        h = r.headers.get("payment-required")
        if h:
            pr = json.loads(base64.b64decode(h)); row["x402Version"] = pr.get("x402Version"); row["options"] = [{"network": a["network"], "amount_atomic": a["amount"], "scheme": a["scheme"]} for a in pr["accepts"]]
        out.append(row); print(row["endpoint"], row["status"], ms, "ms", len(row.get("options", [])), "options"); time.sleep(1)
json.dump(out, open(RES / "quotes.json", "w"), indent=1)
