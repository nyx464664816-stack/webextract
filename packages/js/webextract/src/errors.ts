/** Error classes. Every error thrown by the client is a WebExtractError (or subclass).
 * `charged` is false whenever the API says so (failed fetches are never billed). */

export type PaymentReason =
  | "x402_required" | "x402_requested" | "free_limit_reached" | "invalid_payment"
  | "unsupported_network" | "settlement_failed" | "no_credits" | (string & {});

export interface WebExtractErrorInit {
  status: number;
  code: string;
  charged?: boolean | null;
  retryable?: boolean;
  body?: unknown;
  cause?: unknown;
}

export class WebExtractError extends Error {
  readonly status: number;
  readonly code: string;
  readonly charged: boolean | null;
  readonly retryable: boolean;
  readonly body: unknown;
  constructor(message: string, init: WebExtractErrorInit) {
    super(message, init.cause !== undefined ? { cause: init.cause } : undefined);
    this.name = "WebExtractError";
    this.status = init.status;
    this.code = init.code;
    this.charged = init.charged ?? null;
    this.retryable = init.retryable ?? false;
    this.body = init.body;
  }
  /** Compact, model-friendly description (used by the tool wrappers). */
  toJSON(): Record<string, unknown> {
    return { error: this.code, status: this.status, message: this.message, charged: this.charged, retryable: this.retryable };
  }
}

/** HTTP 402. `reason` explains why; `paymentRequired` is the decoded x402 PAYMENT-REQUIRED header (if any). */
export class PaymentRequiredError extends WebExtractError {
  readonly reason: PaymentReason;
  readonly paymentRequired: Record<string, unknown> | null;
  readonly networks: string[];
  readonly buyUrl: string | null;
  readonly freeRemaining: number | null;
  readonly hint: string;
  constructor(message: string, init: WebExtractErrorInit & {
    reason: PaymentReason; paymentRequired: Record<string, unknown> | null; networks: string[];
    buyUrl: string | null; freeRemaining: number | null; hint: string;
  }) {
    super(message, init);
    this.name = "PaymentRequiredError";
    this.reason = init.reason;
    this.paymentRequired = init.paymentRequired;
    this.networks = init.networks;
    this.buyUrl = init.buyUrl;
    this.freeRemaining = init.freeRemaining;
    this.hint = init.hint;
  }
  override toJSON() {
    return { ...super.toJSON(), reason: this.reason, hint: this.hint, networks: this.networks, buy_url: this.buyUrl, free_remaining: this.freeRemaining };
  }
}

/** The target page could not be fetched (robots.txt, HTTP error, blocked, DNS, timeout, too large, wrong type). Never charged. */
export class TargetFetchError extends WebExtractError {
  constructor(message: string, init: WebExtractErrorInit) { super(message, init); this.name = "TargetFetchError"; }
}
/** 400: missing/invalid url, forbidden (private) host, invalid billing mode. Never charged. */
export class InvalidRequestError extends WebExtractError {
  constructor(message: string, init: WebExtractErrorInit) { super(message, init); this.name = "InvalidRequestError"; }
}
/** 401: unknown API key. */
export class AuthenticationError extends WebExtractError {
  constructor(message: string, init: WebExtractErrorInit) { super(message, init); this.name = "AuthenticationError"; }
}
/** 429: rate limited (e.g. sandbox per-IP limits). */
export class RateLimitError extends WebExtractError {
  readonly retryAfter: number | null;
  constructor(message: string, init: WebExtractErrorInit & { retryAfter: number | null }) {
    super(message, init); this.name = "RateLimitError"; this.retryAfter = init.retryAfter;
  }
}
/** No HTTP response at all (network error, timeout, or the payment wrapper threw before sending). */
export class ConnectionError extends WebExtractError {
  constructor(message: string, init: WebExtractErrorInit) { super(message, init); this.name = "ConnectionError"; }
}

/** API error codes for target-page failures (from the server's ExtractError). */
export const TARGET_FETCH_CODES = new Set([
  "upstream_error", "blocked_by_site", "robots_disallowed", "dns_failed", "fetch_failed", "too_large", "unsupported_type",
]);

export const PAYMENT_HINTS: Record<string, string> = {
  x402_required: "No API key, payment or free opt-in. Use billing \"free\" (20 calls/day per IP), an apiKey (https://webextract.dev/#pricing), or a paymentFetch from @x402/fetch.",
  x402_requested: "x402 requested. Pass a paymentFetch (e.g. wrapFetchWithPayment from @x402/fetch) so the client can sign one of the PAYMENT-REQUIRED options.",
  free_limit_reached: "Free daily limit (20 calls/day per IP, shared with MCP) is used up. Buy credits at https://webextract.dev/#pricing or pay per call via x402 (USDC on Base and 6 other chains).",
  invalid_payment: "The x402 payment was rejected. Check the signer, network and USDC balance, then retry with a new payment.",
  unsupported_network: "The payment used a network/asset this endpoint does not accept. See `networks`.",
  settlement_failed: "Payment verified but settlement did not complete. Not charged. Retry with a freshly signed payment.",
  no_credits: "API key has no credits left. Top up at https://webextract.dev/#pricing.",
};
