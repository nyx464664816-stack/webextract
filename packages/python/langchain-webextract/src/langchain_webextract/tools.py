"""LangChain tools for WebExtract. Tool names and outputs match the MCP tools (extract_url, page_markdown)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, Type

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_core.utils import secret_from_env
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, SecretStr, field_validator

from webextract import TOOL_DESCRIPTIONS, AsyncWebExtract, WebExtract, WebExtractError


class WebExtractInput(BaseModel):
    """Input for the WebExtract tools."""

    url: str = Field(description=TOOL_DESCRIPTIONS["url"])

    @field_validator("url")
    @classmethod
    def _http_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("url must be an absolute http(s) URL")
        return v


class _WebExtractBaseTool(BaseTool):
    """Shared plumbing. Pass ``client`` (sync) and/or ``async_client``; with neither, a free-tier sync client
    is created (X-Billing: free, 50 calls/day per IP). For x402 pay-per-call pass
    ``async_client=AsyncWebExtract(payment_client=x402HttpxClient(...))``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    args_schema: Type[BaseModel] = WebExtractInput
    client: Optional[WebExtract] = None
    async_client: Optional[AsyncWebExtract] = None
    api_key: Optional[SecretStr] = Field(default_factory=secret_from_env("WEBEXTRACT_API_KEY", default=None))
    """Prepaid key (Stripe credits). Defaults to the WEBEXTRACT_API_KEY env var. Only used when no client is given."""
    billing: Optional[Literal["key", "free", "x402", "x402-testnet"]] = None
    """Billing for the built-in client (default: key if api_key is set, else free). x402 needs a client with payment_client."""
    base_url: Optional[str] = None
    on_error: Literal["return", "raise"] = "return"
    """"return": API errors (402 reason, failed fetch, bad url) come back to the model as a JSON string
    {"ok": false, "error": {...}}. "raise": re-raise the WebExtractError."""
    _endpoint: str = PrivateAttr(default="")

    def _sync(self) -> WebExtract:
        if self.client is None:
            if self.async_client is not None:
                raise RuntimeError("only async_client is configured; call the tool with ainvoke()")
            use_key = self.api_key is not None and self.billing in (None, "key")
            self.client = WebExtract(api_key=self.api_key.get_secret_value() if use_key else None,
                                     billing=self.billing or ("key" if use_key else "free"), base_url=self.base_url)
        return self.client

    def _fail(self, e: WebExtractError) -> str:
        if self.on_error == "raise":
            raise e
        return json.dumps({"ok": False, "error": e.to_dict()})

    def _run(self, url: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            r = getattr(self._sync(), self._endpoint)(url)
        except WebExtractError as e:
            return self._fail(e)
        return json.dumps(r.data, ensure_ascii=False)

    async def _arun(self, url: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        if self.async_client is None:
            return await super()._arun(url, run_manager=run_manager)  # runs _run in a thread
        try:
            r = await getattr(self.async_client, self._endpoint)(url)
        except WebExtractError as e:
            return self._fail(e)
        return json.dumps(r.data, ensure_ascii=False)


class WebExtractExtractUrl(_WebExtractBaseTool):
    """Markdown + fixed-schema JSON (metadata, product/price incl. price_detail, tables) for a URL. $0.005 or 1 credit."""

    name: str = "extract_url"
    description: str = TOOL_DESCRIPTIONS["extract_url"]
    _endpoint: str = PrivateAttr(default="extract")


class WebExtractPageMarkdown(_WebExtractBaseTool):
    """Clean Markdown for a URL. $0.002 or 0.4 credit."""

    name: str = "page_markdown"
    description: str = TOOL_DESCRIPTIONS["page_markdown"]
    _endpoint: str = PrivateAttr(default="markdown")


def get_webextract_tools(**kwargs: Any) -> List[BaseTool]:
    """Both tools sharing the same clients/options, e.g. ``get_webextract_tools(client=WebExtract(api_key=...))``."""
    return [WebExtractExtractUrl(**kwargs), WebExtractPageMarkdown(**kwargs)]
