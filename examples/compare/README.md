# WebExtract: same page, Markdown vs structured JSON, plus copy-paste clients

WebExtract turns a URL into data. `GET /v1/markdown` returns clean Markdown; `GET /v1/extract` returns the same Markdown plus fixed-schema fields (`product`, `tables`, `metadata`) that a program can use without parsing text. Failed REST fetches are not charged. 20 free calls per IP per day, no signup; beyond that, pay per call with x402 USDC or use prepaid credits.

## What the two endpoints return for the same URL

> Captured through the Base Sepolia sandbox routes (`/sandbox/v1/...`, paid with test USDC) on 2026-10-25 (UTC); the sandbox runs the same extraction code as the live `/v1/...` routes, which `compare_rest.py` calls.

### Product page: `https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html`
(a practice product page made for scraping; fetched 2026-10-25T22:27:35.244Z)

- `/v1/markdown`: 1567 characters of Markdown, 261 words.
- `/v1/extract`: the same Markdown (identical) plus `product`, `tables`, `metadata`.
- `product`: {"name": "A Light in the Attic", "price": 51.77, "currency": "GBP", "availability": "InStock", "rating": {"value": 3, "count": null}, "source": "heuristic"}; `price_detail.warnings`: ["heuristic_price_low_confidence", "currency_inferred_from_symbol"]; price evidence: "first [class*=price] element; same amount in table row \"Price (excl. tax)\""
- `tables[0]`: caption=None, headers=["col_1", "col_2"], first rows=[["UPC", "a897fe39b1053632"], ["Product Type", "Books"]], checks={"row_count": 7, "column_count": 2, "consistent_width": true}

Raw responses: `out/product.markdown.json`, `out/product.extract.json`, Markdown text `out/product.markdown.txt`.

### Table page: `https://webscraper.io/test-sites/tables`
(a practice page with two standard HTML tables; fetched 2026-10-25T22:27:38.516Z)

- `/v1/markdown`: 508 characters of Markdown, 124 words.
- `/v1/extract`: the same Markdown (identical) plus `product`, `tables`, `metadata`.
- `product`: null (not a product page, nothing is made up)
- `tables[0]`: caption=None, headers=["#", "First Name", "Last Name", "Username"], first rows=[["1", "Mark", "Otto", "@mdo"], ["2", "Jacob", "Thornton", "@fat"]], checks={"row_count": 3, "column_count": 4, "consistent_width": true}
- `tables[1]`: caption=None, headers=["#", "First Name", "Last Name", "Username"], first rows=[["4", "Harry", "Potter", "@hp"], ["5", "John", "Snow", "@dunno"]], checks={"row_count": 3, "column_count": 4, "consistent_width": true}

Raw responses: `out/table.markdown.json`, `out/table.extract.json`, Markdown text `out/table.markdown.txt`.

All outputs above are real responses from `https://api.webextract.dev` saved as returned, not hand-written. Use `/v1/markdown` when a model just needs to read the page; use `/v1/extract` when your code needs the fields.

## Minimal clients (one file each)

| File | What it does | Install |
|---|---|---|
| `compare_rest.py` | Calls both REST endpoints and prints them side by side | `pip install requests` |
| `langchain_tool.py` | Two LangChain tools, `webextract_markdown` and `webextract_extract` | `pip install langchain-core requests` |
| `mcp_client.py` | Official MCP Python SDK against `https://api.webextract.dev/mcp` (tools `page_markdown`, `extract_url`) | `pip install "mcp>=2"` |
| `x402_client.py` | Pay per call with x402, no account: runs against the Base Sepolia test-network sandbox with test USDC and refuses mainnet | `pip install "x402[evm,httpx]==2.25.0"` |

Run `python <file>.py [page-url]`. When the free tier is used up, the REST API and the MCP tools return an x402 payment challenge (HTTP 402 on REST; an `isError` result on MCP with the requirements in `content[0].text`); set `WEBEXTRACT_KEY` to use a prepaid Bearer key instead. `x402_client.py` needs `X402_TESTNET_PRIVATE_KEY`, a throwaway testnet key (test USDC: https://faucet.circle.com). Never use a key that holds real funds. `WEBEXTRACT_UA` optionally labels your traffic.

## Honest limits
- `product` comes from JSON-LD, OpenGraph, microdata or, as a last resort, page heuristics. Heuristic prices keep the `heuristic_price_low_confidence` warning; check `price_detail.warnings` before trusting a price.
- `product.rating` is filled when the page has JSON-LD or star-rating markup; otherwise it is null.
- The LangChain tools were tested by calling them directly; they were not run inside a model-driven agent.
