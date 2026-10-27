# Changelog

Behavior changes to the hosted service at `api.webextract.dev` (REST and MCP). Newest first.

## 2026-10-27

### Clearer errors when a fetch fails
- Failed fetches (for example HTTP 422) keep the same status code, `error` code and `message`, and add two fields: `category` (one of `dns_failed`, `private_address`, `invalid_url`, `robots_disallowed`, `target_blocked`, `target_http_error`, `not_html`, `too_large`, `timeout`, `tls_error`, `redirect_error`, `target_unreachable`, `extract_failed`, `busy`) and, when the target site answered with an HTTP error, `upstream_status`. `charged: false` is still included. Example: `{"error":"upstream_error","message":"target site returned HTTP 404; not charged","charged":false,"category":"target_http_error","upstream_status":404}`.
- MCP tool errors keep the same first text block and add a second text block with the same fields as JSON: `{"error","category","upstream_status","charged":false}`.
- For failed calls, our access log now records only the target's domain and the stage where the fetch failed. It does not record the full URL, path or query string.
- REST and MCP were both checked on the live service.

### Pages with no readable text
- Pages with no readable text (empty markdown; for `/v1/extract` also no product and no tables) still return 200, but no longer use your free daily quota or prepaid credits. The response now includes `warnings: ["empty_content"]`, a `hint` saying you can use the render endpoint instead, and `charged: false`. Applies to REST and MCP; both were checked on the live service.
- The x402 paid path is unchanged: paid x402 calls that return an empty page are still charged at the quoted price.

### Tables
- `/v1/extract` `tables` now expand `rowspan`/`colspan`, so every row has the same number of cells and matches the Markdown output.

### `js_rendered_suspected`
- Server-rendered pages that already contain 150+ words of text are no longer flagged `js_rendered_suspected`; they now report `no_product_markup`. Genuinely empty app shells are still flagged.
