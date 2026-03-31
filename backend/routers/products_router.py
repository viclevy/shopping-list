from datetime import datetime
from typing import List

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
from models import HistoryEvent, Product, ProductPhoto, ProductStore, ShoppingListItem, Store, User
from photo_utils import delete_photo, save_photo, save_photo_from_url
from schemas import ProductCreate, ProductRead, ProductStoreRead, ProductUpdate, StorePriceByName

router = APIRouter()


def _product_to_read(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        name=product.name,
        category=product.category,
        image_url=product.image_url,
        photos=product.photos,
        stores=[
            ProductStoreRead(
                store_id=ps.store_id,
                store_name=ps.store.name,
                price=ps.price,
            )
            for ps in product.stores
        ],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("", response_model=List[ProductRead])
def list_products(
    q: str = Query(None),
    sort: str = Query("name"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Product).options(
        joinedload(Product.photos),
        joinedload(Product.stores).joinedload(ProductStore.store),
    )
    if q:
        query = query.filter(Product.name.ilike("%%%s%%" % q))
    if sort == "newest":
        products = query.order_by(Product.created_at.desc()).all()
    else:
        products = query.order_by(Product.name).all()
    # Deduplicate due to joinedload
    seen = set()
    result = []
    for p in products:
        if p.id not in seen:
            seen.add(p.id)
            result.append(_product_to_read(p))
    return result


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .options(
            joinedload(Product.photos),
            joinedload(Product.stores).joinedload(ProductStore.store),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_read(product)


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = Product(name=body.name, category=body.category)
    db.add(product)
    db.flush()

    if body.store_ids:
        for store_id in body.store_ids:
            price = body.prices.get(store_id) if body.prices else None
            db.add(ProductStore(product_id=product.id, store_id=store_id, price=price))

    db.commit()
    db.refresh(product)
    return get_product(product.id, db, _user)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if body.name is not None:
        product.name = body.name
    if body.category is not None:
        product.category = body.category
    product.updated_at = datetime.utcnow()

    if body.store_ids is not None:
        # Remove old associations
        db.query(ProductStore).filter(ProductStore.product_id == product_id).delete()
        for store_id in body.store_ids:
            price = body.prices.get(store_id) if body.prices else None
            db.add(ProductStore(product_id=product_id, store_id=store_id, price=price))

    db.commit()
    return get_product(product_id, db, _user)


@router.post("/{product_id}/photos", response_model=ProductRead)
async def upload_photo(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    file_bytes = await file.read()
    filename = save_photo(file_bytes, file.filename or "photo.jpg")

    photo = ProductPhoto(
        product_id=product_id,
        filename=filename,
        original_name=file.filename,
    )
    db.add(photo)
    db.add(HistoryEvent(
        product_id=product_id,
        action="photo_added",
        user_id=user.id,
        details=f"Photo uploaded: {file.filename or 'photo.jpg'}",
    ))
    db.commit()
    return get_product(product_id, db, user)


@router.delete("/{product_id}/photos/{photo_id}", status_code=204)
def remove_photo(
    product_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    photo = (
        db.query(ProductPhoto)
        .filter(ProductPhoto.id == photo_id, ProductPhoto.product_id == product_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    delete_photo(photo.filename)
    db.delete(photo)
    db.commit()


@router.post("/{product_id}/photos/from-url", response_model=ProductRead)
def add_photo_from_url(
    product_id: int,
    url: str = Body(..., embed=True),
    set_primary: bool = Body(False, embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        filename = save_photo_from_url(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to download image")

    if set_primary:
        db.query(ProductPhoto).filter(
            ProductPhoto.product_id == product_id
        ).update({"is_primary": False})

    photo = ProductPhoto(
        product_id=product_id,
        filename=filename,
        original_name=url.split("/")[-1][:100],
        is_primary=set_primary,
    )
    db.add(photo)
    db.add(HistoryEvent(
        product_id=product_id,
        action="photo_added",
        user_id=user.id,
        details=f"Photo from URL: {url[:200]}",
    ))
    db.commit()
    return get_product(product_id, db, user)


@router.put("/{product_id}/photos/{photo_id}/primary", response_model=ProductRead)
def set_primary_photo(
    product_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    photo = (
        db.query(ProductPhoto)
        .filter(ProductPhoto.id == photo_id, ProductPhoto.product_id == product_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Unset all others, set this one
    db.query(ProductPhoto).filter(
        ProductPhoto.product_id == product_id
    ).update({"is_primary": False})
    photo.is_primary = True
    db.commit()
    return get_product(product_id, db, _user)


@router.post("/{product_id}/store-prices")
def save_store_prices(
    product_id: int,
    prices: List[StorePriceByName],
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for sp in prices:
        store = db.query(Store).filter(Store.name.ilike(sp.store_name)).first()
        if not store:
            continue
        existing = db.query(ProductStore).filter(
            ProductStore.product_id == product_id,
            ProductStore.store_id == store.id,
        ).first()
        if existing:
            existing.price = sp.price
        else:
            db.add(ProductStore(product_id=product_id, store_id=store.id, price=sp.price))

    db.commit()
    return {"status": "ok"}


@router.get("/{product_id}/delete-preview")
def delete_preview(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    history_count = db.query(HistoryEvent).filter(HistoryEvent.product_id == product_id).count()
    list_count = db.query(ShoppingListItem).filter(ShoppingListItem.product_id == product_id).count()
    photo_count = db.query(ProductPhoto).filter(ProductPhoto.product_id == product_id).count()
    return {
        "product": {"id": product.id, "name": product.name},
        "history_events": history_count,
        "list_items": list_count,
        "photos": photo_count,
    }


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .options(joinedload(Product.photos))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Delete photo files from disk
    for photo in product.photos:
        delete_photo(photo.filename)
    db.delete(product)
    db.commit()
