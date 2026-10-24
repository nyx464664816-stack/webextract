"""Sync and async clients for https://api.webextract.dev. The package never handles private keys:
x402 signing happens inside the ``payment_client`` you pass (e.g. ``x402HttpxClient``)."""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Generic, Literal, Optional, TypeVar
from urllib.parse import urlsplit

import httpx

from ._errors import (
    AuthenticationError, ConnectionError, InvalidRequestError, PaymentRequiredError, RateLimitError,
    TargetFetchError, TARGET_FETCH_CODES, WebExtractError,
)

__version__ = "0.1.1"
ENV_API_KEY = "WEBEXTRACT_API_KEY"
DEFAULT_BASE_URL = "https://api.webextract.dev"
Billing = Literal["key", "free", "x402", "x402-testnet"]
T = TypeVar("T")
_PROTECTED = {"authorization", "x-billing", "payment-signature", "x-payment"}


@dataclass
class ResponseMeta:
    status: int
    billing: str
    free_remaining: Optional[int]
    credits_charged: Optional[float]
    credits_remaining: Optional[float]
    sandbox: bool
    payment_response: Optional[Dict[str, Any]]


@dataclass
class WebExtractResponse(Generic[T]):
    data: T
    meta: ResponseMeta


def _num(v: Optional[str]) -> Optional[float]:
    if v is None or not v.strip():
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _b64json(v: Optional[str]) -> Optional[Dict[str, Any]]:
    if not v:
        return None
    try:
        o = json.loads(base64.b64decode(v))
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def _check_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise InvalidRequestError("url is required", status=0, code="missing_url", charged=False)
    u = url.strip()
    parts = urlsplit(u)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise InvalidRequestError("url must be an absolute http(s) URL", status=0, code="invalid_url", charged=False)
    return u


def error_from_response(res: Any) -> WebExtractError:
    """Map an error response (httpx or requests) to a WebExtractError subclass."""
    status = res.status_code
    try:
        body = res.json()
    except Exception:
        body = None
    if not isinstance(body, dict):
        body = None
    code = (body or {}).get("error") if isinstance((body or {}).get("error"), str) else f"http_{status}"
    message = (body or {}).get("message") or (res.text[:200] if body is None and res.text else f"HTTP {status}")
    charged = (body or {}).get("charged") if isinstance((body or {}).get("charged"), bool) else False
    if status == 402:
        reason = res.headers.get("x-payment-reason") or (body or {}).get("reason") or ("no_credits" if code == "no_credits" else "x402_required")
        pr = _b64json(res.headers.get("payment-required"))
        accepts = pr.get("accepts") if isinstance(pr, dict) and isinstance(pr.get("accepts"), list) else []
        networks = list(dict.fromkeys(a.get("network") for a in accepts if isinstance(a, dict) and a.get("network")))
        if not networks:
            networks = list(((body or {}).get("x402") or {}).get("networks") or [])
        fr = _num(res.headers.get("x-free-remaining"))
        return PaymentRequiredError(
            message, status=status, code="payment_required" if code == "http_402" else code, charged=False,
            retryable=reason == "settlement_failed", body=body, reason=reason, payment_required=pr, networks=networks,
            buy_url=((body or {}).get("stripe") or {}).get("buy_url") or (body or {}).get("buy"),
            free_remaining=int(fr) if fr is not None else None)
    if code in TARGET_FETCH_CODES or status == 451:
        return TargetFetchError(message, status=status, code=code, charged=False, retryable=code == "fetch_failed", body=body)
    if status == 400:
        return InvalidRequestError(message, status=status, code=code, charged=False, body=body)
    if status == 401:
        return AuthenticationError(message, status=status, code=code, charged=False, body=body)
    if status == 429:
        return RateLimitError(message, status=status, code=code, charged=False, retryable=True, body=body,
                              retry_after=_num(res.headers.get("retry-after")))
    return WebExtractError(message, status=status, code=code, charged=charged, retryable=status >= 500, body=body)


class _Base:
    def __init__(self, *, api_key: Optional[str], billing: Optional[Billing], payment_client: Any,
                 http_client: Any, base_url: Optional[str], timeout: float,
                 headers: Optional[Dict[str, str]], settlement_retries: int = 1) -> None:
        if api_key is not None and (not isinstance(api_key, str) or not api_key.strip()):
            raise TypeError("api_key must be a non-empty string")
        if api_key is None and payment_client is None and billing in (None, "key"):
            # Fallback only: an explicit api_key wins; with payment_client or a non-key billing the env var is ignored.
            env_key = os.environ.get(ENV_API_KEY, "").strip()
            api_key = env_key or None
        if api_key and payment_client is not None:
            raise TypeError("pass either api_key or payment_client, not both (a Bearer key always wins on the server)")
        self.billing: str = billing or ("key" if api_key else "x402" if payment_client is not None else "free")
        if self.billing == "key" and not api_key:
            raise TypeError(f'billing "key" needs api_key (or the {ENV_API_KEY} environment variable)')
        if self.billing in ("x402", "x402-testnet") and payment_client is None:
            raise TypeError(f'billing "{self.billing}" needs payment_client (e.g. x402HttpxClient from the x402 SDK)')
        if self.billing != "key" and api_key:
            raise TypeError(f'billing "{self.billing}" cannot be combined with api_key')
        if self.billing not in ("key", "free", "x402", "x402-testnet"):
            raise TypeError(f"unknown billing {self.billing!r}")
        self._api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        if not isinstance(settlement_retries, int) or settlement_retries < 0:
            raise TypeError("settlement_retries must be an int >= 0")
        self.settlement_retries = settlement_retries
        self._extra = {k: v for k, v in (headers or {}).items() if k.lower() not in _PROTECTED}
        self._transport_client = payment_client if payment_client is not None else http_client

    def __repr__(self) -> str:  # never show the key
        return f"{type(self).__name__}(base_url={self.base_url!r}, billing={self.billing!r})"

    def _headers(self, billing_header: bool = True) -> Dict[str, str]:
        h = {"accept": "application/json", "user-agent": f"webextract-python/{__version__}", **self._extra}
        if self._api_key:
            h["authorization"] = f"Bearer {self._api_key}"
        if billing_header and self.billing in ("free", "x402-testnet"):
            h["x-billing"] = self.billing
        return h

    def _should_retry(self, e: WebExtractError, attempt: int) -> bool:
        # settlement_failed = payment verified but not settled; the API says "not charged, retry with a new payment".
        # Only this reason is retried automatically; the payment client signs a fresh payload on the new request.
        return isinstance(e, PaymentRequiredError) and e.reason == "settlement_failed" and attempt < self.settlement_retries

    def _parse(self, res: Any) -> WebExtractResponse[Dict[str, Any]]:
        if 200 <= res.status_code < 300:
            try:
                data = res.json()
            except Exception:
                data = None
            if not isinstance(data, dict):
                raise WebExtractError("response was not JSON", status=res.status_code, code="invalid_response", body=res.text[:500])
            fr = _num(res.headers.get("x-free-remaining"))
            return WebExtractResponse(data=data, meta=ResponseMeta(
                status=res.status_code, billing=self.billing, free_remaining=int(fr) if fr is not None else None,
                credits_charged=_num(res.headers.get("x-credits-charged")),
                credits_remaining=_num(res.headers.get("x-credits-remaining")),
                sandbox=res.headers.get("x-sandbox") == "true",
                payment_response=_b64json(res.headers.get("payment-response"))))
        raise error_from_response(res)


def _wrap_exc(e: Exception) -> ConnectionError:
    timed_out = isinstance(e, httpx.TimeoutException) or "Timeout" in type(e).__name__
    msg = "request timed out" if timed_out else f"request failed before a response: {type(e).__name__}: {e}"
    err = ConnectionError(msg, status=0, code="timeout" if timed_out else "connection_error", charged=None, retryable=True)
    err.__cause__ = e
    return err


class WebExtract(_Base):
    """Synchronous client. ``payment_client`` may be any object with a requests/httpx-style
    ``get(url, params=, headers=, timeout=)``, e.g. the ``requests.Session`` returned by
    ``x402.http.clients.x402_requests(x402_client)`` (the x402 SDK has no sync httpx client).

    >>> WebExtract().markdown("https://example.com").data["markdown"]  # free tier (X-Billing: free)
    """

    def __init__(self, *, api_key: Optional[str] = None, billing: Optional[Billing] = None,
                 payment_client: Any = None, http_client: Optional[httpx.Client] = None,
                 base_url: Optional[str] = None, timeout: float = 60.0, headers: Optional[Dict[str, str]] = None,
                 settlement_retries: int = 1) -> None:
        super().__init__(api_key=api_key, billing=billing, payment_client=payment_client, http_client=http_client,
                         base_url=base_url, timeout=timeout, headers=headers, settlement_retries=settlement_retries)
        self._owned = self._transport_client is None
        self._http: httpx.Client = self._transport_client or httpx.Client(timeout=timeout)

    def extract(self, url: str) -> WebExtractResponse[Dict[str, Any]]:
        """GET /v1/extract: Markdown + fixed-schema JSON. $0.005 or 1 credit."""
        return self._get("/v1/extract", {"url": _check_url(url)})

    def markdown(self, url: str) -> WebExtractResponse[Dict[str, Any]]:
        """GET /v1/markdown: Markdown only. $0.002 or 0.4 credit."""
        return self._get("/v1/markdown", {"url": _check_url(url)})

    def balance(self) -> Dict[str, Any]:
        """GET /v1/balance: credits, or free calls left today for this IP. Never charged."""
        return self._get("/v1/balance", None, billing_header=False).data

    def _get(self, path: str, params: Optional[Dict[str, str]], billing_header: bool = True) -> WebExtractResponse[Dict[str, Any]]:
        attempt = 0
        while True:
            try:
                res = self._http.get(self.base_url + path, params=params, headers=self._headers(billing_header), timeout=self.timeout)
            except Exception as e:
                raise _wrap_exc(e) from e
            try:
                return self._parse(res)
            except WebExtractError as e:
                if not self._should_retry(e, attempt):
                    raise
                attempt += 1

    def close(self) -> None:
        if self._owned:
            self._http.close()

    def __enter__(self) -> "WebExtract":
        return self

    def __exit__(self, *a: Any) -> None:
        self.close()


class AsyncWebExtract(_Base):
    """Async client. For x402 pass ``payment_client=x402HttpxClient(x402_client)`` from the official x402 SDK."""

    def __init__(self, *, api_key: Optional[str] = None, billing: Optional[Billing] = None,
                 payment_client: Optional[httpx.AsyncClient] = None, http_client: Optional[httpx.AsyncClient] = None,
                 base_url: Optional[str] = None, timeout: float = 60.0, headers: Optional[Dict[str, str]] = None,
                 settlement_retries: int = 1) -> None:
        super().__init__(api_key=api_key, billing=billing, payment_client=payment_client, http_client=http_client,
                         base_url=base_url, timeout=timeout, headers=headers, settlement_retries=settlement_retries)
        self._owned = self._transport_client is None
        self._http: httpx.AsyncClient = self._transport_client or httpx.AsyncClient(timeout=timeout)

    async def extract(self, url: str) -> WebExtractResponse[Dict[str, Any]]:
        return await self._get("/v1/extract", {"url": _check_url(url)})

    async def markdown(self, url: str) -> WebExtractResponse[Dict[str, Any]]:
        return await self._get("/v1/markdown", {"url": _check_url(url)})

    async def balance(self) -> Dict[str, Any]:
        return (await self._get("/v1/balance", None, billing_header=False)).data

    async def _get(self, path: str, params: Optional[Dict[str, str]], billing_header: bool = True) -> WebExtractResponse[Dict[str, Any]]:
        attempt = 0
        while True:
            try:
                res = await self._http.get(self.base_url + path, params=params, headers=self._headers(billing_header), timeout=self.timeout)
            except Exception as e:
                raise _wrap_exc(e) from e
            try:
                return self._parse(res)
            except WebExtractError as e:
                if not self._should_retry(e, attempt):
                    raise
                attempt += 1

    async def aclose(self) -> None:
        if self._owned:
            await self._http.aclose()

    async def __aenter__(self) -> "AsyncWebExtract":
        return self

    async def __aexit__(self, *a: Any) -> None:
        await self.aclose()
