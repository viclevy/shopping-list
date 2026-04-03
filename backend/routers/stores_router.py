from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
from models import HistoryEvent, Product, ProductStore, Store, StoreAlias, User
from schemas import StoreAliasRead, StoreCreate, StoreRead


router = APIRouter()


@router.get("/{store_id}/delete-preview")
def delete_preview(
    store_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    history_count = db.query(HistoryEvent).filter(HistoryEvent.store_id == store_id).count()
    product_link_count = db.query(ProductStore).filter(ProductStore.store_id == store_id).count()
    return {
        "store": {"id": store.id, "name": store.name},
        "history_events": history_count,
        "product_links": product_link_count,
    }


@router.get("", response_model=List[StoreRead])
def list_stores(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Store).options(joinedload(Store.aliases)).order_by(Store.name).all()


@router.post("", response_model=StoreRead, status_code=201)
def create_store(
    body: StoreCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if db.query(Store).filter(Store.name == body.name).first():
        raise HTTPException(status_code=409, detail="Store already exists")
    store = Store(name=body.name, include_in_image_search=body.include_in_image_search)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.patch("/{store_id}", response_model=StoreRead)
def update_store(
    store_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    store = db.query(Store).options(joinedload(Store.aliases)).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if "include_in_image_search" in body:
        store.include_in_image_search = body["include_in_image_search"]

    db.commit()
    db.refresh(store)
    return store


@router.delete("/{store_id}", status_code=204)
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    db.query(HistoryEvent).filter(HistoryEvent.store_id == store_id).delete()
    db.delete(store)
    db.commit()


# --- Aliases ---

@router.get("/{store_id}/aliases", response_model=List[StoreAliasRead])
def list_aliases(
    store_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return db.query(StoreAlias).filter(StoreAlias.store_id == store_id).all()


@router.post("/{store_id}/aliases", response_model=StoreAliasRead, status_code=201)
def add_alias(
    store_id: int,
    alias: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    # Check uniqueness against both store names and existing aliases
    if db.query(Store).filter(Store.name.ilike(alias)).first():
        raise HTTPException(status_code=409, detail="Alias conflicts with an existing store name")
    if db.query(StoreAlias).filter(StoreAlias.alias.ilike(alias)).first():
        raise HTTPException(status_code=409, detail="Alias already exists")
    sa = StoreAlias(store_id=store_id, alias=alias)
    db.add(sa)
    db.commit()
    db.refresh(sa)
    return sa


@router.delete("/{store_id}/aliases/{alias_id}", status_code=204)
def remove_alias(
    store_id: int,
    alias_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    sa = db.query(StoreAlias).filter(
        StoreAlias.id == alias_id, StoreAlias.store_id == store_id
    ).first()
    if not sa:
        raise HTTPException(status_code=404, detail="Alias not found")
    db.delete(sa)
    db.commit()


# --- Merge ---

@router.post("/{store_id}/merge/{other_store_id}", response_model=StoreRead)
def merge_stores(
    store_id: int,
    other_store_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Merge other_store into store_id. Moves all references and adds other's name as alias."""
    keeper = db.query(Store).options(joinedload(Store.aliases)).filter(Store.id == store_id).first()
    if not keeper:
        raise HTTPException(status_code=404, detail="Target store not found")
    other = db.query(Store).filter(Store.id == other_store_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="Store to merge not found")
    if store_id == other_store_id:
        raise HTTPException(status_code=400, detail="Cannot merge a store with itself")

    # Move ProductStore links (skip duplicates)
    for ps in db.query(ProductStore).filter(ProductStore.store_id == other_store_id).all():
        existing = db.query(ProductStore).filter(
            ProductStore.product_id == ps.product_id,
            ProductStore.store_id == store_id,
        ).first()
        if existing:
            if ps.price is not None and existing.price is None:
                existing.price = ps.price
            db.delete(ps)
        else:
            ps.store_id = store_id

    # Move HistoryEvent references
    db.query(HistoryEvent).filter(HistoryEvent.store_id == other_store_id).update(
        {"store_id": store_id}, synchronize_session="fetch"
    )

    # Move favorite_store_id references
    db.query(Product).filter(Product.favorite_store_id == other_store_id).update(
        {"favorite_store_id": store_id}, synchronize_session="fetch"
    )

    # Add the other store's name as alias (if not already an alias or the keeper's name)
    if other.name.lower() != keeper.name.lower():
        existing_alias = db.query(StoreAlias).filter(StoreAlias.alias.ilike(other.name)).first()
        if not existing_alias:
            db.add(StoreAlias(store_id=store_id, alias=other.name))

    # Move other store's aliases to keeper
    for alias in db.query(StoreAlias).filter(StoreAlias.store_id == other_store_id).all():
        if alias.alias.lower() != keeper.name.lower():
            existing = db.query(StoreAlias).filter(
                StoreAlias.store_id == store_id, StoreAlias.alias.ilike(alias.alias)
            ).first()
            if not existing:
                alias.store_id = store_id
            else:
                db.delete(alias)
        else:
            db.delete(alias)

    db.delete(other)
    db.commit()
    db.refresh(keeper)
    return keeper
