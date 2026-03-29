from typing import List

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
from models import (
    HistoryEvent,
    Product,
    ProductStore,
    ShoppingListItem,
    User,
)
from schemas import (
    CheckOffRequest,
    ProductRead,
    ProductStoreRead,
    ShoppingListItemCreate,
    ShoppingListItemRead,
    ShoppingListItemUpdate,
)

router = APIRouter()

# Will be set from main.py after websocket_manager is created
ws_manager = None


def _item_to_read(item: ShoppingListItem, last_price_map: dict = None) -> ShoppingListItemRead:
    product = item.product
    lp = (last_price_map or {}).get(product.id)
    return ShoppingListItemRead(
        id=item.id,
        product=ProductRead(
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
        ),
        quantity=item.quantity,
        unit=item.unit,
        added_by=item.user.username,
        added_at=item.added_at,
        last_price=lp[0] if lp else None,
        last_store_id=lp[1] if lp else None,
    )


def _last_price_for(db: Session, product_id: int) -> dict:
    event = (
        db.query(HistoryEvent)
        .filter(
            HistoryEvent.product_id == product_id,
            HistoryEvent.action == "checked_off",
            HistoryEvent.price.isnot(None),
        )
        .order_by(HistoryEvent.timestamp.desc())
        .first()
    )
    if event:
        return {product_id: (event.price, event.store_id)}
    return {}


def _get_all_items(db: Session) -> List[ShoppingListItemRead]:
    items = (
        db.query(ShoppingListItem)
        .options(
            joinedload(ShoppingListItem.product)
            .joinedload(Product.photos),
            joinedload(ShoppingListItem.product)
            .joinedload(Product.stores)
            .joinedload(ProductStore.store),
            joinedload(ShoppingListItem.user),
        )
        .order_by(ShoppingListItem.added_at.desc())
        .all()
    )
    # Deduplicate from joinedload
    seen = set()
    unique_items = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique_items.append(item)

    # Batch fetch last purchase price per product
    product_ids = list({item.product_id for item in unique_items})
    last_price_map = {}
    if product_ids:
        subq = (
            db.query(
                HistoryEvent.product_id,
                func.max(HistoryEvent.id).label("max_id"),
            )
            .filter(
                HistoryEvent.product_id.in_(product_ids),
                HistoryEvent.action == "checked_off",
                HistoryEvent.price.isnot(None),
            )
            .group_by(HistoryEvent.product_id)
            .subquery()
        )
        last_events = (
            db.query(HistoryEvent)
            .join(subq, HistoryEvent.id == subq.c.max_id)
            .all()
        )
        last_price_map = {
            e.product_id: (e.price, e.store_id) for e in last_events
        }

    return [_item_to_read(item, last_price_map) for item in unique_items]


async def _broadcast_list(db: Session):
    if ws_manager:
        items = _get_all_items(db)
        await ws_manager.broadcast({
            "type": "list_updated",
            "data": {"items": [item.model_dump(mode="json") for item in items]},
        })


@router.get("", response_model=List[ShoppingListItemRead])
def get_list(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return _get_all_items(db)


@router.post("", response_model=ShoppingListItemRead, status_code=201)
async def add_item(
    body: ShoppingListItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.product_id:
        product = db.query(Product).filter(Product.id == body.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
    elif body.product_name:
        # Check for existing product with similar name
        product = db.query(Product).filter(
            Product.name.ilike(body.product_name)
        ).first()
        if not product:
            product = Product(name=body.product_name)
            db.add(product)
            db.flush()
    else:
        raise HTTPException(status_code=400, detail="product_id or product_name required")

    # Check if this product is already on the list
    existing_item = db.query(ShoppingListItem).filter(
        ShoppingListItem.product_id == product.id
    ).first()

    if existing_item:
        existing_item.quantity += (body.quantity or 1)
        item = existing_item
    else:
        item = ShoppingListItem(
            product_id=product.id,
            quantity=body.quantity,
            unit=body.unit,
            added_by=user.id,
        )
        db.add(item)

    # Record history
    db.add(HistoryEvent(
        product_id=product.id,
        action="added",
        user_id=user.id,
        quantity=body.quantity,
        unit=body.unit,
    ))

    db.commit()
    db.refresh(item)

    await _broadcast_list(db)
    loaded = (
        db.query(ShoppingListItem)
        .options(
            joinedload(ShoppingListItem.product).joinedload(Product.photos),
            joinedload(ShoppingListItem.product).joinedload(Product.stores).joinedload(ProductStore.store),
            joinedload(ShoppingListItem.user),
        )
        .filter(ShoppingListItem.id == item.id)
        .first()
    )
    return _item_to_read(loaded, _last_price_for(db, loaded.product_id))


@router.put("/{item_id}", response_model=ShoppingListItemRead)
async def edit_item(
    item_id: int,
    body: ShoppingListItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    changes = []
    if body.quantity is not None and body.quantity != item.quantity:
        changes.append("quantity: %s -> %s" % (item.quantity, body.quantity))
        item.quantity = body.quantity
    if body.unit is not None and body.unit != item.unit:
        changes.append("unit: %s -> %s" % (item.unit, body.unit))
        item.unit = body.unit

    if changes:
        db.add(HistoryEvent(
            product_id=item.product_id,
            action="modified",
            user_id=user.id,
            quantity=item.quantity,
            unit=item.unit,
            details="; ".join(changes),
        ))

    db.commit()
    await _broadcast_list(db)

    loaded = (
        db.query(ShoppingListItem)
        .options(
            joinedload(ShoppingListItem.product).joinedload(Product.photos),
            joinedload(ShoppingListItem.product).joinedload(Product.stores).joinedload(ProductStore.store),
            joinedload(ShoppingListItem.user),
        )
        .filter(ShoppingListItem.id == item_id)
        .first()
    )
    return _item_to_read(loaded, _last_price_for(db, loaded.product_id))


@router.post("/{item_id}/check-off", status_code=200)
async def check_off_item(
    item_id: int,
    body: CheckOffRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Update product price if provided
    if body.store_id and body.price is not None:
        ps = (
            db.query(ProductStore)
            .filter(
                ProductStore.product_id == item.product_id,
                ProductStore.store_id == body.store_id,
            )
            .first()
        )
        if ps:
            ps.price = body.price
            ps.updated_at = datetime.utcnow()
        else:
            db.add(ProductStore(
                product_id=item.product_id,
                store_id=body.store_id,
                price=body.price,
            ))

    # Record history
    db.add(HistoryEvent(
        product_id=item.product_id,
        action="checked_off",
        user_id=user.id,
        store_id=body.store_id,
        price=body.price,
        quantity=item.quantity,
        unit=item.unit,
    ))

    db.delete(item)
    db.commit()
    await _broadcast_list(db)
    return {"status": "ok"}


@router.delete("/{item_id}", status_code=200)
async def remove_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.add(HistoryEvent(
        product_id=item.product_id,
        action="removed",
        user_id=user.id,
        quantity=item.quantity,
        unit=item.unit,
    ))

    db.delete(item)
    db.commit()
    await _broadcast_list(db)
    return {"status": "ok"}
