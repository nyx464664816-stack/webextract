"""WebExtract: web page to clean Markdown + fixed-schema JSON for AI agents (https://webextract.dev)."""
from ._client import (
    DEFAULT_BASE_URL, ENV_API_KEY, AsyncWebExtract, ResponseMeta, WebExtract, WebExtractResponse, __version__, error_from_response,
)
from ._errors import (
    PAYMENT_HINTS, TARGET_FETCH_CODES, AuthenticationError, ConnectionError, InvalidRequestError, PaymentRequiredError,
    RateLimitError, TargetFetchError, WebExtractError,
)

TOOL_DESCRIPTIONS = {
    "extract_url": "Fetch a public web page (robots.txt respected) and return clean Markdown plus fixed-schema JSON: article metadata, product/price (with price_detail when available; a missing price is never reported as 0), and tables. Paid per call (USDC on Base and 6 other chains via x402, or prepaid credits); free tier 20 calls/day per IP.",
    "page_markdown": "Fetch a public web page (robots.txt respected) and return clean Markdown only. Cheaper than extract_url. Use it when you only need the text.",
    "url": "Public http(s) URL of the page to read",
}

__all__ = [
    "WebExtract", "AsyncWebExtract", "ENV_API_KEY", "WebExtractResponse", "ResponseMeta", "DEFAULT_BASE_URL", "__version__",
    "error_from_response", "WebExtractError", "PaymentRequiredError", "TargetFetchError", "InvalidRequestError",
    "AuthenticationError", "RateLimitError", "ConnectionError", "PAYMENT_HINTS", "TARGET_FETCH_CODES", "TOOL_DESCRIPTIONS",
]
