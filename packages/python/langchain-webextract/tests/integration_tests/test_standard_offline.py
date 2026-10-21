"""LangChain standard integration tests (ToolsIntegrationTests) run OFFLINE: the WebExtract HTTP API is
replaced by httpx.MockTransport with real response shapes. Includes an error variant (402 free_limit_reached)
to prove the tool never raises on API errors by default."""
from typing import Any, Dict, Type

from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_webextract import WebExtractExtractUrl, WebExtractPageMarkdown
from tests._fixtures import FREE_LIMIT, mock_clients


class TestExtractUrlOffline(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[WebExtractExtractUrl]:
        return WebExtractExtractUrl

    @property
    def tool_constructor_params(self) -> Dict[str, Any]:
        return mock_clients()

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"url": "https://web-scraping.dev/product/1"}


class TestPageMarkdownOffline(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[WebExtractPageMarkdown]:
        return WebExtractPageMarkdown

    @property
    def tool_constructor_params(self) -> Dict[str, Any]:
        return mock_clients()

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"url": "https://example.com"}


class TestExtractUrlOffline402(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[WebExtractExtractUrl]:
        return WebExtractExtractUrl

    @property
    def tool_constructor_params(self) -> Dict[str, Any]:
        return mock_clients(402, FREE_LIMIT)

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"url": "https://web-scraping.dev/product/1"}
