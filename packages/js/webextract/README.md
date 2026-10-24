# @webextract/sdk

Thin, dependency-free client for the [WebExtract](https://webextract.dev) API: a public web page in, clean Markdown plus fixed-schema JSON out (article metadata, product and price, tables). It's built for AI agents. ESM with TypeScript types. Needs Node ≥ 20.3, Bun, Deno or edge runtimes.

```bash
npm i @webextract/sdk
```

```ts
import { WebExtract, PaymentRequiredError, TargetFetchError } from "@webextract/sdk";

const we = new WebExtract();                       // free tier: X-Billing: free, 20 calls/day per IP
const { data, meta } = await we.extract("https://web-scraping.dev/product/1");
console.log(data.product?.price_detail, meta.freeRemaining);
```

## Billing: pick one

| Mode | Option | Cost |
|---|---|---|
| Free tier (default) | nothing (and no `WEBEXTRACT_API_KEY` set), or `billing: "free"` | 20 calls/day per IP (shared with MCP) |
| Prepaid credits | `apiKey: "lx_..."` or env `WEBEXTRACT_API_KEY` → `Authorization: Bearer` | `/v1/extract` 1 credit, `/v1/markdown` 0.4 credit. Buy at https://webextract.dev/#pricing |
| x402 pay per call | `paymentFetch` (default billing `"x402"`) | `/v1/extract` $0.005, `/v1/markdown` $0.002 in USDC on Base and 6 other chains |
| x402 sandbox | `paymentFetch` + `billing: "x402-testnet"` | Base Sepolia **test** USDC only. Nothing real is charged |

**This package never handles private keys.** You pass an x402-capable `fetch`, and signing happens inside it:

```ts
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { WebExtract } from "@webextract/sdk";

const account = privateKeyToAccount(process.env.X402_PRIVATE_KEY as `0x${string}`);
const paymentFetch = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }], // only the networks you allow
});
const we = new WebExtract({ paymentFetch });
const r = await we.markdown("https://example.com");
console.log(r.meta.paymentResponse); // { success, transaction, network, payer }
```

**`WEBEXTRACT_API_KEY`**: if you don't pass `apiKey`, the client reads this environment variable (where `process.env` exists). An explicit `apiKey` always wins. The variable is ignored when you pass `paymentFetch` or set `billing` to anything other than `"key"`, so it never causes the "apiKey + paymentFetch" error.

**`settlementRetries`** (default `1`): when the API answers 402 `settlement_failed` (payment verified, not settled, **not charged**), the request is sent once more and your `paymentFetch` signs a fresh payment. Other errors are never retried. Set it to `0` to turn this off.

`billing: "free"` together with `paymentFetch` gives you free-first: it uses the free tier until the daily limit, after which the wrapper pays for the 402.

## Errors

Every error is a `WebExtractError` with `status`, `code`, `message`, `charged`, `retryable`, `body` and `toJSON()`.

| Class | When | Notes |
|---|---|---|
| `PaymentRequiredError` | HTTP 402 | `reason` is one of `x402_required`, `x402_requested`, `free_limit_reached`, `invalid_payment`, `unsupported_network`, `settlement_failed` (retryable), `no_credits`. Also has `networks`, `paymentRequired` (decoded header), `buyUrl`, `freeRemaining`, `hint` |
| `TargetFetchError` | target page failed: `upstream_error`, `blocked_by_site` (422), `robots_disallowed` (451), `dns_failed`, `fetch_failed`, `too_large`, `unsupported_type` | never charged |
| `InvalidRequestError` | 400, or the client-side URL check | never charged |
| `AuthenticationError` | 401 `invalid_api_key` | |
| `RateLimitError` | 429 | `retryAfter` |
| `ConnectionError` | no response: network, timeout, or `paymentFetch` threw (e.g. no matching network) | `code` is `timeout` or `connection_error` |

## Response fields

The responses are the API JSON as-is (`schema_version` "1.0"). Fields added on 2026-10-21 (`content_source`, `product.price_detail`, `product_unresolved`) are typed as optional. A missing price is never reported as `0`. `price_detail.unresolved.reason` says why it's missing.

Also `balance()`: credits for your key, or free calls left today. It's never charged.

Tools for agents: [`@webextract/ai-sdk`](https://www.npmjs.com/package/@webextract/ai-sdk) (Vercel AI SDK) and [`@webextract/langchain`](https://www.npmjs.com/package/@webextract/langchain) (LangChain.js). The MCP server is at `https://api.webextract.dev/mcp`.

License: MIT © TAINCHENG, L.L.C.
