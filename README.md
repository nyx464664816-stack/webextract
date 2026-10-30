<p align="center"><img src="logo.svg" width="64" alt="WebExtract"></p>

# WebExtract

**Web page → structured JSON (product, tables, metadata) + clean Markdown, for AI agents.** One URL returns product data (name, price, availability), tables with row checks, and article metadata as structured JSON, plus clean Markdown. 20 free calls/day, no signup. Failed REST fetches are not charged. Pay per call with x402 USDC on 7 chains over REST, or use Stripe prepaid credits (REST and MCP).

x402 networks: Base, Polygon, Arbitrum, Avalanche, OP Mainnet, World Chain and Monad. Prepaid credits are bought with a card via Stripe. Works from any MCP client.

- Website: https://webextract.dev
- API base: `https://api.webextract.dev`
- MCP (streamable HTTP): `https://api.webextract.dev/mcp`
- OpenAPI: https://api.webextract.dev/openapi.json · `llms.txt`: https://api.webextract.dev/llms.txt
- Docs: https://webextract.dev/docs
- Try a paid x402 call in your browser wallet: https://webextract.dev/try

## Example output

`GET /v1/extract?url=https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html` (a practice product page made for scraping). Real response saved on 2026-10-25, trimmed here to a few fields; the full files are in [`examples/compare/out`](examples/compare/out).

```json
{
  "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "content_source": "raw_html",
  "word_count": 261,
  "product": {
    "name": "A Light in the Attic",
    "price": 51.77,
    "currency": "GBP",
    "availability": "InStock",
    "rating": { "value": 3, "count": null },
    "source": "heuristic",
    "price_detail": { "warnings": ["heuristic_price_low_confidence", "currency_inferred_from_symbol"] }
  },
  "tables": [
    {
      "headers": ["col_1", "col_2"],
      "rows": [["UPC", "a897fe39b1053632"], ["Product Type", "Books"]],
      "checks": { "row_count": 7, "column_count": 2, "consistent_width": true }
    }
  ]
}
```

The response also carries `markdown` (the page as clean Markdown) and `metadata`. The `warnings` show that the price came from a heuristic, not from structured markup on the page. A page that is not a product page returns `"product": null` instead of a guess. See [`examples/compare`](examples/compare/) for a table page and for how `/v1/markdown` differs.

## Endpoints

| Method | Path | Returns | x402 price | Credits |
| --- | --- | --- | --- | --- |
| GET / POST | `/v1/extract?url=<page>` | Markdown + structured JSON (metadata, product/price, tables) | $0.005 | 1 |
| GET / POST | `/v1/markdown?url=<page>` | Markdown only | $0.002 | 0.4 |
| GET | `/v1/balance` | Free calls left today, or prepaid credits left | free | – |
| POST | `/mcp` | MCP tools `extract_url`, `page_markdown` | use the REST endpoints (not tested over MCP) | same as above, after the free tier |
| GET | `/.well-known/x402` | x402 discovery | free | – |

POST takes the same URL as a JSON body: `{"url": "https://..."}`.

Behaviour:
- `robots.txt` is respected.
- **No charge on failed fetches** (404, timeout, blocked, robots disallowed, invalid URL).
- A missing or invalid `url` returns **400** JSON (`missing_url` / `invalid_url`) before any billing. All errors are JSON.
- Structured JSON costs nothing extra. With a prepaid key, if structured fields come back empty you're charged the Markdown rate (0.4 credit). x402 payments settle at the quoted price.

## Pricing

- **Free:** 20 calls/day per IP, no key, no signup. REST: opt in with the header `X-Billing: free` (or `?free=1`). MCP: no header needed.
- **x402 pay-per-call:** $0.005 (`/v1/extract`) / $0.002 (`/v1/markdown`) in USDC on any supported network (below). No account, no gas needed. Works on the REST endpoints. Over MCP, use the free tier or a prepaid key (see [Use from MCP clients](#use-from-mcp-clients)).
- **Prepaid packs (card, via Stripe Checkout), from $1:** $1 = 200 credits · $5 = 1,000 credits · $20 = 5,000 credits · $50 = 15,000 credits. `/v1/extract` uses 1 credit, `/v1/markdown` uses 0.4 credit. **Credits never expire.** Buy at https://webextract.dev/#pricing; the API key is shown once on the success page.

## Measured results

We ran WebExtract on 10 public pages and published the raw files and scripts: <https://webextract.dev/benchmark> · [`examples/benchmark`](examples/benchmark).

- Sandbox (Base Sepolia test USDC), 4 runs per page and endpoint, 80 calls: `/v1/markdown` 38/40 succeeded (95.0%), `/v1/extract` 40/40 (100.0%). Field checks passed: 75/75 and 212/212. The two failures are counted in the rate.
- Failed fetches on the sandbox route: 10 calls that must fail, wallet balance 18.904000 USDC before and after (control call: 0.002000 USDC). We did not run failing URLs through the paid live path.
- The sandbox and `/v1` run in the same server process and call the same extraction function; only the payment step differs.
- Limits: one client, one day, 10 pages that are easy to fetch. No competitor was run; no mainnet payment and no payment through MCP was tested.

## Quick start

```sh
# Free tier (opt-in: 20 calls/day per IP)
curl -H "X-Billing: free" "https://api.webextract.dev/v1/markdown?url=https://example.com"

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
  "word_count": 25
}
```

Prepaid responses include `X-Credits-Charged` and `X-Credits-Remaining` headers; free-tier responses (only with `X-Billing: free` / `?free=1`) include `X-Free-Remaining`. Without a key, a payment or `X-Billing: free`, the REST endpoints answer HTTP 402 (`reason: x402_required`).

## Pay per call with x402

Requests without a key, payment or `X-Billing: free` get **HTTP 402** (`reason: x402_required`; `X-Billing: x402` gives the same 402 with `reason: x402_requested`) with an x402 v2 `PAYMENT-REQUIRED` header (scheme `exact`). It lists one option per network; pay with whichever one your wallet holds USDC on (see [Choosing a network with the SDK](#choosing-a-network-with-the-sdk)):

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

The JSON body of every 402 says why, in `reason` (also in the `X-Payment-Reason` header):

| `reason` | Meaning |
| --- | --- |
| `x402_required` | No key, no payment and no free opt-in. Pay with x402, use a key, or retry with `X-Billing: free` |
| `x402_requested` | You sent `X-Billing: x402` and no payment yet |
| `free_limit_reached` | You opted in with `X-Billing: free` / `?free=1` but your IP's free calls are used up (`X-Free-Remaining: 0`) |
| `invalid_payment` | A payment was sent but rejected; `detail` has a short reason code (e.g. `invalid_exact_evm_insufficient_balance`). Not charged |
| `unsupported_network` | The payment used a network this endpoint does not accept |
| `settlement_failed` | The payment was verified but on-chain settlement did not complete. Not charged (`retryable: true`); retry with a freshly signed payment |

An unknown `X-Billing` value returns 400 `invalid_billing_mode`. Precedence: a Bearer key wins over a payment, and a payment wins over `X-Billing: free`.

See the requirements without paying anything: [`examples/curl/x402-inspect.sh`](examples/curl/x402-inspect.sh), [`examples/python/inspect_402.py`](examples/python/inspect_402.py) or [`examples/node/inspect-402.mjs`](examples/node/inspect-402.mjs).

### Choosing a network with the SDK

Any x402 client can pay and retry automatically. Two things to know with the official SDKs (`@x402/fetch` / `@x402/evm` 2.28, Python `x402` 2.25):

1. **OP Mainnet and World Chain USDC are not in the SDK default asset list**, so the default `spendControls` reject those options. Add them to `spendControls.allowedAssets`.
2. **With `network: "eip155:*"` the SDK picks the first option (Base)** even if your USDC is elsewhere. Register only the networks where your wallet holds USDC, or pass a `paymentRequirementsSelector`.

```js
// npm i @x402/fetch @x402/evm viem
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.EVM_PRIVATE_KEY); // low-balance hot wallet
const funded = ["eip155:10"]; // networks where this wallet holds USDC, e.g. OP Mainnet
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: funded.map(network => ({ network, client: new ExactEvmScheme(account) })),
  spendControls: { allowedAssets: [
    { network: "eip155:10",  asset: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", maxAmountPerPayment: "10000" }, // OP Mainnet USDC, $0.01 cap
    { network: "eip155:480", asset: "0x79A02482A880bCE3F13e09Da970dC34db4CD24d1", maxAmountPerPayment: "10000" }, // World Chain USDC
  ] },
});

const res = await fetchWithPayment(
  "https://api.webextract.dev/v1/extract?url=" + encodeURIComponent("https://example.com"),
  { headers: { "X-Billing": "x402" } }
);
console.log(await res.json());
```

[`examples/node/x402-fetch.mjs`](examples/node/x402-fetch.mjs) does this automatically: it reads your USDC balance on every supported network, registers only the funded ones, prefers Base, and has a `--dry-run` mode that signs nothing.

In a browser, https://webextract.dev/try shows your USDC balance on every supported network, lets you pick one, switches your wallet to it and signs the payment.

REST: payment is only settled when the request succeeds (status < 400).

### Sandbox (free test money only)

Test your x402 integration without real money: call `https://api.webextract.dev/sandbox/v1/extract` or `/sandbox/v1/markdown`, or send `X-Billing: x402-testnet` to the normal endpoints. The sandbox accepts only **Base Sepolia** (`eip155:84532`) test USDC `0x036CbD53842c5426634e7929541eC2318f3dCF7e`, settled by the `https://x402.org/facilitator` testnet facilitator. Get test USDC at https://faucet.circle.com. Responses are identical; nothing real is charged. Rate limited to 20 requests/minute and 300/day per IP.

```sh
WEBEXTRACT_BILLING=x402-testnet ./examples/curl/x402-inspect.sh markdown
WEBEXTRACT_SANDBOX=1 EVM_PRIVATE_KEY=0x<testnet-only key> node examples/node/x402-fetch.mjs
```

## Use from MCP clients

Remote server, streamable HTTP, stateless: `https://api.webextract.dev/mcp`

Tools:
- `extract_url(url)`: Markdown + structured JSON
- `page_markdown(url)`: Markdown only (cheaper)

Works without a key on the free tier (20 calls/day per IP, no `X-Billing` header needed for MCP). For prepaid credits add header `Authorization: Bearer <key>`.

Both tools declare an `outputSchema` and return `structuredContent`.

**After the free tier over MCP:** once this IP's 20 free calls are used up, a `tools/call` without a Bearer key returns an error result (`isError: true`) whose text carries the payment requirements as JSON. Paying x402 through MCP has not been tested; add a prepaid key (`Authorization: Bearer <key>`), wait for the daily reset, or use the REST endpoints for x402 pay-per-call. `initialize` and `tools/list` are always free. Calls that reach the server through Smithery's shared free pool use your own key there. To test x402 without real money, use the REST [sandbox](#sandbox-free-test-money-only).

Ready-made client configs in [`examples/mcp/`](examples/mcp/):

| Client | File |
| --- | --- |
| Cursor | [`cursor.mcp.json`](examples/mcp/cursor.mcp.json) → `~/.cursor/mcp.json` (with key: [`cursor.mcp.with-key.json`](examples/mcp/cursor.mcp.with-key.json), uses `${env:WEBEXTRACT_KEY}`) |
| VS Code | [`vscode.mcp.json`](examples/mcp/vscode.mcp.json) → `.vscode/mcp.json` |
| Claude Desktop | [`claude_desktop_config.json`](examples/mcp/claude_desktop_config.json) (stdio bridge via `npx mcp-remote`; with key: [`claude_desktop_config.with-key.json`](examples/mcp/claude_desktop_config.with-key.json)). Or add the URL under Settings → Connectors. |
| Cline | [`cline_mcp_settings.json`](examples/mcp/cline_mcp_settings.json). Set `"type": "streamableHttp"` or Cline falls back to SSE and no tools appear. Step-by-step: [`llms-install.md`](llms-install.md). |
| Claude Code | [`claude-code.sh`](examples/mcp/claude-code.sh) |

Cursor-style config:

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

- [`examples/curl/quickstart.sh`](examples/curl/quickstart.sh): free tier or prepaid key, balance, Markdown and structured extract
- [`examples/curl/x402-inspect.sh`](examples/curl/x402-inspect.sh): show and decode the x402 402 without paying
- [`examples/python/inspect_402.py`](examples/python/inspect_402.py): decode the 402 with the official Python `x402` SDK (`pip install -r examples/python/requirements.txt`)
- [`examples/node/inspect-402.mjs`](examples/node/inspect-402.mjs): decode the 402 with `@x402/core` (`cd examples/node && npm i`)
- [`examples/node/x402-fetch.mjs`](examples/node/x402-fetch.mjs): pay per call with x402 on the network where your wallet holds USDC (sandbox and dry-run modes)
- [`examples/mcp/`](examples/mcp/): MCP client configs
- [`examples/compare/`](examples/compare/): same page through `/v1/markdown` vs `/v1/extract` (structured JSON), with saved real outputs and minimal REST, LangChain, MCP and x402 clients

## Changes

Behavior changes to the hosted service are listed in [CHANGELOG.md](CHANGELOG.md).

## Legal

Operated by TAINCHENG, L.L.C. (United States).

[Terms](https://webextract.dev/terms) · [Privacy](https://webextract.dev/privacy) · [Refunds](https://webextract.dev/refunds) · Contact: [removed]

## License

This repository (docs, examples, metadata) is MIT licensed; see [LICENSE](LICENSE). The hosted API is a commercial service.
