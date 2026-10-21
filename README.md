<p align="center"><img src="logo.svg" width="64" alt="WebExtract"></p>

# WebExtract

**Web page → clean Markdown + fixed-schema JSON, for AI agents.** One GET request turns any public URL into LLM-ready Markdown plus structured data (article metadata, product/price, tables). Pay per call with **x402 (USDC on Base, Polygon, Arbitrum, Avalanche, OP Mainnet, World Chain or Monad)**, buy prepaid credits with a card (**Stripe**), or use it from any MCP client.

- Website: https://webextract.dev
- API base: `https://api.webextract.dev`
- MCP (streamable HTTP): `https://api.webextract.dev/mcp`
- OpenAPI: https://api.webextract.dev/openapi.json · `llms.txt`: https://api.webextract.dev/llms.txt
- Try a paid x402 call in your browser wallet: https://webextract.dev/try

## Endpoints

| Method | Path | Returns | x402 price | Credits |
| --- | --- | --- | --- | --- |
| GET | `/v1/extract?url=<page>` | Markdown + structured JSON (metadata, product/price, tables) | $0.005 | 1 |
| GET / POST | `/v1/markdown?url=<page>` | Markdown only | $0.002 | 0.4 |
| GET | `/v1/balance` | Free calls left today, or prepaid credits left | free | – |
| POST | `/mcp` | MCP tools `extract_url`, `page_markdown` | – | same as above |
| GET | `/.well-known/x402` | x402 discovery | free | – |

Behaviour:
- `robots.txt` is respected.
- **No charge on failed fetches** (404, timeout, blocked, robots disallowed, invalid URL).
- Structured JSON costs nothing extra. With a prepaid key, if structured fields come back empty you're charged the Markdown rate (0.4 credit). x402 payments settle at the quoted price.

## Pricing

- **Free:** 50 calls/day per IP, no key, no signup.
- **x402 pay-per-call:** $0.005 (`/v1/extract`) / $0.002 (`/v1/markdown`) in USDC on any supported network (below). No account, no gas needed.
- **Prepaid packs (card, via Stripe Checkout):** $5 = 1,000 credits · $20 = 5,000 credits · $50 = 15,000 credits. **Credits never expire.** Buy at https://webextract.dev/#pricing; the API key is shown once on the success page.

## Quick start

```sh
# Free tier
curl "https://api.webextract.dev/v1/markdown?url=https://example.com"

# Prepaid key (Stripe)
curl -H "Authorization: Bearer $WEBEXTRACT_KEY" \
  "https://api.webextract.dev/v1/extract?url=https://example.com"
```

Response (abridged):

```json
{
  "url": "https://example.com",
  "final_url": "https://example.com/",
  "title": "Example Domain",
  "markdown": "This domain is for use in documentation examples ...",
  "word_count": 17
}
```

Prepaid responses include `X-Credits-Charged` and `X-Credits-Remaining` headers; free-tier responses include `X-Free-Remaining`.

## Pay per call with x402

Requests without a key and without free calls left (or with `X-Billing: x402`) get **HTTP 402** with an x402 v2 `PAYMENT-REQUIRED` header (scheme `exact`). It lists one option per network; pay with whichever one your wallet holds USDC on:

| Network | CAIP-2 id | USDC (native) | EIP-712 name / version |
| --- | --- | --- | --- |
| Base (recommended) | `eip155:8453` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | USD Coin / 2 |
| Polygon PoS | `eip155:137` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | USD Coin / 2 |
| Arbitrum One | `eip155:42161` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | USD Coin / 2 |
| Avalanche C-Chain | `eip155:43114` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | USD Coin / 2 |
| OP Mainnet | `eip155:10` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | USD Coin / 2 |
| World Chain | `eip155:480` | `0x79A02482A880bCE3F13e09Da970dC34db4CD24d1` | USDC / 2 |
| Monad | `eip155:143` | `0x754704Bc059F8C67012fEd69BC8A327a5aafb603` | USDC / 2 |

Not supported: **USDC on Ethereum mainnet** (no x402 facilitator settles there). Solana is planned.

Any x402 client can pay and retry automatically:

```js
// npm i @x402/fetch @x402/evm viem
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.EVM_PRIVATE_KEY); // low-balance hot wallet
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  // register the network(s) where your wallet holds USDC, e.g. Base and Polygon
  schemes: [
    { network: "eip155:8453", client: new ExactEvmScheme(account) },
    { network: "eip155:137", client: new ExactEvmScheme(account) },
  ],
});

const res = await fetchWithPayment(
  "https://api.webextract.dev/v1/extract?url=" + encodeURIComponent("https://example.com"),
  { headers: { "X-Billing": "x402" } }
);
console.log(await res.json());
```

In a browser, https://webextract.dev/try shows your USDC balance on every supported network, lets you pick one, switches your wallet to it and signs the payment.

Payment is only settled when the request succeeds (status < 400).

## Use from MCP clients

Remote server, streamable HTTP, stateless: `https://api.webextract.dev/mcp`

Tools:
- `extract_url(url)`: Markdown + structured JSON
- `page_markdown(url)`: Markdown only (cheaper)

Works without a key on the free tier. For prepaid credits add header `Authorization: Bearer <key>`.

Claude Desktop / Cursor style config:

```json
{
  "mcpServers": {
    "webextract": {
      "url": "https://api.webextract.dev/mcp",
      "headers": { "Authorization": "Bearer YOUR_KEY_OPTIONAL" }
    }
  }
}
```

Claude Code:

```sh
claude mcp add --transport http webextract https://api.webextract.dev/mcp
```

Listed in the official MCP Registry as `dev.webextract/extract` (see [`server.json`](server.json)).

## Examples

- [`examples/curl.sh`](examples/curl.sh): free tier, prepaid key, balance, MCP
- [`examples/x402-fetch.mjs`](examples/x402-fetch.mjs): pay per call with x402

## Legal

[Terms](https://webextract.dev/terms) · [Privacy](https://webextract.dev/privacy) · [Refunds](https://webextract.dev/refunds) · Contact: [removed]

## License

This repository (docs, examples, metadata) is MIT licensed; see [LICENSE](LICENSE). The hosted API is a commercial service.
