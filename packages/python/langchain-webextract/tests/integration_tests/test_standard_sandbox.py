"""LangChain standard integration tests against the LIVE WebExtract SANDBOX (Base Sepolia test USDC only).

Opt-in: set WEBEXTRACT_SANDBOX_TESTS=1 and X402_TESTNET_ENV_FILE=<path to a mode-600 .env with
X402_TESTNET_PRIVATE_KEY>. Only eip155:84532 is registered with the x402 SDK and billing is x402-testnet,
so nothing can be signed for a mainnet requirement. The key is never printed. Each run makes 4 test payments
per tool (sync + async, with and without ToolCall)."""
import json
import os
import stat
import time
from typing import Any, Dict, Type

import pytest
from langchain_core.messages import ToolCall
from langchain_core.tools import BaseTool
from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_webextract import WebExtractExtractUrl, WebExtractPageMarkdown
from webextract import AsyncWebExtract, WebExtract

NET = "eip155:84532"
pytestmark = pytest.mark.skipif(os.environ.get("WEBEXTRACT_SANDBOX_TESTS") != "1", reason="set WEBEXTRACT_SANDBOX_TESTS=1 to run live sandbox tests")


def _key() -> str:
    path = os.environ["X402_TESTNET_ENV_FILE"]
    if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise RuntimeError("testnet .env must be mode 600")
    with open(path) as f:
        return next(l.split("=", 1)[1].strip() for l in f if l.startswith("X402_TESTNET_PRIVATE_KEY="))


def sandbox_clients() -> Dict[str, Any]:
    from eth_account import Account
    from x402 import x402Client, x402ClientSync
    from x402.http.clients import x402_requests, x402HttpxClient
    from x402.mechanisms.evm.exact import ExactEvmScheme

    acct = Account.from_key(_key())
    sync_x, async_x = x402ClientSync(), x402Client()
    sync_x.register(NET, ExactEvmScheme(signer=acct))
    async_x.register(NET, ExactEvmScheme(signer=acct))
    return {"client": WebExtract(payment_client=x402_requests(sync_x), billing="x402-testnet", timeout=60),
            "async_client": AsyncWebExtract(payment_client=x402HttpxClient(async_x, timeout=60), billing="x402-testnet", timeout=60)}


@pytest.fixture(autouse=True)
def _pace():
    """The sandbox allows 20 requests/minute per IP and every x402 call is 2 HTTP requests
    (unpaid 402, then the signed retry), so stay at <= ~9 paid calls per minute."""
    yield
    time.sleep(float(os.environ.get("WEBEXTRACT_SANDBOX_PACE_S", "7")))


class _Live(ToolsIntegrationTests):
    @property
    def tool_constructor_params(self) -> Dict[str, Any]:
        # on_error="raise": any 402/422/429 from the sandbox fails the standard tests instead of being
        # returned to the "model" as an error object, so a green run means every call was paid and served.
        return {**sandbox_clients(), "on_error": "raise"}

    def test_live_result_is_success(self, tool: BaseTool) -> None:
        """Extra (not in the standard suite): the live sandbox call must succeed, not come back as an error object."""
        msg = tool.invoke(ToolCall(name=tool.name, args=self.tool_invoke_params_example, id="1", type="tool_call"))
        out = json.loads(msg.content)
        assert out.get("ok") is not False, out
        assert out["markdown"] and out.get("content_source") in (None, "raw_html")


class TestPageMarkdownSandbox(_Live):
    @property
    def tool_constructor(self) -> Type[WebExtractPageMarkdown]:
        return WebExtractPageMarkdown

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"url": "https://example.com"}


class TestExtractUrlSandbox(_Live):
    @property
    def tool_constructor(self) -> Type[WebExtractExtractUrl]:
        return WebExtractExtractUrl

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"url": "https://web-scraping.dev/product/1"}
