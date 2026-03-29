import math
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import HistoryEvent, Product, ShoppingListItem, Store, User
from schemas import (
    BoughtBeforeItem,
    FrequentItem,
    MemberContribution,
    SpendingByCategory,
    SpendingByStore,
    SpendingPeriod,
)

router = APIRouter()


@router.get("/spending", response_model=List[SpendingPeriod])
def get_spending(
    period: str = Query("month", pattern="^(week|month|year)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Group checked_off events by period
    if period == "week":
        date_fmt = "%Y-W%W"
    elif period == "month":
        date_fmt = "%Y-%m"
    else:
        date_fmt = "%Y"

    rows = (
        db.query(
            func.strftime(date_fmt, HistoryEvent.timestamp).label("period"),
            func.sum(
                HistoryEvent.price * HistoryEvent.quantity
            ).label("total"),
        )
        .filter(
            HistoryEvent.action == "checked_off",
            HistoryEvent.price.isnot(None),
        )
        .group_by("period")
        .order_by("period")
        .all()
    )
    return [SpendingPeriod(period=r.period, total=r.total or 0) for r in rows]


@router.get("/by-store", response_model=List[SpendingByStore])
def spending_by_store(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        db.query(
            Store.name,
            func.sum(HistoryEvent.price * HistoryEvent.quantity).label("total"),
        )
        .join(Store, HistoryEvent.store_id == Store.id)
        .filter(
            HistoryEvent.action == "checked_off",
            HistoryEvent.price.isnot(None),
        )
        .group_by(Store.name)
        .order_by(func.sum(HistoryEvent.price * HistoryEvent.quantity).desc())
        .all()
    )
    return [SpendingByStore(store_name=r[0], total=r[1] or 0) for r in rows]


@router.get("/by-category", response_model=List[SpendingByCategory])
def spending_by_category(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        db.query(
            func.coalesce(Product.category, "Uncategorized"),
            func.sum(HistoryEvent.price * HistoryEvent.quantity).label("total"),
        )
        .join(Product, HistoryEvent.product_id == Product.id)
        .filter(
            HistoryEvent.action == "checked_off",
            HistoryEvent.price.isnot(None),
        )
        .group_by(Product.category)
        .order_by(func.sum(HistoryEvent.price * HistoryEvent.quantity).desc())
        .all()
    )
    return [SpendingByCategory(category=r[0], total=r[1] or 0) for r in rows]


@router.get("/frequent-items", response_model=List[FrequentItem])
def frequent_items(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        db.query(
            HistoryEvent.product_id,
            Product.name,
            func.count(HistoryEvent.id).label("count"),
            func.max(HistoryEvent.timestamp).label("last_purchased"),
        )
        .join(Product, HistoryEvent.product_id == Product.id)
        .filter(HistoryEvent.action == "checked_off")
        .group_by(HistoryEvent.product_id, Product.name)
        .order_by(func.count(HistoryEvent.id).desc())
        .limit(limit)
        .all()
    )
    return [
        FrequentItem(
            product_id=r[0],
            product_name=r[1],
            count=r[2],
            last_purchased=r[3],
        )
        for r in rows
    ]


@router.get("/frequency/{product_id}")
def purchase_frequency(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    events = (
        db.query(HistoryEvent.timestamp, HistoryEvent.price, HistoryEvent.quantity)
        .filter(
            HistoryEvent.product_id == product_id,
            HistoryEvent.action == "checked_off",
        )
        .order_by(HistoryEvent.timestamp)
        .all()
    )
    purchases = [
        {"date": e.timestamp.isoformat(), "price": e.price, "quantity": e.quantity}
        for e in events
    ]

    avg_days = None
    if len(events) >= 2:
        deltas = [
            (events[i].timestamp - events[i - 1].timestamp).days
            for i in range(1, len(events))
        ]
        avg_days = sum(deltas) / len(deltas) if deltas else None

    return {
        "product_id": product_id,
        "total_purchases": len(events),
        "avg_days_between_purchases": avg_days,
        "purchases": purchases,
    }


@router.get("/contributions", response_model=List[MemberContribution])
def member_contributions(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    users = db.query(User).all()
    result = []
    for u in users:
        items_added = (
            db.query(func.count(HistoryEvent.id))
            .filter(HistoryEvent.user_id == u.id, HistoryEvent.action == "added")
            .scalar()
        ) or 0
        items_bought = (
            db.query(func.count(HistoryEvent.id))
            .filter(HistoryEvent.user_id == u.id, HistoryEvent.action == "checked_off")
            .scalar()
        ) or 0
        total_spent = (
            db.query(func.sum(HistoryEvent.price * HistoryEvent.quantity))
            .filter(
                HistoryEvent.user_id == u.id,
                HistoryEvent.action == "checked_off",
                HistoryEvent.price.isnot(None),
            )
            .scalar()
        ) or 0
        result.append(MemberContribution(
            username=u.username,
            items_added=items_added,
            items_bought=items_bought,
            total_spent=total_spent,
        ))
    return result


@router.get("/bought-before", response_model=List[BoughtBeforeItem])
def bought_before(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    HALF_LIFE = 30.0

    # IDs currently on the active shopping list
    on_list_ids = {
        row[0] for row in db.query(ShoppingListItem.product_id).all()
    }

    # Aggregate checked_off events per product
    rows = (
        db.query(
            HistoryEvent.product_id,
            Product.name,
            Product.category,
            Product.image_url,
            func.count(HistoryEvent.id).label("purchase_count"),
            func.max(HistoryEvent.timestamp).label("last_purchased"),
        )
        .join(Product, HistoryEvent.product_id == Product.id)
        .filter(HistoryEvent.action == "checked_off")
        .group_by(HistoryEvent.product_id, Product.name, Product.category, Product.image_url)
        .all()
    )

    now = datetime.utcnow()
    results = []
    for r in rows:
        if r.product_id in on_list_ids:
            continue
        days_since = (now - r.last_purchased).total_seconds() / 86400.0
        decay = math.exp(-days_since / HALF_LIFE)
        score = r.purchase_count * decay
        results.append(BoughtBeforeItem(
            product_id=r.product_id,
            product_name=r.name,
            category=r.category,
            image_url=r.image_url,
            purchase_count=r.purchase_count,
            last_purchased=r.last_purchased,
            score=round(score, 4),
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:limit]
