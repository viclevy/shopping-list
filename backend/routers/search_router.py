from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from google_search import download_image, search_images, suggest_category_and_price
from models import Product, ProductPhoto, User
from photo_utils import save_photo

router = APIRouter()


@router.get("/images")
async def proxy_image_search(
    q: str = Query(...),
    _user: User = Depends(get_current_user),
):
    results = await search_images(q)
    return {"results": results}


@router.get("/suggest")
async def proxy_suggest(
    q: str = Query(...),
    _user: User = Depends(get_current_user),
):
    suggestions = await suggest_category_and_price(q)
    return suggestions


class DownloadImageRequest(BaseModel):
    url: str
    product_id: int


@router.post("/images/download")
async def proxy_download_image(
    body: DownloadImageRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == body.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    image_bytes = await download_image(body.url)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Failed to download image")

    filename = save_photo(image_bytes, "google_image.jpg")
    photo = ProductPhoto(
        product_id=body.product_id,
        filename=filename,
        original_name="google_image.jpg",
    )
    db.add(photo)
    db.commit()
    return {"filename": filename, "photo_id": photo.id}
