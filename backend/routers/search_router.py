import asyncio

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from models import User
from store_scraper import search_images
from web_search import suggest_product_info

router = APIRouter()


@router.get("/suggest")
async def proxy_suggest(
    q: str = Query(...),
    _user: User = Depends(get_current_user),
):
    return await suggest_product_info(q)


@router.get("/images")
async def image_search(
    q: str = Query(...),
    _user: User = Depends(get_current_user),
):
    """Search store scrapers for product images."""
    return await asyncio.to_thread(search_images, q)
