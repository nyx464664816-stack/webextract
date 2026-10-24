# WebExtract MCP — installation guide for AI agents (Cline and others)

WebExtract is a **hosted, remote MCP server**. There is nothing to clone, build, or run locally: you only add one entry to your MCP settings.

- Endpoint: `https://api.webextract.dev/mcp`
- Transport: **Streamable HTTP** (stateless; plain JSON responses). SSE is not supported.
- Tools:
  - `extract_url(url)`: fetches a public web page and returns clean Markdown plus fixed-schema JSON (article metadata, product/price, tables).
  - `page_markdown(url)`: returns only the clean Markdown. This is cheaper than `extract_url`.
- Access:
  - Free tier: **20 calls per day per IP address**, no key and no signup. MCP needs no extra header. (The REST API needs the header `X-Billing: free` for the same free tier; without it REST answers HTTP 402.)
  - Prepaid credits (optional): send the header `Authorization: Bearer <key>`. Keys are sold at https://webextract.dev/#pricing.
- WebExtract respects robots.txt and only fetches public `http(s)` URLs.

## 1. Add the server

### Cline (VS Code extension or Cline CLI)

Add this to `cline_mcp_settings.json`. In the extension, open MCP Servers → Configure → "Configure MCP Servers". For the CLI, the file is `~/.cline/data/settings/cline_mcp_settings.json`.

```json
{
  "mcpServers": {
    "webextract": {
      "type": "streamableHttp",
      "url": "https://api.webextract.dev/mcp",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Important: keep `"type": "streamableHttp"`. If `type` is omitted, Cline falls back to the legacy SSE transport and the WebExtract tools will not appear.

Cline CLI one-liner (it writes an equivalent entry):

```sh
cline mcp add webextract https://api.webextract.dev/mcp --transport http --yes
```

The Remote Servers tab in the Cline extension also works: set Server Name to `webextract`, Server URL to `https://api.webextract.dev/mcp`, and Transport Type to "Streamable HTTP".

### Optional: use prepaid credits

Add a `headers` block. Do not commit the key.

```json
{
  "mcpServers": {
    "webextract": {
      "type": "streamableHttp",
      "url": "https://api.webextract.dev/mcp",
      "headers": { "Authorization": "Bearer YOUR_WEBEXTRACT_KEY" },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

CLI: `cline mcp add webextract https://api.webextract.dev/mcp --transport http --header "Authorization: Bearer YOUR_WEBEXTRACT_KEY" --yes`

### Other MCP clients

| Client | How to configure |
|---|---|
| Cursor (`~/.cursor/mcp.json`) | `{"mcpServers":{"webextract":{"url":"https://api.webextract.dev/mcp"}}}` |
| VS Code (`.vscode/mcp.json`) | `{"servers":{"webextract":{"type":"http","url":"https://api.webextract.dev/mcp"}}}` |
| Claude Code | `claude mcp add --transport http webextract https://api.webextract.dev/mcp` |
| stdio-only clients | `npx -y mcp-remote https://api.webextract.dev/mcp --transport http-only` |

## 2. Verify

1. In the MCP server list, the `webextract` server should be enabled and connected, with two tools: `extract_url` and `page_markdown`. In Cline, these are exposed to the model as `webextract__extract_url` and `webextract__page_markdown`.
2. Call `page_markdown` with `{"url": "https://example.com"}`. The text result should begin with "This domain is for use in documentation examples". The structured result should contain `title: "Example Domain"`.
3. Optional check without any MCP client:
   ```sh
   curl -s -X POST https://api.webextract.dev/mcp \
     -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

## 3. Troubleshooting

- **Tools do not appear in Cline**: make sure `"type": "streamableHttp"` is set. If it is omitted, Cline uses SSE, which this server does not provide.
- **A tool returns `isError` with "Free daily limit reached"**: this IP has used its 20 free calls today. Add a prepaid key in `headers`, or wait for the daily reset. Pay-per-call x402 is available through the REST API (`GET https://api.webextract.dev/v1/extract?url=...`, which answers HTTP 402 with x402 requirements), not through MCP. MCP and REST `X-Billing: free` calls share the same 20/day per-IP counter.
- **`invalid_api_key`**: the `Authorization` header must be exactly `Bearer <key>`.
- **robots.txt or private-address errors**: WebExtract only fetches public pages that robots.txt allows. These errors come from the target site and cannot be overridden.
