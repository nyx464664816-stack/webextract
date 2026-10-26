"""Independent ground truth: fetch each page directly (not through WebExtract) and read facts from the raw HTML with BeautifulSoup.
   python ground_truth.py  -> results/ground_truth.json"""
import json, requests
from bs4 import BeautifulSoup
from common import *
out = {}
for u in URLS:
    r = requests.get(u["url"], headers={"User-Agent": UA}, timeout=30); soup = BeautifulSoup(r.content, "lxml")
    h1 = soup.find("h1"); tabs = []
    for t in soup.find_all("table"):
        rows = [tr for tr in t.find_all("tr") if tr.find("td")]
        if rows: tabs.append({"rows": len(rows), "cells": [norm(td.get_text()) for tr in rows[:2] for td in tr.find_all("td")][:6]})
    gt = {"status": r.status_code, "title": norm(soup.title.get_text()) if soup.title else None, "h1": norm(h1.get_text()) if h1 else None, "tables": tabs}
    ps = [norm(x.get_text()) for x in soup.find_all("p")]; ps = [x for x in ps if len(x) >= 40]
    gt["p_longest"] = max(ps, key=len)[:50] if ps else None   # first 50 characters of the longest paragraph: should appear in the Markdown
    if u["id"] == "books-product":
        gt["product_name"] = gt["h1"]; gt["price"] = float(norm(soup.select_one("p.price_color").get_text()).lstrip("£"))
    if u["id"] == "wsio-product":
        gt["product_name"] = norm(soup.select_one("h4.title").get_text()); gt["price"] = float(norm(soup.select_one("h4.price").get_text()).lstrip("$").replace(",", ""))
    out[u["id"]] = gt; print(u["id"], gt["status"], gt["title"], "| h1:", gt["h1"], "| tables:", [t["rows"] for t in tabs])
json.dump(out, open(RES / "ground_truth.json", "w"), indent=1, ensure_ascii=False)
