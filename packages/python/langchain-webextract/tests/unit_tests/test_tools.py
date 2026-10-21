"""Unit tests with mocked HTTP. No network, no money."""
import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from langchain_webextract import WebExtractExtractUrl, WebExtractPageMarkdown, get_webextract_tools
from webextract import AsyncWebExtract, TargetFetchError, WebExtract

MD = {"url": "https://a.test/", "final_url": "https://a.test/", "title": "A", "markdown": "# A"}
EX = {"url": "u", "final_url": "u", "markdown": "# A", "metadata": {}, "tables": [], "product": None, "product_unresolved": {"reason": "listing_page"}}


def transport(status, body, headers=None, calls=None):
    def h(req):
        if calls is not None:
            calls.append(req)
        return httpx.Response(status, json=body, headers=headers or {})
    return httpx.MockTransport(h)


def sync(status, body, headers=None, calls=None, **kw):
    return WebExtract(http_client=httpx.Client(transport=transport(status, body, headers, calls)), **kw)


def test_names_and_schema():
    a, b = get_webextract_tools(client=sync(200, MD))
    assert (a.name, b.name) == ("extract_url", "page_markdown")
    assert "url" in a.args and "Markdown" in a.description
    assert a.tool_call_schema.model_json_schema()["required"] == ["url"]


def test_extract_invoke_returns_json_string():
    calls = []
    out = json.loads(WebExtractExtractUrl(client=sync(200, EX, None, calls)).invoke({"url": "https://a.test/"}))
    assert out["product_unresolved"]["reason"] == "listing_page" and calls[0].url.path == "/v1/extract"


def test_markdown_invoke_with_key():
    calls = []
    out = json.loads(WebExtractPageMarkdown(client=sync(200, MD, None, calls, api_key="lx_k")).invoke({"url": "https://a.test/"}))
    assert out["markdown"] == "# A" and calls[0].headers["authorization"] == "Bearer lx_k"


def test_invalid_url_rejected_before_http():
    calls = []
    with pytest.raises(ValidationError):
        WebExtractPageMarkdown(client=sync(200, MD, None, calls)).invoke({"url": "nope"})
    assert calls == []


def test_402_returned_as_error_json():
    t = WebExtractExtractUrl(client=sync(402, {"error": "payment_required", "reason": "free_limit_reached", "message": "limit"}, {"x-payment-reason": "free_limit_reached"}))
    out = json.loads(t.invoke({"url": "https://a.test/"}))
    assert out["ok"] is False and out["error"]["reason"] == "free_limit_reached" and out["error"]["charged"] is False


def test_on_error_raise():
    t = WebExtractExtractUrl(client=sync(451, {"error": "robots_disallowed", "message": "robots", "charged": False}), on_error="raise")
    with pytest.raises(TargetFetchError):
        t.invoke({"url": "https://a.test/"})


def test_async_client_used_by_ainvoke():
    calls = []
    ac = AsyncWebExtract(http_client=httpx.AsyncClient(transport=transport(200, MD, None, calls)))
    out = json.loads(asyncio.run(WebExtractPageMarkdown(async_client=ac).ainvoke({"url": "https://a.test/"})))
    assert out["markdown"] == "# A" and calls[0].url.path == "/v1/markdown"


def test_sync_invoke_with_only_async_client_is_clear_error():
    ac = AsyncWebExtract(http_client=httpx.AsyncClient(transport=transport(200, MD)))
    with pytest.raises(RuntimeError, match="ainvoke"):
        WebExtractPageMarkdown(async_client=ac).invoke({"url": "https://a.test/"})


def test_ainvoke_falls_back_to_sync_client():
    calls = []
    out = json.loads(asyncio.run(WebExtractPageMarkdown(client=sync(200, MD, None, calls)).ainvoke({"url": "https://a.test/"})))
    assert out["markdown"] == "# A" and len(calls) == 1
