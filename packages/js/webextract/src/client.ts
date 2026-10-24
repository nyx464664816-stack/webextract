import {
  WebExtractError, PaymentRequiredError, TargetFetchError, InvalidRequestError, AuthenticationError,
  RateLimitError, ConnectionError, TARGET_FETCH_CODES, PAYMENT_HINTS, type PaymentReason,
} from "./errors.js";
import type { Billing, ExtractResult, MarkdownResult, BalanceResult, ResponseMeta, WebExtractResponse } from "./types.js";

export const VERSION = "0.1.1";
export const DEFAULT_BASE_URL = "https://api.webextract.dev";
export const ENV_API_KEY = "WEBEXTRACT_API_KEY";

/** Reads WEBEXTRACT_API_KEY where a `process.env` exists (Node, Bun, Deno with --allow-env); undefined elsewhere. */
function envApiKey(): string | undefined {
  try {
    const v = (globalThis as any).process?.env?.[ENV_API_KEY];
    return typeof v === "string" && v.trim() ? v.trim() : undefined;
  } catch { return undefined; }
}

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface WebExtractOptions {
  /** Prepaid API key (Stripe credits), sent as Authorization: Bearer. Never logged. */
  apiKey?: string;
  /** An x402-capable fetch, e.g. `wrapFetchWithPayment(fetch, client)` from @x402/fetch.
   * The package never sees your private key: signing happens inside this function. */
  paymentFetch?: FetchLike;
  /** How to bill. Default: "key" with apiKey, "x402" with paymentFetch, otherwise "free".
   * "x402-testnet" = sandbox (Base Sepolia test USDC only; needs paymentFetch). */
  billing?: Billing;
  /** Plain transport override (tests, proxies). Has no billing meaning. */
  fetch?: FetchLike;
  baseUrl?: string;
  /** Per-request timeout in ms (default 60000). */
  timeoutMs?: number;
  /** Extra headers (e.g. a custom User-Agent suffix). Billing/auth headers cannot be overridden here. */
  headers?: Record<string, string>;
  /** Automatic retries when the API answers 402 settlement_failed (payment verified, not settled, not charged).
   * The paymentFetch signs a fresh payment on the new request. Default 1. Other errors are never retried. */
  settlementRetries?: number;
}

export interface RequestOptions { signal?: AbortSignal; timeoutMs?: number }

const num = (v: string | null): number | null => {
  if (v === null || v.trim() === "") return null;
  const n = Number(v); return Number.isFinite(n) ? n : null;
};
const b64json = (v: string | null): Record<string, unknown> | null => {
  if (!v) return null;
  try {
    const txt = typeof atob === "function" ? new TextDecoder().decode(Uint8Array.from(atob(v), c => c.charCodeAt(0))) : "";
    const o = JSON.parse(txt); return o && typeof o === "object" ? o : null;
  } catch { return null; }
};

export class WebExtract {
  readonly baseUrl: string;
  readonly billing: Billing;
  readonly #apiKey: string | undefined;
  readonly #fetch: FetchLike;
  readonly #timeoutMs: number;
  readonly #headers: Record<string, string>;

  readonly settlementRetries: number;

  constructor(opts: WebExtractOptions = {}) {
    // WEBEXTRACT_API_KEY is a fallback only: explicit apiKey wins; ignored with paymentFetch or a non-"key" billing.
    if (opts.apiKey === undefined && !opts.paymentFetch && (opts.billing === undefined || opts.billing === "key")) {
      const k = envApiKey(); if (k) opts = { ...opts, apiKey: k };
    }
    if (opts.apiKey && opts.paymentFetch) throw new TypeError("WebExtract: pass either apiKey or paymentFetch, not both (a Bearer key always wins on the server, so the payment would never be used).");
    if (opts.apiKey !== undefined && (typeof opts.apiKey !== "string" || !opts.apiKey.trim())) throw new TypeError("WebExtract: apiKey must be a non-empty string");
    this.billing = opts.billing ?? (opts.apiKey ? "key" : opts.paymentFetch ? "x402" : "free");
    if (this.billing === "key" && !opts.apiKey) throw new TypeError(`WebExtract: billing "key" needs apiKey (or the ${ENV_API_KEY} environment variable)`);
    if ((this.billing === "x402" || this.billing === "x402-testnet") && !opts.paymentFetch)
      throw new TypeError(`WebExtract: billing "${this.billing}" needs paymentFetch (e.g. wrapFetchWithPayment from @x402/fetch)`);
    if (this.billing !== "key" && opts.apiKey) throw new TypeError(`WebExtract: billing "${this.billing}" cannot be combined with apiKey`);
    this.#apiKey = opts.apiKey;
    const f = opts.paymentFetch ?? opts.fetch ?? (globalThis.fetch as FetchLike | undefined);
    if (!f) throw new TypeError("WebExtract: no fetch available (Node >= 18 required, or pass `fetch`)");
    this.#fetch = f;
    this.baseUrl = (opts.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.#timeoutMs = opts.timeoutMs ?? 60_000;
    this.#headers = { ...(opts.headers ?? {}) };
    const sr = opts.settlementRetries ?? 1;
    if (!Number.isInteger(sr) || sr < 0) throw new TypeError("WebExtract: settlementRetries must be an integer >= 0");
    this.settlementRetries = sr;
  }

  /** GET /v1/extract: Markdown + fixed-schema JSON (metadata, product/price, tables). $0.005 or 1 credit. */
  extract(url: string, opts?: RequestOptions): Promise<WebExtractResponse<ExtractResult>> {
    return this.#call<ExtractResult>("/v1/extract", url, opts);
  }
  /** GET /v1/markdown: clean Markdown only. $0.002 or 0.4 credit. */
  markdown(url: string, opts?: RequestOptions): Promise<WebExtractResponse<MarkdownResult>> {
    return this.#call<MarkdownResult>("/v1/markdown", url, opts);
  }
  /** GET /v1/balance: credits for the key, or free calls left today for this IP. Free, never charged. */
  async balance(opts?: RequestOptions): Promise<BalanceResult> {
    const res = await this.#send(`${this.baseUrl}/v1/balance`, this.#authHeaders(false), opts, this.#fetch);
    return (await this.#handle<BalanceResult>(res)).data;
  }

  #authHeaders(billingHeader = true): Record<string, string> {
    const h: Record<string, string> = { accept: "application/json", "user-agent": `webextract-js/${VERSION}`, ...this.#headers };
    for (const k of Object.keys(h)) if (/^(authorization|x-billing|payment-signature|x-payment)$/i.test(k)) delete h[k];
    if (this.#apiKey) h.authorization = `Bearer ${this.#apiKey}`;
    if (billingHeader) {
      if (this.billing === "free") h["x-billing"] = "free";
      else if (this.billing === "x402-testnet") h["x-billing"] = "x402-testnet";
      // "x402": no header -> server answers 402 x402_required with PAYMENT-REQUIRED, paymentFetch signs and retries.
    }
    return h;
  }

  async #call<T>(path: string, url: string, opts?: RequestOptions): Promise<WebExtractResponse<T>> {
    if (typeof url !== "string" || !url.trim()) throw new InvalidRequestError("url is required", { status: 0, code: "missing_url", charged: false });
    let parsed: URL;
    try { parsed = new URL(url.trim()); } catch { throw new InvalidRequestError("url is not a valid absolute URL", { status: 0, code: "invalid_url", charged: false }); }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") throw new InvalidRequestError("only http/https URLs are supported", { status: 0, code: "invalid_url", charged: false });
    const endpoint = `${this.baseUrl}${path}?${new URLSearchParams({ url: url.trim() })}`;
    for (let attempt = 0; ; attempt++) {
      const res = await this.#send(endpoint, this.#authHeaders(), opts, this.#fetch);
      try { return await this.#handle<T>(res); }
      catch (e) {
        if (e instanceof PaymentRequiredError && e.reason === "settlement_failed" && attempt < this.settlementRetries) continue;
        throw e;
      }
    }
  }

  async #send(endpoint: string, headers: Record<string, string>, opts: RequestOptions | undefined, f: FetchLike): Promise<Response> {
    const timeout = AbortSignal.timeout(opts?.timeoutMs ?? this.#timeoutMs);
    const signal = opts?.signal ? AbortSignal.any([opts.signal, timeout]) : timeout;
    try {
      return await f(endpoint, { method: "GET", headers, signal });
    } catch (e) {
      const name = (e as Error)?.name;
      const timedOut = name === "TimeoutError" || (name === "AbortError" && timeout.aborted);
      const msg = timedOut ? "request timed out" : `request failed before a response: ${(e as Error)?.message ?? String(e)}`;
      throw new ConnectionError(msg, { status: 0, code: timedOut ? "timeout" : "connection_error", charged: null, retryable: true, cause: e });
    }
  }

  async #handle<T>(res: Response): Promise<WebExtractResponse<T>> {
    const text = await res.text();
    let body: any = null;
    try { body = text ? JSON.parse(text) : null; } catch { body = null; }
    if (res.ok) {
      if (body === null || typeof body !== "object") throw new WebExtractError("response was not JSON", { status: res.status, code: "invalid_response", body: text.slice(0, 500) });
      const meta: ResponseMeta = {
        status: res.status, billing: this.billing,
        freeRemaining: num(res.headers.get("x-free-remaining")),
        creditsCharged: num(res.headers.get("x-credits-charged")),
        creditsRemaining: num(res.headers.get("x-credits-remaining")),
        sandbox: res.headers.get("x-sandbox") === "true",
        paymentResponse: b64json(res.headers.get("payment-response")),
      };
      return { data: body as T, meta };
    }
    throw toError(res, body, text);
  }
}

export function toError(res: Response, body: any, text = ""): WebExtractError {
  const status = res.status;
  const code: string = (body && typeof body.error === "string" && body.error) || `http_${status}`;
  const message: string = (body && typeof body.message === "string" && body.message) || (text && !body ? text.slice(0, 200) : `HTTP ${status}`);
  const charged = body && typeof body.charged === "boolean" ? body.charged : status >= 400 ? false : null;
  if (status === 402) {
    const reason: PaymentReason = res.headers.get("x-payment-reason") || body?.reason || (code === "no_credits" ? "no_credits" : "x402_required");
    const pr = b64json(res.headers.get("payment-required"));
    const accepts = Array.isArray((pr as any)?.accepts) ? (pr as any).accepts : [];
    const networks: string[] = accepts.length ? [...new Set<string>(accepts.map((a: any) => a?.network).filter(Boolean))]
      : Array.isArray(body?.x402?.networks) ? body.x402.networks : [];
    return new PaymentRequiredError(message, {
      status, code: code === `http_402` ? "payment_required" : code, charged: false,
      retryable: reason === "settlement_failed", body, reason, paymentRequired: pr, networks,
      buyUrl: body?.stripe?.buy_url ?? body?.buy ?? null,
      freeRemaining: num(res.headers.get("x-free-remaining")),
      hint: PAYMENT_HINTS[reason] ?? "Payment required.",
    });
  }
  if (TARGET_FETCH_CODES.has(code) || status === 451) return new TargetFetchError(message, { status, code, charged: false, retryable: code === "fetch_failed", body });
  if (status === 400) return new InvalidRequestError(message, { status, code, charged: false, body });
  if (status === 401) return new AuthenticationError(message, { status, code, charged: false, body });
  if (status === 429) return new RateLimitError(message, { status, code, charged: false, retryable: true, body, retryAfter: num(res.headers.get("retry-after")) });
  return new WebExtractError(message, { status, code, charged, retryable: status >= 500, body });
}
