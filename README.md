<p align="center"><img src="logo.svg" width="64" alt="WebExtract"></p>

# WebExtract

**Web page → clean Markdown + fixed-schema JSON, for AI agents.** One GET request turns any public URL into LLM-ready Markdown plus structured data (article metadata, product/price, tables). Pay per call with **x402 (USDC on Base, Polygon, Arbitrum, Avalanche, OP Mainnet, World Chain or Monad)**, buy prepaid credits with a card (**Stripe**), or use it from any MCP client.

- Website: https://webextract.dev
- API base: `https://api.webextract.dev`
- MCP (streamable HTTP): `https://api.webextract.dev/mcp`
- OpenAPI: https://api.webextract.dev/openapi.json · `llms.txt`: https://api.webextract.dev/llms.txt
- Docs: https://webextract.dev/docs
- Try a paid x402 call in your browser wallet: https://webextract.dev/try

## Endpoints

| Method | Path | Returns | x402 price | Credits |
| --- | --- | --- | --- | --- |
| GET / POST | `/v1/extract?url=<page>` | Markdown + structured JSON (metadata, product/price, tables) | $0.005 | 1 |
| GET / POST | `/v1/markdown?url=<page>` | Markdown only | $0.002 | 0.4 |
| GET | `/v1/balance` | Free calls left today, or prepaid credits left | free | – |
| POST | `/mcp` | MCP tools `extract_url`, `page_markdown` | – | same as above |
| GET | `/.well-known/x402` | x402 discovery | free | – |

POST takes the same URL as a JSON body: `{"url": "https://..."}`.

Behaviour:
- `robots.txt` is respected.
- **No charge on failed fetches** (404, timeout, blocked, robots disallowed, invalid URL).
- A missing or invalid `url` returns **400** JSON (`missing_url` / `invalid_url`) before any billing. All errors are JSON.
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
  "word_count": 25
}
```

Prepaid responses include `X-Credits-Charged` and `X-Credits-Remaining` headers; free-tier responses include `X-Free-Remaining`.

## Pay per call with x402

Requests without a key and without free calls left (or with `X-Billing: x402`) get **HTTP 402** with an x402 v2 `PAYMENT-REQUIRED` header (scheme `exact`). It lists one option per network; pay with whichever one your wallet holds USDC on (see [Choosing a network with the SDK](#choosing-a-network-with-the-sdk)):

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
| `x402_requested` | You sent `X-Billing: x402` and no payment yet |
| `free_limit_reached` | Free calls for your IP are used up |
| `invalid_payment` | A payment was sent but rejected; `detail` has the facilitator's reason (e.g. `invalid_exact_evm_insufficient_balance`). Not charged |
| `unsupported_network` | The payment used a network this endpoint does not accept |

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

Payment is only settled when the request succeeds (status < 400).

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

Works without a key on the free tier. For prepaid credits add header `Authorization: Bearer <key>`.

Both tools declare an `outputSchema` and return `structuredContent`. MCP calls use the free tier or a Bearer key; for pay-per-call without an account use the REST endpoints with x402.

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

## Legal

[Terms](https://webextract.dev/terms) · [Privacy](https://webextract.dev/privacy) · [Refunds](https://webextract.dev/refunds) · Contact: [removed]

## License

This repository (docs, examples, metadata) is MIT licensed; see [LICENSE](LICENSE). The hosted API is a commercial service.
