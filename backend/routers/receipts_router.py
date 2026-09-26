import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

import receipt_extraction
from auth import get_current_user
from database import get_db
from models import (
    HistoryEvent,
    Product,
    ProductStore,
    Receipt,
    ReceiptImage,
    ReceiptItemMap,
    ReceiptLine,
    ShoppingListItem,
    Store,
    User,
)
from photo_utils import delete_receipt_image, receipt_image_path, save_receipt_image
from receipt_utils import (
    TOTAL_TOLERANCE,
    category_from_section,
    category_from_similar_product,
    check_totals,
    clean_local_time,
    finite,
    match_key,
    match_store,
    net_amounts,
)
from routers.shopping_list_router import _broadcast_list
from schemas import (
    ReceiptCheck,
    ReceiptConfirm,
    ReceiptConfirmResult,
    ReceiptLineRead,
    ReceiptRead,
    ReceiptStoreUpdate,
    ReceiptSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_IMAGES = 3
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
# A check-off already made in the app is corrected from the receipt, not counted twice,
# when it falls in this window around the purchase
ADOPT_BEFORE = timedelta(hours=8)  # ticked off in the aisle, before the receipt printed
ADOPT_AFTER = timedelta(hours=36)  # ticked off at home afterwards
PRICE_SLACK = timedelta(minutes=1)  # a check-off writes its event and the store price a moment apart


# --- Reading receipts back out ---

def _get_receipt(db: Session, receipt_id: int) -> Receipt:
    receipt = (
        db.query(Receipt)
        .options(
            selectinload(Receipt.lines),
            selectinload(Receipt.images),
            joinedload(Receipt.store),
            joinedload(Receipt.user),
        )
        .filter(Receipt.id == receipt_id)
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def _receipt_to_read(db: Session, receipt: Receipt) -> ReceiptRead:
    net = net_amounts(receipt.lines)
    product_ids = {l.product_id for l in receipt.lines if l.product_id}
    names = dict(db.query(Product.id, Product.name).filter(Product.id.in_(product_ids)).all()) if product_ids else {}
    categories = [c for (c,) in db.query(Product.category).filter(Product.category.isnot(None)).distinct().all()]
    named_products = db.query(Product.name, Product.category).filter(Product.category.isnot(None)).all()
    lines = [
        ReceiptLineRead(
            id=l.id,
            position=l.position,
            raw_text=l.raw_text,
            item_code=l.item_code,
            section=l.section,
            line_type=l.line_type,
            quantity=l.quantity or 1,
            unit_price=l.unit_price,
            line_total=l.line_total,
            net_amount=net.get(l.position),
            taxable=bool(l.taxable),
            applies_to=l.applies_to,
            suggested_name=l.suggested_name,
            suggested_category=category_from_section(l.section, categories) or (
                category_from_similar_product(l.suggested_name or l.raw_text, named_products)
                if l.line_type == "product" else None
            ),
            product_id=l.product_id,
            product_name=names.get(l.product_id),
            match_source=l.match_source,
            ignored=bool(l.ignored),
        )
        for l in receipt.lines
    ]
    check = check_totals(receipt.lines, receipt.tax, receipt.total) if receipt.lines else None
    return ReceiptRead(
        id=receipt.id,
        status=receipt.status,
        error=receipt.error,
        store_id=receipt.store_id,
        store_name=receipt.store.name if receipt.store else None,
        store_text=receipt.store_text,
        purchased_local=receipt.purchased_local,
        purchased_at=receipt.purchased_at,
        subtotal=receipt.subtotal,
        tax=receipt.tax,
        total=receipt.total,
        check=ReceiptCheck(**check) if check else None,
        uploaded_by=receipt.user.username,
        created_at=receipt.created_at,
        confirmed_at=receipt.confirmed_at,
        image_ids=[i.id for i in receipt.images],
        lines=lines,
    )


# --- Turning a photo into a draft ---

def _find_store(db: Session, printed: Optional[str]) -> Optional[int]:
    stores = db.query(Store).options(selectinload(Store.aliases)).all()
    return match_store(printed, [(s.id, [s.name] + [a.alias for a in s.aliases]) for s in stores])


def _match_lines(db: Session, receipt: Receipt):
    """Fill in what earlier confirmed receipts taught us about this store's lines."""
    if receipt.store_id is None:
        return
    learned = {
        m.match_key: m
        for m in db.query(ReceiptItemMap).filter(ReceiptItemMap.store_id == receipt.store_id)
    }
    for line in receipt.lines:
        if line.line_type == "discount":
            continue
        entry = learned.get(match_key(line.item_code, line.raw_text))
        if entry is None:
            continue
        line.match_source = "learned"
        if entry.ignore:
            line.ignored = True
            line.product_id = None
        else:
            line.ignored = False
            line.product_id = entry.product_id


def _apply_extraction(db: Session, receipt: Receipt, extracted, valid_product_ids: set):
    receipt.lines.clear()
    db.flush()
    receipt.store_text = (extracted.store_name or "").strip() or None
    receipt.purchased_local = clean_local_time(extracted.purchased_at)
    receipt.subtotal = finite(extracted.subtotal)
    receipt.tax = finite(extracted.tax)
    receipt.total = finite(extracted.total)
    receipt.store_id = _find_store(db, receipt.store_text)
    receipt.status = "pending"
    receipt.error = None

    reviewable = {i for i, line in enumerate(extracted.lines) if line.line_type != "discount"}
    for position, line in enumerate(extracted.lines):
        quantity = finite(line.quantity, 1)
        if quantity <= 0:
            quantity = 1
        total = finite(line.line_total, 0.0)
        if line.line_type == "discount":
            total = -abs(total)
        # The line total is what the receipt charged, so it wins over an inconsistent unit price
        unit = finite(line.unit_price)
        if unit is None or abs(unit * quantity - total) > TOTAL_TOLERANCE:
            unit = total / quantity
        suggested = line.matched_product_id if line.matched_product_id in valid_product_ids else None
        receipt.lines.append(ReceiptLine(
            position=position,
            raw_text=(line.description or "").strip() or "?",
            item_code=re.sub(r"\s+", "", line.item_code or "") or None,
            section=(line.section or "").strip() or None,
            line_type=line.line_type,
            quantity=quantity,
            unit_price=unit,
            line_total=total,
            taxable=bool(line.taxable),
            applies_to=line.applies_to_line if line.line_type == "discount" and line.applies_to_line in reviewable else None,
            suggested_name=(line.suggested_name or "").strip() or None,
            product_id=suggested,
            match_source="suggested" if suggested else None,
            ignored=line.line_type == "fee",
        ))
    _match_lines(db, receipt)
    db.commit()


async def _extract_into(db: Session, receipt: Receipt):
    """Read the receipt's photos and fill in its draft, or mark it failed with the reason."""
    images = []
    for image in receipt.images:
        with open(receipt_image_path(image.filename), "rb") as f:
            images.append(f.read())
    catalog = [
        (pid, name)
        for pid, name in db.query(Product.id, Product.name).order_by(Product.name).limit(receipt_extraction.MAX_CATALOG)
    ]
    try:
        extracted = await asyncio.to_thread(receipt_extraction.extract, images, catalog)
    except receipt_extraction.ExtractionError as e:
        logger.warning("Receipt %d could not be read: %s", receipt.id, e)
        receipt.status = "failed"
        receipt.error = str(e)[:500]
        db.commit()
        return
    _apply_extraction(db, receipt, extracted, {pid for pid, _ in catalog})


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That photo is too large")
    return data


# --- Endpoints ---

@router.get("", response_model=List[ReceiptSummary])
def list_receipts(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    receipts = (
        db.query(Receipt)
        .options(selectinload(Receipt.lines), joinedload(Receipt.store), joinedload(Receipt.user))
        .order_by(Receipt.created_at.desc(), Receipt.id.desc())
        .limit(200)
        .all()
    )
    return [
        ReceiptSummary(
            id=r.id,
            status=r.status,
            store_name=r.store.name if r.store else None,
            store_text=r.store_text,
            purchased_local=r.purchased_local,
            purchased_at=r.purchased_at,
            total=r.total,
            line_count=len([l for l in r.lines if l.line_type != "discount"]),
            uploaded_by=r.user.username,
            created_at=r.created_at,
        )
        for r in receipts
    ]


@router.post("", response_model=ReceiptRead, status_code=201)
async def upload_receipt(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save the photos of one receipt and read them. A failed reading still keeps the receipt."""
    if not files or len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Send between 1 and %d photos" % MAX_IMAGES)
    saved = []
    try:
        for f in files:
            saved.append(await asyncio.to_thread(save_receipt_image, await _read_upload(f)))
    except (ValueError, HTTPException) as e:
        for name in saved:
            delete_receipt_image(name)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=str(e))

    receipt = Receipt(uploaded_by=user.id, status="pending")
    for position, name in enumerate(saved):
        receipt.images.append(ReceiptImage(filename=name, position=position))
    db.add(receipt)
    db.commit()
    await _extract_into(db, receipt)
    return _receipt_to_read(db, _get_receipt(db, receipt.id))


@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return _receipt_to_read(db, _get_receipt(db, receipt_id))


@router.get("/{receipt_id}/images/{image_id}")
def get_receipt_image(
    receipt_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    image = db.query(ReceiptImage).filter(ReceiptImage.id == image_id, ReceiptImage.receipt_id == receipt_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(receipt_image_path(image.filename), media_type="image/jpeg")


@router.post("/{receipt_id}/extract", response_model=ReceiptRead)
async def retry_extraction(
    receipt_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Read the photos again, e.g. after a failure. Replaces the draft."""
    receipt = _get_receipt(db, receipt_id)
    if receipt.status == "confirmed":
        raise HTTPException(status_code=409, detail="This receipt is already confirmed")
    await _extract_into(db, receipt)
    return _receipt_to_read(db, _get_receipt(db, receipt_id))


@router.put("/{receipt_id}", response_model=ReceiptRead)
def set_receipt_store(
    receipt_id: int,
    body: ReceiptStoreUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Choose the store of a draft; lines this store has taught us about are matched again."""
    receipt = _get_receipt(db, receipt_id)
    if receipt.status != "pending":
        raise HTTPException(status_code=409, detail="Only a receipt waiting for review can be changed")
    if body.store_id is not None and not db.get(Store, body.store_id):
        raise HTTPException(status_code=400, detail="Store not found")
    receipt.store_id = body.store_id
    _match_lines(db, receipt)
    db.commit()
    return _receipt_to_read(db, _get_receipt(db, receipt_id))


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _find_adoptable(
    db: Session, product_id: int, store_id: int, purchased_at: datetime, taken: set,
) -> Optional[HistoryEvent]:
    """An earlier in-app check-off of this product that the receipt should correct, not duplicate."""
    query = db.query(HistoryEvent).filter(
        HistoryEvent.product_id == product_id,
        HistoryEvent.action == "checked_off",
        HistoryEvent.receipt_id.is_(None),
        HistoryEvent.timestamp >= purchased_at - ADOPT_BEFORE,
        HistoryEvent.timestamp <= purchased_at + ADOPT_AFTER,
        or_(HistoryEvent.store_id == store_id, HistoryEvent.store_id.is_(None)),
    )
    if taken:
        query = query.filter(HistoryEvent.id.notin_(taken))
    events = query.all()
    if not events:
        return None
    return min(events, key=lambda e: abs((e.timestamp - purchased_at).total_seconds()))


def _remember(db: Session, store_id: int, key: Optional[str], product_id: Optional[int], ignore: bool):
    """Teach the store's line -> product mapping so the next receipt matches by itself."""
    if key is None:
        return
    entry = db.query(ReceiptItemMap).filter(
        ReceiptItemMap.store_id == store_id, ReceiptItemMap.match_key == key
    ).first()
    if entry:
        entry.product_id = product_id
        entry.ignore = ignore
    else:
        db.add(ReceiptItemMap(store_id=store_id, match_key=key, product_id=product_id, ignore=ignore))


@router.post("/{receipt_id}/confirm", response_model=ReceiptConfirmResult)
async def confirm_receipt(
    receipt_id: int,
    body: ReceiptConfirm,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record the reviewed receipt as purchases: history, prices, the shopping list and learned matches."""
    receipt = _get_receipt(db, receipt_id)
    if receipt.status != "pending":
        raise HTTPException(status_code=409, detail="Only a receipt waiting for review can be confirmed")
    store = db.get(Store, body.store_id)
    if not store:
        raise HTTPException(status_code=400, detail="Store not found")

    # Discounts are folded into the line they reduce, so every other line must be reviewed
    reviewable = {l.id: l for l in receipt.lines if l.line_type != "discount"}
    sent = {}
    for item in body.lines:
        if item.id not in reviewable or item.id in sent:
            raise HTTPException(status_code=400, detail="Unknown or repeated receipt line")
        sent[item.id] = item
    if set(sent) != set(reviewable):
        raise HTTPException(status_code=400, detail="Every receipt line must be reviewed")

    purchased_at = _to_naive_utc(body.purchased_at)
    taken = set()
    recorded = updated = new_products = removed = 0
    for line in receipt.lines:
        item = sent.get(line.id)
        if item is None:
            continue
        key = match_key(line.item_code, line.raw_text)
        if item.ignore:
            if line.line_type == "product":
                _remember(db, store.id, key, None, ignore=True)
            line.ignored = True
            line.product_id = None
            continue

        if item.product_id:
            product = db.get(Product, item.product_id)
            if not product:
                raise HTTPException(status_code=400, detail="Product not found")
        else:
            product = db.query(Product).filter(func.lower(Product.name) == item.new_product_name.lower()).first()
            if not product:
                product = Product(name=item.new_product_name, category=item.category)
                db.add(product)
                db.flush()
                new_products += 1

        unit_price = item.amount / item.quantity
        list_item = db.query(ShoppingListItem).filter(ShoppingListItem.product_id == product.id).first()
        event = _find_adoptable(db, product.id, store.id, purchased_at, taken)
        # A store price set after the purchase normally beats the receipt (an old receipt uploaded late),
        # but not when it came from the very check-off this receipt is correcting
        price_cutoff = max(purchased_at, event.timestamp) if event else purchased_at
        if event:
            line.adopted_previous = json.dumps({
                "price": event.price,
                "quantity": event.quantity,
                "store_id": event.store_id,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
            })
            event.price = unit_price
            event.quantity = item.quantity
            event.store_id = store.id
            event.timestamp = purchased_at
            event.details = (event.details + "; " if event.details else "") + "Corrected from receipt #%d" % receipt.id
            event.receipt_id = receipt.id
            updated += 1
        else:
            event = HistoryEvent(
                product_id=product.id,
                action="checked_off",
                user_id=user.id,
                store_id=store.id,
                price=unit_price,
                quantity=item.quantity,
                unit=list_item.unit if list_item else None,
                timestamp=purchased_at,
                details="From receipt #%d" % receipt.id,
                receipt_id=receipt.id,
            )
            db.add(event)
            recorded += 1
        db.flush()
        taken.add(event.id)
        line.event_id = event.id

        # Same rule as a check-off in the app: the price paid becomes the store's price
        price = round(unit_price, 2)
        link = db.query(ProductStore).filter(
            ProductStore.product_id == product.id, ProductStore.store_id == store.id
        ).first()
        if link is None:
            db.add(ProductStore(product_id=product.id, store_id=store.id, price=price))
        elif link.price is None or link.updated_at is None or link.updated_at <= price_cutoff + PRICE_SLACK:
            link.price = price
            link.updated_at = datetime.utcnow()

        if list_item:
            db.delete(list_item)
            removed += 1
        _remember(db, store.id, key, product.id, ignore=False)
        line.product_id = product.id
        line.ignored = False

    receipt.store_id = store.id
    receipt.purchased_at = purchased_at
    receipt.status = "confirmed"
    receipt.confirmed_at = datetime.utcnow()
    db.commit()
    await _broadcast_list(db)
    return ReceiptConfirmResult(
        receipt=_receipt_to_read(db, _get_receipt(db, receipt_id)),
        recorded=recorded,
        updated=updated,
        new_products=new_products,
        removed_from_list=removed,
    )


@router.delete("/{receipt_id}", status_code=204)
def delete_receipt(receipt_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Remove a receipt. If it was confirmed, its purchases are taken back out of the history."""
    receipt = _get_receipt(db, receipt_id)
    if receipt.status == "confirmed":
        for line in receipt.lines:
            event = db.get(HistoryEvent, line.event_id) if line.event_id else None
            if event is None:
                continue
            if line.adopted_previous:
                # Give back the check-off this receipt had corrected
                previous = json.loads(line.adopted_previous)
                event.price = previous["price"]
                event.quantity = previous["quantity"]
                event.store_id = previous["store_id"]
                event.timestamp = datetime.fromisoformat(previous["timestamp"])
                event.details = previous["details"]
                event.receipt_id = None
            else:
                db.delete(event)
        db.flush()
    filenames = [image.filename for image in receipt.images]
    db.delete(receipt)
    db.commit()
    for name in filenames:
        delete_receipt_image(name)
