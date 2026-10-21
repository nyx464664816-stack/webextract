"""Error classes. Every error raised by the client is a WebExtractError (or subclass)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

TARGET_FETCH_CODES = frozenset({
    "upstream_error", "blocked_by_site", "robots_disallowed", "dns_failed", "fetch_failed", "too_large", "unsupported_type",
})

PAYMENT_HINTS: Dict[str, str] = {
    "x402_required": 'No API key, payment or free opt-in. Use billing="free" (50 calls/day per IP), an api_key (https://webextract.dev/#pricing), or a payment_client from the x402 SDK.',
    "x402_requested": "x402 requested. Pass a payment_client (e.g. x402HttpxClient) so one of the PAYMENT-REQUIRED options can be signed.",
    "free_limit_reached": "Free daily limit (50 calls/day per IP, shared with MCP) is used up. Buy credits at https://webextract.dev/#pricing or pay per call via x402 (USDC on Base and 6 other chains).",
    "invalid_payment": "The x402 payment was rejected. Check the signer, network and USDC balance, then retry with a new payment.",
    "unsupported_network": "The payment used a network/asset this endpoint does not accept. See `networks`.",
    "settlement_failed": "Payment verified but settlement did not complete. Not charged. Retry with a freshly signed payment.",
    "no_credits": "API key has no credits left. Top up at https://webextract.dev/#pricing.",
}


class WebExtractError(Exception):
    """Base error. ``charged`` is False whenever the API says so (failed fetches are never billed)."""

    def __init__(self, message: str, *, status: int, code: str, charged: Optional[bool] = None,
                 retryable: bool = False, body: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.charged = charged
        self.retryable = retryable
        self.body = body

    def to_dict(self) -> Dict[str, Any]:
        """Compact, model-friendly description (used by the LangChain tools)."""
        return {"error": self.code, "status": self.status, "message": self.message,
                "charged": self.charged, "retryable": self.retryable}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status}, code={self.code!r}, message={self.message!r})"


class PaymentRequiredError(WebExtractError):
    """HTTP 402. ``reason`` explains why; ``payment_required`` is the decoded PAYMENT-REQUIRED header."""

    def __init__(self, message: str, *, reason: str, payment_required: Optional[Dict[str, Any]],
                 networks: List[str], buy_url: Optional[str], free_remaining: Optional[int], **kw: Any) -> None:
        super().__init__(message, **kw)
        self.reason = reason
        self.payment_required = payment_required
        self.networks = networks
        self.buy_url = buy_url
        self.free_remaining = free_remaining
        self.hint = PAYMENT_HINTS.get(reason, "Payment required.")

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "reason": self.reason, "hint": self.hint, "networks": self.networks,
                "buy_url": self.buy_url, "free_remaining": self.free_remaining}


class TargetFetchError(WebExtractError):
    """The target page could not be fetched (robots.txt, HTTP error, blocked, DNS, timeout, size, type). Never charged."""


class InvalidRequestError(WebExtractError):
    """400: missing/invalid url, private host, invalid billing mode. Never charged."""


class AuthenticationError(WebExtractError):
    """401: unknown API key."""


class RateLimitError(WebExtractError):
    """429: rate limited (e.g. sandbox per-IP limits)."""

    def __init__(self, message: str, *, retry_after: Optional[float], **kw: Any) -> None:
        super().__init__(message, **kw)
        self.retry_after = retry_after


class ConnectionError(WebExtractError):  # noqa: A001 - deliberate, namespaced as webextract.ConnectionError
    """No HTTP response (network error, timeout, or the payment client raised before sending)."""
