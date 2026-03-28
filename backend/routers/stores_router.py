from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Store, User
from schemas import StoreCreate, StoreRead

router = APIRouter()


@router.get("", response_model=List[StoreRead])
def list_stores(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Store).order_by(Store.name).all()


@router.post("", response_model=StoreRead, status_code=201)
def create_store(
    body: StoreCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if db.query(Store).filter(Store.name == body.name).first():
        raise HTTPException(status_code=409, detail="Store already exists")
    store = Store(name=body.name)
    db.add(store)
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
    db.delete(store)
    db.commit()
