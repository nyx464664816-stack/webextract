"""Canned API responses (shapes copied from the live API, schema_version 1.0 + 2026-10-21 additive fields)."""
import json

import httpx

from webextract import AsyncWebExtract, WebExtract

EXTRACT = {
    "url": "https://web-scraping.dev/product/1", "final_url": "https://web-scraping.dev/product/1",
    "fetched_at": "2026-10-21T11:00:00.000Z", "schema_version": "1.0", "content_source": "raw_html",
    "markdown": "# Box of Chocolate Candy\n\n...", "markdown_truncated": False, "word_count": 120,
    "metadata": {"title": "Box of Chocolate Candy", "description": None, "authors": [], "published_at": None, "modified_at": None,
                 "site_name": None, "language": "en", "canonical_url": None, "image": None, "type": "product"},
    "product": {"name": "Box of Chocolate Candy", "brand": None, "sku": None, "gtin": None, "description": None, "image": None,
                "price": 9.99, "price_high": None, "currency": "USD", "availability": "InStock", "rating": None, "source": "json-ld",
                "price_detail": {"status": "resolved", "currency": "USD", "currency_basis": "declared",
                                 "prices": [{"type": "sale", "amount": 9.99, "currency": "USD", "method": "dom"},
                                            {"type": "list", "amount": 12.99, "currency": "USD", "method": "dom"}],
                                 "unresolved": None, "warnings": []}},
    "tables": [],
}
MARKDOWN = {"url": "https://example.com", "final_url": "https://example.com/", "fetched_at": "2026-10-21T11:00:00.000Z",
            "content_source": "raw_html", "title": "Example Domain", "markdown": "# Example Domain\n\n...", "markdown_truncated": False,
            "word_count": 25}
FREE_LIMIT = {"error": "payment_required", "reason": "free_limit_reached", "message": "Free daily limit reached"}


def _handler(status=200, body=None):
    def h(req: httpx.Request) -> httpx.Response:
        payload = body if body is not None else (MARKDOWN if req.url.path.endswith("/markdown") else EXTRACT)
        headers = {"x-payment-reason": payload["reason"]} if status == 402 else {}
        return httpx.Response(status, content=json.dumps(payload), headers={"content-type": "application/json", **headers})
    return h


def mock_clients(status=200, body=None):
    t = _handler(status, body)
    return {"client": WebExtract(http_client=httpx.Client(transport=httpx.MockTransport(t))),
            "async_client": AsyncWebExtract(http_client=httpx.AsyncClient(transport=httpx.MockTransport(t)))}
