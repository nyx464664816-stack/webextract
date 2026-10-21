"""Unit tests: all HTTP is mocked with httpx.MockTransport. No network, no money."""
import asyncio
import base64
import json

import httpx
import pytest

import webextract as we

@pytest.fixture(autouse=True)
def _no_env_key(monkeypatch):
    monkeypatch.delenv("WEBEXTRACT_API_KEY", raising=False)


PR = {"x402Version": 2, "accepts": [{"network": "eip155:8453"}, {"network": "eip155:137"}, {"network": "eip155:8453"}]}
EX = {"url": "u", "final_url": "u", "fetched_at": "t", "schema_version": "1.0", "markdown": "# P", "metadata": {}, "tables": [],
      "content_source": "raw_html", "product": {"price": None, "price_detail": {"status": "unresolved", "prices": [],
      "unresolved": {"reason": "variant_not_matched"}}}}


def b64(o):
    return base64.b64encode(json.dumps(o).encode()).decode()


def mock(status, body, headers=None, calls=None):
    def handler(req):
        if calls is not None:
            calls.append(req)
        content = body if isinstance(body, str) else json.dumps(body)
        return httpx.Response(status, content=content, headers={"content-type": "application/json", **(headers or {})})
    return httpx.MockTransport(handler)


def client(status, body, resp_headers=None, calls=None, **kw):
    return we.WebExtract(http_client=httpx.Client(transport=mock(status, body, resp_headers, calls)), **kw)


def test_default_free_get_with_encoded_url():
    calls = []
    r = client(200, EX, {"x-free-remaining": "9"}, calls).extract("https://shop.test/p?variant=red&a=b")
    req = calls[0]
    assert req.method == "GET" and req.url.path == "/v1/extract"
    assert req.url.params["url"] == "https://shop.test/p?variant=red&a=b"
    assert req.headers["x-billing"] == "free" and "authorization" not in req.headers
    assert r.meta.billing == "free" and r.meta.free_remaining == 9
    assert r.data["product"]["price_detail"]["unresolved"]["reason"] == "variant_not_matched"
    assert r.data["content_source"] == "raw_html"


def test_api_key_bearer_and_credit_headers():
    calls = []
    r = client(200, EX, {"x-credits-charged": "0.4", "x-credits-remaining": "10"}, calls, api_key="lx_secret").markdown("https://a.test/")
    assert calls[0].url.path == "/v1/markdown"
    assert calls[0].headers["authorization"] == "Bearer lx_secret" and "x-billing" not in calls[0].headers
    assert r.meta.credits_charged == 0.4 and r.meta.credits_remaining == 10
    assert "lx_secret" not in repr(client(200, EX, api_key="lx_secret"))


def test_payment_client_no_billing_header_and_receipt():
    calls = []
    pay = httpx.Client(transport=mock(200, EX, {"payment-response": b64({"transaction": "0xabc"})}, calls))
    r = we.WebExtract(payment_client=pay).extract("https://a.test/")
    assert "x-billing" not in calls[0].headers and r.meta.billing == "x402"
    assert r.meta.payment_response["transaction"] == "0xabc"


def test_testnet_header_and_sandbox_flag():
    calls = []
    pay = httpx.Client(transport=mock(200, EX, {"x-sandbox": "true"}, calls))
    r = we.WebExtract(payment_client=pay, billing="x402-testnet").markdown("https://a.test/")
    assert calls[0].headers["x-billing"] == "x402-testnet" and r.meta.sandbox is True


def test_protected_headers_cannot_be_overridden():
    calls = []
    client(200, EX, None, calls, headers={"Authorization": "Bearer evil", "X-Billing": "x402", "x-trace": "1"}).extract("https://a.test/")
    h = calls[0].headers
    assert h["x-billing"] == "free" and "authorization" not in h and h["x-trace"] == "1"


@pytest.mark.parametrize("kw,msg", [
    ({"api_key": "k", "payment_client": httpx.Client()}, "not both"),
    ({"billing": "x402"}, "needs payment_client"),
    ({"billing": "x402-testnet"}, "needs payment_client"),
    ({"billing": "key"}, "needs api_key"),
    ({"api_key": "k", "billing": "free"}, "cannot be combined"),
    ({"api_key": " "}, "non-empty"),
    ({"billing": "bogus"}, "unknown billing"),
])
def test_bad_configs(kw, msg):
    with pytest.raises(TypeError, match=msg):
        we.WebExtract(**kw)


@pytest.mark.parametrize("url,code", [("", "missing_url"), ("nope", "invalid_url"), ("ftp://x/", "invalid_url")])
def test_client_side_url_check_sends_nothing(url, code):
    calls = []
    with pytest.raises(we.InvalidRequestError) as ei:
        client(200, EX, None, calls).extract(url)
    assert ei.value.code == code and calls == []


@pytest.mark.parametrize("reason", ["x402_required", "x402_requested", "free_limit_reached", "invalid_payment", "unsupported_network", "settlement_failed"])
def test_402_reasons(reason):
    body = {"error": "payment_required", "reason": reason, "message": f"m {reason}", "stripe": {"buy_url": "https://webextract.dev/#pricing"}}
    hdrs = {"x-payment-reason": reason, "payment-required": b64(PR), **({"x-free-remaining": "0"} if reason == "free_limit_reached" else {})}
    with pytest.raises(we.PaymentRequiredError) as ei:
        client(402, body, hdrs).extract("https://a.test/")
    e = ei.value
    assert isinstance(e, we.WebExtractError) and e.status == 402 and e.reason == reason and e.charged is False
    assert e.networks == ["eip155:8453", "eip155:137"] and e.payment_required["x402Version"] == 2
    assert e.buy_url == "https://webextract.dev/#pricing" and e.retryable == (reason == "settlement_failed") and e.hint
    assert e.to_dict()["reason"] == reason
    if reason == "free_limit_reached":
        assert e.free_remaining == 0


def test_402_body_only_and_no_credits():
    with pytest.raises(we.PaymentRequiredError) as ei:
        client(402, {"error": "payment_required", "reason": "x402_required", "x402": {"networks": ["eip155:10"]}}).extract("https://a.test/")
    assert ei.value.reason == "x402_required" and ei.value.networks == ["eip155:10"] and ei.value.payment_required is None
    with pytest.raises(we.PaymentRequiredError) as ei:
        client(402, {"error": "no_credits", "message": "Out of credits", "buy": "https://webextract.dev/#pricing"}, api_key="k").extract("https://a.test/")
    assert ei.value.reason == "no_credits" and ei.value.code == "no_credits" and ei.value.buy_url


@pytest.mark.parametrize("status,code,retryable", [(422, "upstream_error", False), (422, "blocked_by_site", False), (451, "robots_disallowed", False),
                                                   (422, "dns_failed", False), (502, "fetch_failed", True), (413, "too_large", False), (415, "unsupported_type", False)])
def test_target_fetch_errors(status, code, retryable):
    with pytest.raises(we.TargetFetchError) as ei:
        client(status, {"error": code, "message": "x; not charged", "charged": False}).extract("https://a.test/")
    assert ei.value.code == code and ei.value.status == status and ei.value.charged is False and ei.value.retryable == retryable


def test_other_statuses():
    with pytest.raises(we.InvalidRequestError):
        client(400, {"error": "forbidden_host", "message": "private"}).extract("https://a.test/")
    with pytest.raises(we.AuthenticationError) as ei:
        client(401, {"error": "invalid_api_key"}, api_key="lx_secret").extract("https://a.test/")
    assert "lx_secret" not in json.dumps(ei.value.to_dict())
    with pytest.raises(we.RateLimitError) as ei:
        client(429, {"error": "rate_limited", "message": "Sandbox limit"}, {"retry-after": "30"}).extract("https://a.test/")
    assert ei.value.retry_after == 30 and ei.value.retryable
    with pytest.raises(we.WebExtractError) as ei:
        client(500, "<html>oops", {"content-type": "text/html"}).extract("https://a.test/")
    assert ei.value.code == "http_500" and ei.value.retryable
    with pytest.raises(we.WebExtractError) as ei:
        client(200, "<html>", {"content-type": "text/html"}).extract("https://a.test/")
    assert ei.value.code == "invalid_response"


def test_connection_and_timeout_errors():
    def boom(req):
        raise httpx.ConnectError("refused")

    def slow(req):
        raise httpx.ReadTimeout("slow")
    with pytest.raises(we.ConnectionError) as ei:
        we.WebExtract(http_client=httpx.Client(transport=httpx.MockTransport(boom))).extract("https://a.test/")
    assert ei.value.code == "connection_error" and ei.value.retryable
    with pytest.raises(we.ConnectionError) as ei:
        we.WebExtract(http_client=httpx.Client(transport=httpx.MockTransport(slow))).extract("https://a.test/")
    assert ei.value.code == "timeout"


def test_duck_typed_sync_payment_client_like_requests_session():
    class Resp:
        status_code = 200
        headers = {"payment-response": b64({"transaction": "0xdef"})}
        text = json.dumps(EX)

        def json(self):
            return EX

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None, headers=None, timeout=None):
            self.calls.append((url, params, headers))
            return Resp()
    s = Session()
    r = we.WebExtract(payment_client=s).extract("https://a.test/")
    assert r.meta.payment_response["transaction"] == "0xdef" and s.calls[0][1] == {"url": "https://a.test/"}


def test_balance_no_billing_header():
    calls = []
    b = client(200, {"plan": "free", "free_remaining_today": 3}, None, calls).balance()
    assert b["free_remaining_today"] == 3 and calls[0].url.path == "/v1/balance" and "x-billing" not in calls[0].headers


def test_async_client():
    calls = []

    async def go():
        async with we.AsyncWebExtract(http_client=httpx.AsyncClient(transport=mock(200, EX, None, calls))) as c:
            r = await c.markdown("https://a.test/")
            return r
    r = asyncio.run(go())
    assert calls[0].url.path == "/v1/markdown" and calls[0].headers["x-billing"] == "free" and r.data["markdown"] == "# P"

    async def go402():
        c = we.AsyncWebExtract(http_client=httpx.AsyncClient(transport=mock(402, {"reason": "free_limit_reached"}, {"x-payment-reason": "free_limit_reached"})))
        await c.extract("https://a.test/")
    with pytest.raises(we.PaymentRequiredError) as ei:
        asyncio.run(go402())
    assert ei.value.reason == "free_limit_reached"


def test_env_api_key_used_when_no_explicit_key(monkeypatch):
    monkeypatch.setenv("WEBEXTRACT_API_KEY", " lx_env ")
    calls = []
    r = client(200, EX, None, calls).extract("https://a.test/")
    assert calls[0].headers["authorization"] == "Bearer lx_env" and "x-billing" not in calls[0].headers
    assert r.meta.billing == "key"
    calls = []
    client(200, EX, None, calls, billing="key").extract("https://a.test/")
    assert calls[0].headers["authorization"] == "Bearer lx_env"
    assert "lx_env" not in repr(client(200, EX))


def test_explicit_key_beats_env(monkeypatch):
    monkeypatch.setenv("WEBEXTRACT_API_KEY", "lx_env")
    calls = []
    client(200, EX, None, calls, api_key="lx_explicit").extract("https://a.test/")
    assert calls[0].headers["authorization"] == "Bearer lx_explicit"


def test_env_ignored_with_payment_client_or_non_key_billing(monkeypatch):
    monkeypatch.setenv("WEBEXTRACT_API_KEY", "lx_env")
    calls = []
    pay = httpx.Client(transport=mock(200, EX, None, calls))
    c = we.WebExtract(payment_client=pay)            # must not raise "not both"
    c.extract("https://a.test/")
    assert c.billing == "x402" and "authorization" not in calls[0].headers
    for billing in ("free", "x402-testnet"):
        calls = []
        kw = {"payment_client": httpx.Client(transport=mock(200, EX, None, calls))} if billing != "free" else {}
        c = we.WebExtract(billing=billing, http_client=httpx.Client(transport=mock(200, EX, None, calls)), **kw)
        c.extract("https://a.test/")
        assert c.billing == billing and "authorization" not in calls[0].headers and calls[0].headers["x-billing"] == billing


def test_empty_env_is_ignored(monkeypatch):
    monkeypatch.setenv("WEBEXTRACT_API_KEY", "  ")
    assert client(200, EX).billing == "free"
    with pytest.raises(TypeError, match="WEBEXTRACT_API_KEY"):
        we.WebExtract(billing="key")


def test_async_client_reads_env(monkeypatch):
    monkeypatch.setenv("WEBEXTRACT_API_KEY", "lx_env")
    calls = []

    async def go():
        c = we.AsyncWebExtract(http_client=httpx.AsyncClient(transport=mock(200, EX, None, calls)))
        await c.markdown("https://a.test/")
    asyncio.run(go())
    assert calls[0].headers["authorization"] == "Bearer lx_env"


def _seq(*responses, calls):
    it = iter(responses)

    def h(req):
        calls.append(req)
        status, body, hdrs = next(it)
        return httpx.Response(status, json=body, headers=hdrs)
    return httpx.MockTransport(h)


SETTLE_FAIL = (402, {"error": "payment_required", "reason": "settlement_failed", "message": "not settled", "retryable": True}, {"x-payment-reason": "settlement_failed"})


def test_settlement_failed_is_retried_once_by_default():
    calls = []
    pay = httpx.Client(transport=_seq(SETTLE_FAIL, (200, EX, {}), calls=calls))
    r = we.WebExtract(payment_client=pay).extract("https://a.test/")
    assert r.meta.status == 200 and len(calls) == 2


def test_settlement_retry_limit_and_opt_out():
    calls = []
    pay = httpx.Client(transport=_seq(SETTLE_FAIL, SETTLE_FAIL, calls=calls))
    with pytest.raises(we.PaymentRequiredError) as ei:
        we.WebExtract(payment_client=pay).extract("https://a.test/")
    assert ei.value.reason == "settlement_failed" and len(calls) == 2
    calls = []
    pay = httpx.Client(transport=_seq(SETTLE_FAIL, calls=calls))
    with pytest.raises(we.PaymentRequiredError):
        we.WebExtract(payment_client=pay, settlement_retries=0).extract("https://a.test/")
    assert len(calls) == 1
    with pytest.raises(TypeError):
        we.WebExtract(settlement_retries=-1)


def test_other_402_reasons_are_not_retried():
    calls = []
    pay = httpx.Client(transport=_seq((402, {"reason": "invalid_payment"}, {"x-payment-reason": "invalid_payment"}), calls=calls))
    with pytest.raises(we.PaymentRequiredError):
        we.WebExtract(payment_client=pay, settlement_retries=3).extract("https://a.test/")
    assert len(calls) == 1


def test_async_settlement_retry():
    calls = []

    async def go():
        c = we.AsyncWebExtract(payment_client=httpx.AsyncClient(transport=_seq(SETTLE_FAIL, (200, EX, {}), calls=calls)))
        return await c.markdown("https://a.test/")
    assert asyncio.run(go()).meta.status == 200 and len(calls) == 2
