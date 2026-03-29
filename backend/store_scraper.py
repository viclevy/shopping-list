"""
Store scraper module — fetches product prices and images from
Walmart and Target via public search endpoints.

No API keys required. Uses simple HTTP GET requests.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

import requests

_UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)
_UA_DESKTOP = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_TARGET_API_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"
_TARGET_STORE_ID = "3991"
_TIMEOUT = 12


# ── Walmart ──────────────────────────────────────────────────────────────────

def search_walmart(query: str) -> list[dict]:
    """Search Walmart. Returns list of product dicts."""
    url = f"https://www.walmart.com/search?q={quote_plus(query)}"
    try:
        resp = requests.get(url, headers={
            "User-Agent": _UA_MOBILE,
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=_TIMEOUT)
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    html = resp.text

    # Strategy 1: __NEXT_DATA__ JSON blob (cleanest)
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
    )
    if m:
        try:
            data = json.loads(m.group(1))
            stacks = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
            for stack in stacks:
                items = [i for i in stack.get("items", []) if i.get("__typename") == "Product"]
                if items:
                    return [_parse_walmart_item(i) for i in items]
        except (KeyError, IndexError, json.JSONDecodeError):
            pass

    # Strategy 2: extract Product objects embedded in JS bundles
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for script in scripts:
        if '{"__typename":"Product"' not in script:
            continue
        products = _extract_json_objects(script, '{"__typename":"Product"')
        if products:
            return [_parse_walmart_item(p) for p in products if p.get("__typename") == "Product"]

    return []


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
        "url": f"https://www.walmart.com/ip/{item.get('usItemId', '')}",
    }


# ── Target ───────────────────────────────────────────────────────────────────

def search_target(query: str) -> list[dict]:
    """Search Target via Redsky API. Returns list of product dicts."""
    url = (
        "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"
        f"?key={_TARGET_API_KEY}"
        f"&keyword={quote_plus(query)}"
        "&count=5"
        "&channel=WEB"
        f"&pricing_store_id={_TARGET_STORE_ID}"
        "&visitor_id=00000000005D01004BEDB747D78F3397"
        "&default_purchasability_filter=true"
        f"&page=%2Fs%2F{quote_plus(query)}"
    )
    try:
        resp = requests.get(url, headers={
            "User-Agent": _UA_DESKTOP,
            "Accept": "application/json",
        }, timeout=_TIMEOUT)
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    try:
        data = resp.json()
    except (ValueError, KeyError):
        return []

    products = data.get("data", {}).get("search", {}).get("products", [])
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
        "url": f"https://www.target.com/p/-/A-{tcin}",
    }


# ── Combined search ──────────────────────────────────────────────────────────

def search_stores(query: str) -> dict:
    """Search Walmart and Target in parallel. Returns {"walmart": [...], "target": [...]}."""
    results = {"walmart": [], "target": []}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(search_walmart, query): "walmart",
            pool.submit(search_target, query): "target",
        }
        for future in as_completed(futures):
            store = futures[future]
            try:
                results[store] = future.result()[:5]
            except Exception:
                results[store] = []
    return results


def search_images(query: str) -> list[dict]:
    """Search both stores and return a flat list of image dicts for selection."""
    store_results = search_stores(query)
    images = []
    for store_key in ("walmart", "target"):
        for item in store_results.get(store_key, [])[:3]:
            img = item.get("image", "")
            if img:
                images.append({
                    "url": img,
                    "name": item.get("name", ""),
                    "store": item.get("store", store_key.title()),
                })
    return images
