#!/usr/bin/env bash
# Claude Code: add WebExtract as a remote (streamable HTTP) MCP server.
claude mcp add --transport http webextract https://api.webextract.dev/mcp
# With prepaid credits:
# claude mcp add --transport http webextract https://api.webextract.dev/mcp --header "Authorization: Bearer $WEBEXTRACT_KEY"
