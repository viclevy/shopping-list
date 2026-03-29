import asyncio

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from models import User
from web_search import search_images, suggest_product_info

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
    start: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
):
    """Search SerpAPI Google Shopping for product images."""
    return await asyncio.to_thread(search_images, q, start)
