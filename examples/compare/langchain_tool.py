"""WebExtract as LangChain tools (REST, no extra SDK): one tool returns Markdown, one returns structured product/table fields.

    pip install langchain-core requests
    python langchain_tool.py [page-url]        # calls both tools directly, no LLM key needed

Give the tools to any tool-calling chat model:  model.bind_tools([webextract_markdown, webextract_extract])
(or langgraph's create_react_agent(model, [webextract_markdown, webextract_extract])). Free tier unless WEBEXTRACT_KEY is set."""
import json, os, sys, requests
from langchain_core.tools import tool

BASE = os.environ.get("WEBEXTRACT_BASE", "https://api.webextract.dev")
def _get(path: str, url: str) -> dict:
    h = {"Authorization": f"Bearer {os.environ['WEBEXTRACT_KEY']}"} if os.environ.get("WEBEXTRACT_KEY") else {"X-Billing": "free"}
    if os.environ.get("WEBEXTRACT_UA"): h["User-Agent"] = os.environ["WEBEXTRACT_UA"]
    r = requests.get(f"{BASE}{path}", params={"url": url}, headers=h, timeout=60)
    if r.status_code == 402: return {"error": "payment_required (free limit reached): use WEBEXTRACT_KEY or x402", "detail": r.text[:300]}
    r.raise_for_status(); return r.json()

@tool
def webextract_markdown(url: str) -> str:
    """Fetch a public web page and return its main content as clean Markdown. Cheapest option; use it when you only need to read the text."""
    d = _get("/v1/markdown", url); return d.get("markdown") or json.dumps(d)

@tool
def webextract_extract(url: str) -> str:
    """Fetch a public web page and return JSON: markdown plus product (name, price, currency, availability), tables and metadata. Use it when you need fields, not prose."""
    d = _get("/v1/extract", url)
    return json.dumps({k: d.get(k) for k in ("final_url", "metadata", "product", "tables", "word_count", "error")}, ensure_ascii=False)

if __name__ == "__main__":
    page = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    print("tool schema the model sees:", json.dumps(webextract_extract.args_schema.model_json_schema() if hasattr(webextract_extract.args_schema, "model_json_schema") else webextract_extract.args_schema, ensure_ascii=False))
    print("\n--- webextract_markdown ---\n" + webextract_markdown.invoke({"url": page})[:400])
    data = json.loads(webextract_extract.invoke({"url": page}))
    print("\n--- webextract_extract ---"); print(json.dumps({"product": {k: (data.get("product") or {}).get(k) for k in ("name", "price", "currency", "availability")}, "title": (data.get("metadata") or {}).get("title")}, ensure_ascii=False))
