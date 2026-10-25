"""Pay per call with x402 (no account, no key) — Base Sepolia TESTNET sandbox: /sandbox/v1/markdown ($0.002) and /sandbox/v1/extract ($0.005) test USDC.

    pip install "x402[evm,httpx]==2.25.0"
    export X402_TESTNET_PRIVATE_KEY=0x...    # a throwaway TESTNET key; get test USDC at https://faucet.circle.com (Base Sepolia)
    python x402_client.py [page-url]

The production endpoints (/v1/markdown, /v1/extract) use the same flow with real USDC on 7 chains; this script refuses mainnet networks.
WEBEXTRACT_UA labels your traffic."""
import asyncio, json, os, sys
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.http.utils import decode_payment_response_header
from x402.mechanisms.evm.exact import ExactEvmScheme

BASE = os.environ.get("WEBEXTRACT_BASE", "https://api.webextract.dev")
PAGE = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
key = os.environ.get("X402_TESTNET_PRIVATE_KEY") or sys.exit("set X402_TESTNET_PRIVATE_KEY (testnet key only)")
account = Account.from_key(key); short = lambda a: a[:6] + "…" + a[-4:]

async def main() -> None:
    client = x402Client(); client.register("eip155:84532", ExactEvmScheme(signer=account))   # only Base Sepolia is registered: nothing else can be signed
    print("payer:", short(account.address), "network: eip155:84532 (Base Sepolia test USDC)")
    kw = {"headers": {"User-Agent": os.environ["WEBEXTRACT_UA"]}} if os.environ.get("WEBEXTRACT_UA") else {}
    async with x402HttpxClient(client, timeout=90, **kw) as http:
        for path in ("markdown", "extract"):
            r = await http.get(f"{BASE}/sandbox/v1/{path}", params={"url": PAGE}); await r.aread()
            pr = decode_payment_response_header(r.headers["payment-response"]) if r.headers.get("payment-response") else None
            print(f"\n--- /sandbox/v1/{path}: HTTP {r.status_code}; settled={pr.success if pr else None} tx={(pr.transaction[:12] + '…') if pr else None} ---")
            if r.status_code != 200: print(r.text[:300]); continue
            d = r.json(); p = d.get("product") or {}
            print(d["markdown"][:200].replace("\n", " ") + "…" if path == "markdown" else json.dumps({k: p.get(k) for k in ("name", "price", "currency", "availability")}, ensure_ascii=False))

asyncio.run(main())
