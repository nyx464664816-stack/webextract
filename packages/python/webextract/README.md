# webextract-sdk (Python)

Thin client for the [WebExtract](https://webextract.dev) API: a public web page in, clean Markdown plus fixed-schema JSON out (article metadata, product and price, tables). It's built for AI agents.

```bash
pip install webextract-sdk            # core (httpx only)
pip install "webextract-sdk[x402]"    # + the official x402 SDK, for pay-per-call
```

The PyPI name is `webextract-sdk`; the import name is `webextract` (`from webextract import WebExtract`).

## Billing: pick one

| Mode | How | Cost |
|---|---|---|
| Free tier (default) | `WebExtract()` sends `X-Billing: free` (when `WEBEXTRACT_API_KEY` is not set) | 20 calls/day per IP (shared with MCP) |
| Prepaid credits | `WebExtract(api_key="lx_...")` or env `WEBEXTRACT_API_KEY` → `Authorization: Bearer` | `/v1/extract` 1 credit, `/v1/markdown` 0.4 credit. Buy at https://webextract.dev/#pricing |
| x402 pay per call | `AsyncWebExtract(payment_client=x402HttpxClient(...))` | `/v1/extract` $0.005, `/v1/markdown` $0.002 in USDC on Base and 6 other chains |
| x402 sandbox | add `billing="x402-testnet"` | Base Sepolia **test** USDC only. Nothing real is charged |

**This package never handles private keys.** With x402, signing happens inside the client you build with the official `x402` SDK.

```python
from webextract import WebExtract, PaymentRequiredError, TargetFetchError

with WebExtract() as we:                      # free tier
    r = we.extract("https://web-scraping.dev/product/1")
    print(r.data["product"], r.meta.free_remaining)
```

### x402 (async, official SDK)

```python
import asyncio, os
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm.exact import ExactEvmScheme
from webextract import AsyncWebExtract

async def main():
    signer = Account.from_key(os.environ["X402_PRIVATE_KEY"])    # your key, your process
    xc = x402Client(); xc.register("eip155:8453", ExactEvmScheme(signer=signer))
    async with x402HttpxClient(xc, timeout=60) as pay:
        we = AsyncWebExtract(payment_client=pay)                 # billing="x402"
        r = await we.markdown("https://example.com")
        print(r.meta.payment_response)                           # settlement receipt (tx hash)
asyncio.run(main())
```

**`WEBEXTRACT_API_KEY`**: if `api_key` isn't passed, the client reads this environment variable. An explicit `api_key` always wins. The variable is ignored when `payment_client` is given or `billing` is anything other than `"key"`, so it never causes the "api_key + payment_client" error.

**`settlement_retries`** (default `1`): a 402 `settlement_failed` (payment verified, not settled, **not charged**) is retried once, and the payment client signs a fresh payment. Other errors are never retried.

For a sync client, pass the `requests.Session` from `x402.http.clients.x402_requests(xc)` as `payment_client=`. The x402 SDK has no sync httpx client.

## Errors

Every error is a `WebExtractError` with `status`, `code`, `message`, `charged`, `retryable`, `body`.

| Class | When | Notes |
|---|---|---|
| `PaymentRequiredError` | HTTP 402 | `.reason` is one of `x402_required`, `x402_requested`, `free_limit_reached`, `invalid_payment`, `unsupported_network`, `settlement_failed` (retryable), `no_credits`. Also has `.networks`, `.payment_required` (decoded header), `.buy_url`, `.free_remaining`, `.hint` |
| `TargetFetchError` | target page failed: `upstream_error`, `blocked_by_site` (422), `robots_disallowed` (451), `dns_failed`, `fetch_failed`, `too_large`, `unsupported_type` | never charged |
| `InvalidRequestError` | 400 (`missing_url`, `invalid_url`, `forbidden_host`, ...) or client-side URL check | never charged |
| `AuthenticationError` | 401 `invalid_api_key` | |
| `RateLimitError` | 429 (sandbox limits) | `.retry_after` |
| `ConnectionError` | no response: network error, timeout, or the payment client raised | `code` is `timeout` or `connection_error` |

## Response fields

The responses are the API JSON as-is (`schema_version` "1.0"). Fields added on 2026-10-21 (`content_source`, `product.price_detail`, `product_unresolved`) may be missing on older deployments, so read them with `.get()`. A missing price is never reported as `0`. `price_detail.unresolved.reason` says why it's missing.

License: MIT © TAINCHENG, L.L.C.
