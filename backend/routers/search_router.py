import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Store, User
from web_search import search_images, suggest_product_info

router = APIRouter()


def _get_store_names(db: Session) -> list[str]:
    """Fetch store names for image search (where include_in_image_search is True)."""
    return [s.name for s in db.query(Store.name).filter(Store.include_in_image_search == True).order_by(Store.name).all()]


@router.get("/suggest")
async def proxy_suggest(
    q: str = Query(...),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store_names = _get_store_names(db)
    return await suggest_product_info(q, store_names=store_names)


@router.get("/images")
async def image_search(
    q: str = Query(...),
    start: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search SerpAPI Google Shopping for product images."""
    store_names = _get_store_names(db)
    return await asyncio.to_thread(search_images, q, start, store_names)
