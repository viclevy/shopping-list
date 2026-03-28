from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import HistoryEvent, Product, Store, User
from schemas import HistoryEventRead

router = APIRouter()


@router.get("", response_model=List[HistoryEventRead])
def list_history(
    product_id: int = Query(None),
    action: str = Query(None),
    user_id: int = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(HistoryEvent)
    if product_id:
        query = query.filter(HistoryEvent.product_id == product_id)
    if action:
        query = query.filter(HistoryEvent.action == action)
    if user_id:
        query = query.filter(HistoryEvent.user_id == user_id)

    events = (
        query.order_by(HistoryEvent.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    result = []
    for e in events:
        product = db.query(Product).filter(Product.id == e.product_id).first()
        user_obj = db.query(User).filter(User.id == e.user_id).first()
        store = db.query(Store).filter(Store.id == e.store_id).first() if e.store_id else None
        result.append(HistoryEventRead(
            id=e.id,
            product_name=product.name if product else "Unknown",
            product_id=e.product_id,
            action=e.action,
            username=user_obj.username if user_obj else "Unknown",
            timestamp=e.timestamp,
            store_name=store.name if store else None,
            price=e.price,
            quantity=e.quantity,
            unit=e.unit,
            details=e.details,
        ))
    return result


@router.delete("/{event_id}", status_code=204)
def delete_history_event(
    event_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    event = db.query(HistoryEvent).filter(HistoryEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="History event not found")
    db.delete(event)
    db.commit()
