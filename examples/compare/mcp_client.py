"""Call WebExtract's MCP tools with the official MCP Python SDK (streamable HTTP): page_markdown vs extract_url on the same page.

    pip install "mcp>=2"
    python mcp_client.py [page-url]

Free tier without a key (shared 20 calls/day per IP); WEBEXTRACT_KEY adds a prepaid Bearer key. WEBEXTRACT_UA labels your traffic."""
import asyncio, json, os, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

MCP_URL = os.environ.get("WEBEXTRACT_MCP", "https://api.webextract.dev/mcp")
PAGE = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
headers = {}
if os.environ.get("WEBEXTRACT_KEY"): headers["Authorization"] = f"Bearer {os.environ['WEBEXTRACT_KEY']}"
if os.environ.get("WEBEXTRACT_UA"): headers["User-Agent"] = os.environ["WEBEXTRACT_UA"]
sc = lambda r: getattr(r, "structured_content", None) or getattr(r, "structuredContent", None)   # mcp 2.x / 1.x

async def main() -> None:
    async with create_mcp_http_client(headers=headers or None) as http, streamable_http_client(MCP_URL, http_client=http) as (read, write, *_):
        async with ClientSession(read, write) as s:
            await s.initialize()
            print("tools:", [t.name for t in (await s.list_tools()).tools])
            md = await s.call_tool("page_markdown", {"url": PAGE})
            print("\n--- page_markdown (text for an LLM) ---\n" + md.content[0].text[:400])
            ex = await s.call_tool("extract_url", {"url": PAGE})
            if getattr(ex, "is_error", False) or getattr(ex, "isError", False):
                print("\nextract_url error:", ex.content[0].text[:300]); return
            d = sc(ex) or json.loads(ex.content[0].text); p = d.get("product") or {}
            print("\n--- extract_url (structured fields) ---")
            print(json.dumps({k: p.get(k) for k in ("name", "price", "currency", "availability")}, ensure_ascii=False), "| title:", (d.get("metadata") or {}).get("title"))

asyncio.run(main())
