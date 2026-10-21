/** Response types for https://api.webextract.dev (schema_version "1.0").
 * Fields marked "additive" were approved on 2026-10-21 (price provenance patch) and may be
 * absent on older deployments, so they are optional here. Never assume they exist. */

export type ContentSource = "raw_html" | "rendered";

export type UnresolvedReason =
  | "no_offer_in_structured_data" | "price_not_numeric" | "zero_price" | "js_rendered_suspected"
  | "template_placeholder" | "no_price_found" | "variant_not_matched" | "listing_page"
  | "no_product_markup" | "not_html" | (string & {});

export interface Unresolved { reason: UnresolvedReason; detail?: string | null }

export interface VariantRef {
  id?: string | null; sku?: string | null; name?: string | null;
  attributes?: Record<string, unknown> | null; url?: string | null;
  match?: "offer_url" | "offer_sku" | "shopify_variant_id" | "url_param+dom_selected" | "dom_selected" | (string & {});
}

export interface PriceItem {
  type: "list" | "sale" | "installment" | "current" | (string & {});
  /** Always > 0. A missing price is reported via `unresolved`, never as 0. */
  amount: number;
  amount_high?: number | null;
  currency: string | null;
  variant?: VariantRef | null;
  installment?: Record<string, unknown> | null;
  method?: "json-ld" | "opengraph" | "microdata" | "heuristic" | "dom" | "shopify_meta" | (string & {});
  evidence?: string | null;
}

export interface PriceDetail {
  status: "resolved" | "partial" | "unresolved";
  currency?: string | null;
  currency_basis?: "declared" | "symbol" | null;
  prices: PriceItem[];
  range?: { low: number; high?: number | null; currency?: string | null; basis?: string; offer_count?: number | null } | null;
  selected_variant?: VariantRef | null;
  variants?: Array<{ id?: string | null; sku?: string | null; name?: string | null; attributes?: Record<string, unknown> | null;
    url?: string | null; amount?: number | null; currency?: string | null; availability?: string | null; source?: string | null; evidence?: string | null }>;
  unresolved?: Unresolved | null;
  warnings?: string[];
}

export interface Product {
  name: string | null; brand: string | null; sku: string | null; gtin: string | null;
  description: string | null; image: string | null;
  /** Legacy flat price. Prefer `price_detail` when present. Can be null. */
  price: number | null; price_high: number | null; currency: string | null;
  availability: string | null; rating: { value?: number; count?: number } | null;
  /** Extraction method for the flat fields (json-ld | opengraph | microdata | heuristic). Not the content source. */
  source: string | null;
  /** additive (2026-10-21) */
  price_detail?: PriceDetail;
  [k: string]: unknown;
}

export interface Metadata {
  title: string | null; description: string | null; authors: string[];
  published_at: string | null; modified_at: string | null; site_name: string | null;
  language: string | null; canonical_url: string | null; image: string | null; type: string | null;
}

export interface Table {
  index: number; caption: string | null; headers: string[]; rows: string[][];
  checks: { row_count: number; column_count: number; consistent_width: boolean };
}

export interface ExtractResult {
  url: string; final_url: string; fetched_at: string; schema_version: string;
  markdown: string; markdown_truncated?: boolean; word_count?: number;
  metadata: Metadata; product: Product | null; tables: Table[];
  /** additive (2026-10-21): raw_html today; rendered only once ?render=1 ships */
  content_source?: ContentSource;
  /** additive (2026-10-21): only when product is null, e.g. { reason: "listing_page" } */
  product_unresolved?: Unresolved | null;
  billing_note?: string;
  [k: string]: unknown;
}

export interface MarkdownResult {
  url: string; final_url: string; fetched_at?: string; title: string | null;
  markdown: string; markdown_truncated?: boolean; word_count?: number;
  /** additive (2026-10-21) */
  content_source?: ContentSource;
  [k: string]: unknown;
}

export interface BalanceResult { plan?: string; credits?: number; free_remaining_today?: number; [k: string]: unknown }

/** Billing facts read from response headers. */
export interface ResponseMeta {
  status: number;
  /** How this client asked to be billed. */
  billing: Billing;
  freeRemaining: number | null;
  creditsCharged: number | null;
  creditsRemaining: number | null;
  sandbox: boolean;
  /** Decoded x402 PAYMENT-RESPONSE header (settlement receipt) when a payment settled. */
  paymentResponse: Record<string, unknown> | null;
}

export interface WebExtractResponse<T> { data: T; meta: ResponseMeta }

/** key = Bearer API key (Stripe credits); free = X-Billing: free; x402 = pay per call through `paymentFetch`;
 * x402-testnet = sandbox (Base Sepolia test USDC only, through `paymentFetch`). */
export type Billing = "key" | "free" | "x402" | "x402-testnet";
