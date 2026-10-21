# langchain-webextract

LangChain tools for [WebExtract](https://webextract.dev). The tool names and outputs match the WebExtract MCP tools:

- `extract_url`: clean Markdown plus fixed-schema JSON (metadata, product and price with `price_detail`, tables). $0.005 or 1 credit.
- `page_markdown`: clean Markdown only. $0.002 or 0.4 credit.

```bash
pip install langchain-webextract
```

This also installs the core client from PyPI `webextract-sdk` (imported as `webextract`). For x402 pay per call add `pip install "webextract-sdk[x402]"`.

```python
from langchain_webextract import WebExtractExtractUrl, WebExtractPageMarkdown, get_webextract_tools
from webextract import WebExtract

tools = get_webextract_tools()                                    # free tier, or WEBEXTRACT_API_KEY if set
tools = get_webextract_tools(api_key="lx_...")                     # prepaid credits (SecretStr field)
tools = get_webextract_tools(client=WebExtract(api_key="lx_..."))  # prepaid credits
print(WebExtractPageMarkdown().invoke({"url": "https://example.com"}))
```

**x402 pay per call (async).** Build the paying client with the official x402 SDK, then hand it over. This package never sees the private key.

```python
from webextract import AsyncWebExtract
tool = WebExtractExtractUrl(async_client=AsyncWebExtract(payment_client=x402_httpx_client))
await tool.ainvoke({"url": "https://web-scraping.dev/product/1"})
```

The tools return a JSON string. By default, API errors come back to the model as `{"ok": false, "error": {"error", "status", "message", "charged", "reason", "hint", ...}}`, so an agent can react to `free_limit_reached`, `robots_disallowed` and so on. Set `on_error="raise"` to raise `webextract.WebExtractError` subclasses instead.

## Tests

```bash
pytest --disable-socket --allow-unix-socket tests/unit_tests                  # mocks + langchain-tests ToolsUnitTests
pytest --disable-socket --allow-unix-socket tests/integration_tests           # ToolsIntegrationTests, offline (mocked API)
WEBEXTRACT_SANDBOX_TESTS=1 X402_TESTNET_ENV_FILE=/path/to/testnet.env \
  pytest tests/integration_tests/test_standard_sandbox.py                     # live sandbox, Base Sepolia TEST USDC only
```

License: MIT © TAINCHENG, L.L.C.
