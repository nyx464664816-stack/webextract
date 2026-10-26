"""Base Sepolia sandbox runs (test USDC, no free-tier quota): REPS calls per URL per endpoint, sequential, 7 s apart.
   env: X402_TESTNET_PRIVATE_KEY (TESTNET key only; only eip155:84532 is registered, so nothing else can be signed)
   python run_sandbox.py [REPS=5]  -> results/sandbox_runs.jsonl + results/raw/sandbox/<id>.<endpoint>.<rep>.json
   Timing = wall clock of the whole client call: unpaid request -> 402 -> sign -> paid request (includes the extraction and testnet settlement)."""
import asyncio, json, os, sys, time
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.http.utils import decode_payment_response_header
from x402.mechanisms.evm.exact import ExactEvmScheme
from common import *
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
(RAW / "sandbox").mkdir(parents=True, exist_ok=True)
account = Account.from_key(os.environ["X402_TESTNET_PRIVATE_KEY"])
async def main():
    c = x402Client(); c.register("eip155:84532", ExactEvmScheme(signer=account))
    log = open(RES / "sandbox_runs.jsonl", "a")
    async with x402HttpxClient(c, timeout=120, headers={"User-Agent": UA}) as http:
        for rep in range(1, REPS + 1):
            for u in URLS:
                for ep in ("markdown", "extract"):
                    f = RAW / "sandbox" / f"{u['id']}.{ep}.{rep}.json"
                    if f.exists(): continue
                    for attempt in range(1, 5):   # only HTTP 429 (sandbox limit 20 requests/minute, 300/day per IP; each call = 2 requests) is retried, after waiting
                        t0 = time.perf_counter()
                        try:
                            r = await http.get(f"{BASE}/sandbox/v1/{ep}", params={"url": u["url"]}); await r.aread(); err = None
                        except Exception as e: r = None; err = f"{type(e).__name__}: {str(e)[:120]}"
                        ms = round((time.perf_counter() - t0) * 1000)
                        if r is not None and r.status_code == 429:
                            log.write(json.dumps({"ts": now(), "id": u["id"], "endpoint": ep, "rep": rep, "status": 429, "pacing": True}) + "\n"); log.flush()
                            print("429, waiting 65 s"); await asyncio.sleep(65); continue
                        break
                    row = {"ts": now(), "id": u["id"], "endpoint": ep, "rep": rep, "ms": ms, "status": r.status_code if r else None, "error": err}
                    if r is not None:
                        pr = decode_payment_response_header(r.headers["payment-response"]) if r.headers.get("payment-response") else None
                        row["settled"] = bool(pr and pr.success); row["bytes"] = len(r.content)
                        if r.status_code == 200: f.write_text(json.dumps(r.json(), ensure_ascii=False))
                        else: row["body_head"] = r.text[:200]
                    log.write(json.dumps(row) + "\n"); log.flush(); print(row["id"], ep, rep, row["status"], ms, "ms", row.get("settled"), err or "")
                    await asyncio.sleep(7)   # 2 requests per call, keep under 20/minute
asyncio.run(main())
