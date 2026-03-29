#!/usr/bin/env python3
"""
POC: Scrape product prices and images from Walmart and Target.
No API keys required — uses public search endpoints with simple HTTP GET.

Usage:
    python3 store_scraper_poc.py "Lactaid Lactose Free 2% Reduced Fat Milk"
    python3 store_scraper_poc.py   # runs all 3 test products
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

import requests

UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)
UA_DESKTOP = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

TARGET_API_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"
TARGET_STORE_ID = "3991"


# ── Walmart ──────────────────────────────────────────────────────────────────

def search_walmart(query: str) -> list[dict]:
    """Search Walmart via their search page. Returns list of product dicts."""
    url = f"https://www.walmart.com/search?q={quote_plus(query)}"
    try:
        resp = requests.get(url, headers={
            "User-Agent": UA_MOBILE,
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=15)
    except requests.RequestException as e:
        return [{"error": f"Request failed: {e}"}]

    if resp.status_code != 200:
        return [{"error": f"HTTP {resp.status_code}"}]

    html = resp.text

    # Strategy 1: __NEXT_DATA__ (cleanest, available when no CAPTCHA)
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
    )
    if m:
        data = json.loads(m.group(1))
        try:
            stacks = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
            for stack in stacks:
                items = [i for i in stack.get("items", []) if i.get("__typename") == "Product"]
                if items:
                    return [_parse_walmart_item(i) for i in items]
        except (KeyError, IndexError):
            pass

    # Strategy 2: extract Product objects from embedded JS (works even with CAPTCHA overlay)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for script in scripts:
        if '{"__typename":"Product"' not in script:
            continue
        products = _extract_json_objects(script, '{"__typename":"Product"')
        if products:
            return [_parse_walmart_item(p) for p in products if p.get("__typename") == "Product"]

    return [{"error": "No product data found (blocked or layout change)"}]


def _extract_json_objects(text: str, marker: str) -> list[dict]:
    """Extract JSON objects starting with `marker` from a JS string."""
    results = []
    start_pos = 0
    while True:
        idx = text.find(marker, start_pos)
        if idx < 0:
            break
        depth = 0
        i = idx
        in_string = False
        prev_backslash = False
        while i < len(text):
            c = text[i]
            if in_string:
                if prev_backslash:
                    prev_backslash = False
                elif c == "\\":
                    prev_backslash = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            results.append(json.loads(text[idx : i + 1]))
                        except json.JSONDecodeError:
                            pass
                        break
            i += 1
        start_pos = idx + 1
    return results


def _parse_walmart_item(item: dict) -> dict:
    pi = item.get("priceInfo", {})
    img = item.get("image", "")
    if img and "?" not in img:
        img += "?odnHeight=400&odnWidth=400&odnBg=FFFFFF"
    return {
        "store": "Walmart",
        "name": item.get("name", ""),
        "price": item.get("price"),
        "price_display": pi.get("linePrice", ""),
        "image": img,
        "id": item.get("usItemId", ""),
        "rating": item.get("averageRating"),
        "url": f"https://www.walmart.com/ip/{item.get('usItemId', '')}",
    }


# ── Target ───────────────────────────────────────────────────────────────────

def search_target(query: str) -> list[dict]:
    """Search Target via their Redsky API. Returns list of product dicts."""
    url = (
        "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"
        f"?key={TARGET_API_KEY}"
        f"&keyword={quote_plus(query)}"
        "&count=5"
        "&channel=WEB"
        f"&pricing_store_id={TARGET_STORE_ID}"
        "&visitor_id=00000000005D01004BEDB747D78F3397"
        "&default_purchasability_filter=true"
        f"&page=%2Fs%2F{quote_plus(query)}"
    )
    try:
        resp = requests.get(url, headers={
            "User-Agent": UA_DESKTOP,
            "Accept": "application/json",
        }, timeout=15)
    except requests.RequestException as e:
        return [{"error": f"Request failed: {e}"}]

    if resp.status_code != 200:
        return [{"error": f"HTTP {resp.status_code}"}]

    data = resp.json()
    products = data.get("data", {}).get("search", {}).get("products", [])
    if not products:
        return [{"error": "No products in response"}]

    return [_parse_target_item(p) for p in products]


def _parse_target_item(item: dict) -> dict:
    desc = item.get("item", {}).get("product_description", {})
    price = item.get("price", {})
    imgs = item.get("item", {}).get("enrichment", {}).get("images", {})
    img = imgs.get("primary_image_url", "")
    if img and "?" not in img:
        img += "?wid=400&hei=400&fmt=webp"
    tcin = item.get("tcin", "")
    return {
        "store": "Target",
        "name": desc.get("title", ""),
        "price": price.get("reg_retail"),
        "price_display": price.get("formatted_current_price", ""),
        "image": img,
        "id": tcin,
        "rating": (
            item.get("ratings_and_reviews", {})
            .get("statistics", {})
            .get("rating", {})
            .get("average")
        ),
        "url": f"https://www.target.com/p/-/A-{tcin}",
    }


# ── Combined Search ──────────────────────────────────────────────────────────

def search_product(query: str) -> dict:
    """Search both stores in parallel and return combined results."""
    results = {"query": query, "walmart": [], "target": []}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(search_walmart, query): "walmart",
            pool.submit(search_target, query): "target",
        }
        for future in as_completed(futures):
            store = futures[future]
            try:
                results[store] = future.result()[:5]
            except Exception as e:
                results[store] = [{"error": str(e)}]

    return results


# ── CLI ──────────────────────────────────────────────────────────────────────

def print_results(results: dict):
    print(f"\n{'='*70}")
    print(f"  QUERY: {results['query']}")
    print(f"{'='*70}")

    for store_key in ("walmart", "target"):
        items = results[store_key]
        store_name = store_key.upper()
        print(f"\n  ┌─ {store_name} {'─'*(60 - len(store_name))}")

        if not items or (items and "error" in items[0]):
            err = items[0]["error"] if items else "No results"
            print(f"  │  ERROR: {err}")
            print(f"  └{'─'*65}")
            continue

        for i, item in enumerate(items[:3], 1):
            price = item.get("price_display") or f"${item.get('price', '?')}"
            print(f"  │  {i}. {item['name'][:55]}")
            print(f"  │     Price: {price}")
            print(f"  │     Image: {item.get('image', 'N/A')[:70]}")
            print(f"  │     URL:   {item.get('url', '')}")
            if i < min(3, len(items)):
                print(f"  │")

        print(f"  └{'─'*65}")


def main():
    test_products = [
        "Lactaid Lactose Free 2% Reduced Fat Milk",
        "Hass Avocado",
        "Edge Sensitive Skin Shave Gel",
    ]

    if len(sys.argv) > 1:
        queries = [" ".join(sys.argv[1:])]
    else:
        queries = test_products

    for query in queries:
        results = search_product(query)
        print_results(results)


if __name__ == "__main__":
    main()
