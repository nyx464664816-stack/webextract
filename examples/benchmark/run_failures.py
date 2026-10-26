"""Does a FAILED fetch cost money? Base Sepolia sandbox, test USDC. For each bad URL and endpoint: pay when asked, record the HTTP result and
   whether a settlement is reported; compare the wallet's on-chain test-USDC balance before and after all failure cases, then run one
   successful control call to show the balance check can see a charge.   python run_failures.py -> results/failures.json
   env: X402_TESTNET_PRIVATE_KEY (testnet only)"""
import asyncio, json, os, time, requests
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.http.utils import decode_payment_response_header
from x402.mechanisms.evm.exact import ExactEvmScheme
from common import *
USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"; RPC = "https://sepolia.base.org"
account = Account.from_key(os.environ["X402_TESTNET_PRIVATE_KEY"])
def balance():
    data = "0x70a08231" + account.address[2:].lower().rjust(64, "0")
    return int(requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": USDC, "data": data}, "latest"]}, timeout=20).json()["result"], 16)
CASES = [("http-404", "https://books.toscrape.com/catalogue/this-page-does-not-exist_0/index.html"),
         ("dns-failure", "https://no-such-host.webextract-benchmark.invalid/"),
         ("not-html-png", "https://httpbin.org/image/png"),
         ("private-127.0.0.1", "http://127.0.0.1/"),
         ("private-10.0.0.1", "http://10.0.0.1/")]
async def call(http, ep, url):
    t0 = time.perf_counter(); r = await http.get(f"{BASE}/sandbox/v1/{ep}", params={"url": url}); await r.aread()
    pr = decode_payment_response_header(r.headers["payment-response"]) if r.headers.get("payment-response") else None
    try: body = r.json()
    except Exception: body = {}
    return {"status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000), "settlement_reported": bool(pr and pr.success), "error": body.get("error"), "message": (body.get("message") or "")[:160]}
async def main():
    c = x402Client(); c.register("eip155:84532", ExactEvmScheme(signer=account)); res = {"cases": []}
    b0 = balance(); res["balance_before_atomic"] = b0
    async with x402HttpxClient(c, timeout=120, headers={"User-Agent": UA}) as http:
        for name, url in CASES:
            for ep in ("markdown", "extract"):
                row = {"case": name, "url": url, "endpoint": ep, **await call(http, ep, url)}; res["cases"].append(row); print(row); await asyncio.sleep(7)
        time.sleep(15); b1 = balance(); res["balance_after_failures_atomic"] = b1
        res["control"] = {"url": "https://example.com/", "endpoint": "markdown", **await call(http, "markdown", "https://example.com/")}
    time.sleep(20); b2 = balance(); res["balance_after_control_atomic"] = b2
    res["failures_charged_atomic"] = b0 - b1; res["control_charged_atomic"] = b1 - b2; print({k: v for k, v in res.items() if k != "cases"})
    json.dump(res, open(RES / "failures.json", "w"), indent=1)
asyncio.run(main())
