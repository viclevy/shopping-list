import asyncio
import json
import os
import re

from typing import Dict, List, Optional

import httpx

from config import settings

_oauth_credentials = None


def _load_oauth_credentials() -> Optional[dict]:
    """Load OAuth 2.0 credentials from the client secret file."""
    global _oauth_credentials
    if _oauth_credentials is not None:
        return _oauth_credentials

    oauth_file = settings.google_client_secret_file
    if not oauth_file or not os.path.exists(oauth_file):
        _oauth_credentials = {}
        return _oauth_credentials

    try:
        with open(oauth_file) as f:
            data = json.load(f)
        _oauth_credentials = data.get("installed", {})
    except (json.JSONDecodeError, IOError):
        _oauth_credentials = {}

    return _oauth_credentials


async def _get_oauth_access_token(oauth_creds: dict) -> Optional[str]:
    """
    Get an OAuth 2.0 access token using refresh token flow.
    Returns None if credentials are incomplete or token refresh fails.
    """
    token_url = oauth_creds.get("token_uri")
    client_id = oauth_creds.get("client_id")
    client_secret = oauth_creds.get("client_secret")
    refresh_token = oauth_creds.get("refresh_token")

    if not all([token_url, client_id, client_secret, refresh_token]):
        return None

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(token_url, json=payload)
        if resp.status_code == 200:
            token_data = resp.json()
            return token_data.get("access_token")
    except Exception:
        pass

    return None


async def _get_search_headers_and_params(
    query: str, **extra_params
) -> tuple[Optional[dict], Optional[dict]]:
    """
    Build headers and params for Custom Search API request using OAuth 2.0.
    Returns (headers, params) or (None, None) if auth fails.
    """
    search_engine_id = settings.google_search_engine_id
    if not search_engine_id:
        return None, None

    oauth_creds = _load_oauth_credentials()
    if not oauth_creds:
        return None, None

    access_token = await _get_oauth_access_token(oauth_creds)
    if not access_token:
        return None, None

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "cx": search_engine_id,
        "q": query,
        **extra_params,
    }
    return headers, params


async def search_images(query: str, num: int = 8) -> List[dict]:
    """Search for images using Google Custom Search API."""
    headers, params = await _get_search_headers_and_params(
        query, searchType="image", num=min(num, 10)
    )
    if headers is None or params is None:
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
                headers=headers
            )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("items", []):
        results.append({
            "url": item.get("link", ""),
            "thumbnail": item.get("image", {}).get("thumbnailLink", ""),
            "title": item.get("title", ""),
        })
    return results


_CATEGORIES = [
    "Produce", "Dairy", "Meat", "Seafood", "Bakery", "Frozen",
    "Canned Goods", "Snacks", "Beverages", "Condiments", "Cereal",
    "Pasta", "Rice", "Spices", "Baking", "Deli", "Baby", "Pet",
    "Household", "Health", "Personal Care",
    "Fruits", "Vegetables", "Eggs", "Cheese", "Breakfast",
]

# Map variant terms found in search results to canonical category names
_CATEGORY_ALIASES = {
    "fruit": "Produce", "fruits": "Produce", "vegetable": "Produce",
    "vegetables": "Produce", "veggies": "Produce",
}

# Build word-boundary patterns for each category keyword
_CATEGORY_PATTERNS = {}
for _cat in _CATEGORIES:
    _CATEGORY_PATTERNS[_cat] = re.compile(r"\b" + re.escape(_cat.lower()) + r"\b")
for _alias, _canonical in _CATEGORY_ALIASES.items():
    _CATEGORY_PATTERNS[_alias] = re.compile(r"\b" + re.escape(_alias) + r"\b")


async def suggest_category_and_price(product_name: str) -> dict:
    """Suggest category and price for a product using Google Custom Search API."""
    cat_headers, cat_params = await _get_search_headers_and_params(
        f"{product_name} food category in one word", num=5
    )
    price_headers, price_params = await _get_search_headers_and_params(
        f"{product_name} grocery store price", num=3
    )

    if cat_headers is None or cat_params is None or price_headers is None or price_params is None:
        return {"category": None, "price": None}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            cat_resp, price_resp = await asyncio.gather(
                client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=cat_params,
                    headers=cat_headers
                ),
                client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=price_params,
                    headers=price_headers
                ),
            )
    except Exception:
        return {"category": None, "price": None}

    # Extract category using word-boundary matching
    category = None
    if cat_resp.status_code == 200:
        cat_data = cat_resp.json()
        # Count how many times each category appears across all snippets
        category_hits: Dict[str, int] = {}
        for item in cat_data.get("items", []):
            text = (item.get("snippet", "") + " " + item.get("title", "")).lower()
            for label, pattern in _CATEGORY_PATTERNS.items():
                if pattern.search(text):
                    canonical = _CATEGORY_ALIASES.get(label, label)
                    category_hits[canonical] = category_hits.get(canonical, 0) + 1
        if category_hits:
            category = max(category_hits, key=category_hits.get)

    # Extract price from snippets
    price = None
    if price_resp.status_code == 200:
        price_data = price_resp.json()
        price_pattern = re.compile(r"\$(\d+\.?\d{0,2})")
        for item in price_data.get("items", []):
            snippet = item.get("snippet", "")
            match = price_pattern.search(snippet)
            if match:
                price = float(match.group(1))
                break

    return {"category": category, "price": price}


async def download_image(url: str) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=15.0)
            if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
                return resp.content
    except Exception:
        pass
    return None
