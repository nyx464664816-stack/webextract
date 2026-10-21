"""LangChain standard unit tests (langchain-tests ToolsUnitTests). No network."""
from typing import Any, Dict, Tuple, Type

from langchain_tests.unit_tests import ToolsUnitTests

from langchain_webextract import WebExtractExtractUrl, WebExtractPageMarkdown

EXAMPLE = {"url": "https://web-scraping.dev/product/1"}
ENV = ({"WEBEXTRACT_API_KEY": "lx_test_env_key"}, {}, {"api_key": "lx_test_env_key"})


class TestExtractUrlStandard(ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[WebExtractExtractUrl]:
        return WebExtractExtractUrl

    @property
    def tool_constructor_params(self) -> Dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return EXAMPLE

    @property
    def init_from_env_params(self) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        return ENV


class TestPageMarkdownStandard(ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[WebExtractPageMarkdown]:
        return WebExtractPageMarkdown

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"url": "https://example.com"}

    @property
    def init_from_env_params(self) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        return ENV
