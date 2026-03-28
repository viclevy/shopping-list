"""Test for Google Custom Search API using OAuth 2.0 client credentials."""

import asyncio
import json
import os
import sys
from typing import Optional

# Add backend directory to path so we can import config, etc.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

from config import settings

TEST_PRODUCTS = [
    ("Hass Avocado", "Produce"),
    ("Lactaid Milk", "Dairy"),
]


def load_oauth_credentials() -> Optional[dict]:
    """Load OAuth 2.0 credentials from client secret JSON file."""
    secret_file = settings.google_client_secret_file
    if not secret_file or not os.path.exists(secret_file):
        print(f"ERROR: Client secret file not found: {secret_file!r}")
        print("Set GOOGLE_CLIENT_SECRET_FILE in .env")
        return None

    with open(secret_file) as f:
        data = json.load(f)

    return data.get("installed")


async def get_oauth_access_token(oauth_creds: dict) -> Optional[str]:
    """
    Get an OAuth 2.0 access token via refresh token flow.

    For installed/desktop apps, this requires a refresh token from a previous
    authorization code flow. If you don't have a refresh token yet, run the
    authorization code flow first to get one.
    """
    token_url = oauth_creds.get("token_uri")
    client_id = oauth_creds.get("client_id")
    client_secret = oauth_creds.get("client_secret")
    refresh_token = oauth_creds.get("refresh_token")

    if not all([token_url, client_id, client_secret]):
        print("ERROR: Missing required OAuth fields (token_uri, client_id, client_secret)")
        return None

    if not refresh_token:
        print("ERROR: No refresh_token found in OAuth credentials.")
        print("Note: For desktop apps, you need to complete the authorization code flow first.")
        print("See: https://developers.google.com/identity/protocols/oauth2/native-app")
        return None

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(token_url, json=payload)

    if resp.status_code != 200:
        print(f"ERROR: Failed to get access token (status {resp.status_code})")
        print(f"Response: {resp.text}")
        return None

    token_data = resp.json()
    return token_data.get("access_token")


async def test_api_connectivity(oauth_creds: dict) -> bool:
    """Test that OAuth 2.0 credentials work with the Custom Search API."""
    access_token = await get_oauth_access_token(oauth_creds)

    if not access_token:
        print("  OAuth connectivity: FAILED (could not obtain access token)")
        return False

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "cx": settings.google_search_engine_id,
        "q": "test",
        "num": 1,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            headers=headers
        )

    if resp.status_code == 200:
        print(f"  OAuth API connectivity: OK (status {resp.status_code})")
        return True
    else:
        data = resp.json()
        error = data.get("error", {})
        print(f"  OAuth API connectivity: FAILED (status {resp.status_code})")
        print(f"  Error: {error.get('message', resp.text)}")
        return False


async def test_search_images(query: str, oauth_creds: dict) -> bool:
    """Test image search using OAuth 2.0 credentials."""
    access_token = await get_oauth_access_token(oauth_creds)
    if not access_token:
        print(f"  Image search for '{query}': Could not get token, skipping...")
        return False

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "cx": settings.google_search_engine_id,
        "q": query,
        "searchType": "image",
        "num": 3,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            headers=headers
        )

    if resp.status_code != 200:
        print(f"  Image search for '{query}': FAILED (status {resp.status_code})")
        return False

    data = resp.json()
    items = data.get("items", [])

    if items:
        print(f"  Image search for '{query}': OK ({len(items)} results)")
        for item in items[:2]:
            print(f"    - {item.get('title', 'N/A')}")
        return True
    else:
        print(f"  Image search for '{query}': No results found")
        return False


async def test_category_search(
    product_name: str, expected_category: str, oauth_creds: dict
) -> bool:
    """Test category suggestion using OAuth 2.0 credentials."""
    access_token = await get_oauth_access_token(oauth_creds)
    if not access_token:
        print(f"  Category search for '{product_name}': Could not get token, skipping...")
        return False

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "cx": settings.google_search_engine_id,
        "q": f"{product_name} food category in one word",
        "num": 5,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            headers=headers
        )

    if resp.status_code != 200:
        print(f"  Category search for '{product_name}': FAILED (status {resp.status_code})")
        return False

    data = resp.json()
    items = data.get("items", [])

    if not items:
        print(f"  {product_name}: No results found")
        return False

    snippets = " ".join([item.get("snippet", "") for item in items])
    match = "OK" if expected_category.lower() in snippets.lower() else "PARTIAL"
    print(f"  {product_name}: {match} (expected: {expected_category})")
    if items:
        print(f"    Sample result: {items[0].get('title', 'N/A')}")

    return True


async def main():
    print("=== Google Custom Search API - OAuth 2.0 Test ===\n")

    # 1. Load credentials
    print("1. Loading OAuth 2.0 credentials...")
    print(f"   Client secret file: {settings.google_client_secret_file}")
    print(f"   Search Engine ID:   {settings.google_search_engine_id}")

    if not settings.google_search_engine_id:
        print("ERROR: GOOGLE_SEARCH_ENGINE_ID not set in .env")
        sys.exit(1)

    oauth_creds = load_oauth_credentials()
    if not oauth_creds:
        sys.exit(1)

    print(f"   Client ID: {oauth_creds.get('client_id', '')[:20]}...")
    if not oauth_creds.get("refresh_token"):
        print("   ⚠ Warning: No refresh_token — complete authorization code flow first")
    print()

    # 2. Test API connectivity
    print("2. Testing OAuth API connectivity...")
    await test_api_connectivity(oauth_creds)
    print()

    # 3. Test image search
    print("3. Testing image search...")
    await test_search_images("apple", oauth_creds)
    print()

    # 4. Test category suggestions
    print("4. Testing category suggestions...")
    for product_name, expected in TEST_PRODUCTS:
        await test_category_search(product_name, expected, oauth_creds)
    print()

    print("✓ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
