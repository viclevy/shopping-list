"""
Web search module using Gemini API with Google Search grounding
and store scrapers (Walmart, Target) for prices and images.

Runs both sources in parallel and merges results.
"""

import asyncio
import json
import re
from typing import Optional

from google import genai
from google.genai import types

from config import settings
from store_scraper import search_stores

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


async def suggest_product_info(product_name: str) -> dict:
    """Suggest category, price, stores, and images using Gemini + store scrapers.

    Runs both sources in parallel. Returns merged dict with keys:
        category, price, stores (from Gemini),
        store_prices (from scrapers),
        image_url (best image from scrapers).
    """
    gemini_task = asyncio.to_thread(_query_gemini, product_name)
    scraper_task = asyncio.to_thread(search_stores, product_name)

    gemini_result, scraper_result = await asyncio.gather(
        gemini_task, scraper_task, return_exceptions=True,
    )

    # Handle failures gracefully
    if isinstance(gemini_result, Exception):
        gemini_result = {"category": None, "price": None, "stores": []}
    if isinstance(scraper_result, Exception):
        scraper_result = {"walmart": [], "target": []}

    # Build store_prices — first result from each store that has a price
    store_prices = []
    for store_key in ("walmart", "target"):
        items = scraper_result.get(store_key, [])
        for item in items[:1]:  # take best match from each store
            if item.get("price") is not None:
                store_prices.append(item)

    # Collect multiple images for selection (up to 3 per store)
    images = []
    for store_key in ("walmart", "target"):
        items = scraper_result.get(store_key, [])
        for item in items[:3]:
            img = item.get("image", "")
            if img:
                images.append({
                    "url": img,
                    "name": item.get("name", ""),
                    "store": item.get("store", store_key.title()),
                })

    # Pick best image: prefer Walmart (higher quality), fall back to Target
    image_url = images[0]["url"] if images else None

    return {
        **gemini_result,
        "store_prices": store_prices,
        "image_url": image_url,
        "images": images,
    }
