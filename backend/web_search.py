"""
Web search module using Gemini API for category suggestions
and SerpAPI Google Shopping for multi-store prices and images.

Runs both sources in parallel and merges results.
"""

import asyncio
import json
import re
from typing import Optional

import serpapi
from google import genai
from google.genai import types

from config import settings

_CATEGORIES = [
    "Produce", "Dairy", "Meat", "Seafood", "Bakery", "Frozen",
    "Canned Goods", "Snacks", "Beverages", "Condiments", "Cereal",
    "Pasta", "Rice", "Spices", "Baking", "Deli", "Baby", "Pet",
    "Household", "Health", "Personal Care",
    "Fruits", "Vegetables", "Eggs", "Cheese", "Breakfast",
]


def _get_client() -> Optional[genai.Client]:
    """Return a Gemini client, or None if no key configured."""
    if not settings.gemini_api_key:
        return None
    return genai.Client(api_key=settings.gemini_api_key)


def _query_gemini(product_name: str) -> dict:
    """Synchronous Gemini call. Returns {category, price, stores}."""
    client = _get_client()
    if client is None:
        return {"category": None, "price": None, "stores": []}

    prompt = f"""I need info about the grocery product "{product_name}".

Return ONLY a JSON object (no markdown, no backticks) with these fields:
- "category": one of {json.dumps(_CATEGORIES)}, or null if unsure
- "price": typical US retail price as a number (e.g. 3.99), or null if unsure
- "stores": list of major US store names where this product is commonly available (e.g. ["Walmart", "Target", "Kroger"]), up to 5 stores, or empty list if unsure

Example: {{"category": "Dairy", "price": 4.29, "stores": ["Walmart", "Kroger", "Target"]}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)

        category = data.get("category")
        if category and category not in _CATEGORIES:
            category = None

        price = data.get("price")
        if price is not None:
            try:
                price = round(float(price), 2)
            except (ValueError, TypeError):
                price = None

        stores = data.get("stores", [])
        if not isinstance(stores, list):
            stores = []
        stores = [s for s in stores if isinstance(s, str) and s.strip()][:5]

        return {"category": category, "price": price, "stores": stores}
    except Exception:
        return {"category": None, "price": None, "stores": []}


def _search_serpapi(product_name: str, start: int = 0) -> dict:
    """Call SerpAPI Google Shopping. Returns {store_prices, images, image_url}."""
    if not settings.serpapi_key:
        return {"store_prices": [], "images": [], "image_url": None}

    try:
        client = serpapi.Client(api_key=settings.serpapi_key)
        params = {
            "engine": "google_shopping",
            "q": product_name,
            "hl": "en",
            "gl": "us",
            "num": 10,
        }
        if start > 0:
            params["start"] = start
        results = client.search(params)
    except Exception:
        return {"store_prices": [], "images": [], "image_url": None}

    shopping = results.get("shopping_results", [])

    # Build store_prices — one per unique store, best match first
    seen_stores = set()
    store_prices = []
    for item in shopping:
        store = item.get("source", "")
        if not store or store in seen_stores:
            continue
        seen_stores.add(store)
        price = item.get("extracted_price")
        if price is None:
            continue
        store_prices.append({
            "store": store,
            "name": item.get("title", ""),
            "price": price,
            "price_display": item.get("price", ""),
            "image": item.get("thumbnail", ""),
            "id": item.get("product_id", ""),
            "url": item.get("product_link", ""),
        })
        if len(store_prices) >= 5:
            break

    # Build images list for ImageSearchPicker
    images = []
    for item in shopping[:6]:
        thumb = item.get("thumbnail", "")
        if thumb:
            images.append({
                "url": thumb,
                "name": item.get("title", ""),
                "store": item.get("source", ""),
            })

    image_url = images[0]["url"] if images else None
    return {"store_prices": store_prices, "images": images, "image_url": image_url}


def search_images(product_name: str, start: int = 0) -> list[dict]:
    """Search SerpAPI Google Shopping for product images."""
    result = _search_serpapi(product_name, start=start)
    return result["images"]


async def suggest_product_info(product_name: str) -> dict:
    """Suggest category, price, stores, and images using Gemini + SerpAPI.

    Runs both sources in parallel. Returns merged dict with keys:
        category, price, stores (from Gemini),
        store_prices, image_url, images (from SerpAPI).
    """
    gemini_task = asyncio.to_thread(_query_gemini, product_name)
    serpapi_task = asyncio.to_thread(_search_serpapi, product_name)

    gemini_result, serpapi_result = await asyncio.gather(
        gemini_task, serpapi_task, return_exceptions=True,
    )

    if isinstance(gemini_result, Exception):
        gemini_result = {"category": None, "price": None, "stores": []}
    if isinstance(serpapi_result, Exception):
        serpapi_result = {"store_prices": [], "images": [], "image_url": None}

    return {
        **gemini_result,
        "store_prices": serpapi_result["store_prices"],
        "image_url": serpapi_result["image_url"],
        "images": serpapi_result["images"],
    }
