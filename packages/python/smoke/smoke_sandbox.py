"""Real call (Python): x402 SANDBOX payment with Base Sepolia TEST USDC through the official x402 SDK.
Run with examples/python-x402/.venv (has x402 2.25). Only eip155:84532 is registered. Key never printed."""
import asyncio
import datetime
import os
import stat
import sys

from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm.exact import ExactEvmScheme

import webextract as we

ENV = os.path.join(os.path.dirname(__file__), "..", "..", "..", "examples", "python-x402", ".env")
if os.stat(ENV).st_mode & 0o077:
    sys.exit(".env must be mode 600")
key = next(l.split("=", 1)[1].strip() for l in open(ENV) if l.startswith("X402_TESTNET_PRIVATE_KEY="))
NET = "eip155:84532"


async def main():
    acct = Account.from_key(key)
    print(datetime.datetime.now(datetime.timezone.utc).isoformat(), "payer", acct.address, "network", NET)
    xc = x402Client()
    xc.register(NET, ExactEvmScheme(signer=acct))
    async with x402HttpxClient(xc, timeout=60) as pay:
        c = we.AsyncWebExtract(payment_client=pay, billing="x402-testnet")
        try:
            r = await c.markdown(sys.argv[1] if len(sys.argv) > 1 else "https://example.com")
        except we.WebExtractError as e:
            print("ERROR", type(e).__name__, e.status, e.code, getattr(e, "reason", ""), e.message)
            sys.exit(1)
    print("HTTP", r.meta.status, "sandbox", r.meta.sandbox, "billing", r.meta.billing)
    print("settlement", r.meta.payment_response)
    print("title", r.data.get("title"), "| words", r.data.get("word_count"), "| content_source", r.data.get("content_source", "(absent)"))

asyncio.run(main())
