#!/usr/bin/env sh
# Free tier (50 calls/day per IP, no key)
curl -s "https://api.webextract.dev/v1/markdown?url=https://example.com"

# Prepaid credits (key from https://webextract.dev/#pricing)
curl -s -H "Authorization: Bearer $WEBEXTRACT_KEY" \
  "https://api.webextract.dev/v1/extract?url=https://example.com"

# Remaining credits
curl -s -H "Authorization: Bearer $WEBEXTRACT_KEY" https://api.webextract.dev/v1/balance

# MCP: list tools
curl -s -X POST https://api.webextract.dev/mcp \
  -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
