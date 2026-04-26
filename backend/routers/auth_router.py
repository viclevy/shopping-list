import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import create_token, get_current_user, verify_password
from database import get_db
from models import User, UserPreference
from schemas import LoginRequest, TokenResponse, UserPreferenceRead, UserPreferenceUpdate, UserRead

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/preferences", response_model=UserPreferenceRead)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if not pref:
        return UserPreferenceRead()
    return UserPreferenceRead(
        list_grouping=pref.list_grouping or "category",
        list_item_sort=pref.list_item_sort or "alpha-asc",
        category_sort=pref.category_sort or "alpha-asc",
        category_order=json.loads(pref.category_order) if pref.category_order else None,
        buyagain_sort=pref.buyagain_sort or "frequency",
    )


@router.put("/preferences", response_model=UserPreferenceRead)
def set_preferences(
    body: UserPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if not pref:
        pref = UserPreference(user_id=user.id)
        db.add(pref)
    if body.list_grouping is not None:
        pref.list_grouping = body.list_grouping
    if body.list_item_sort is not None:
        pref.list_item_sort = body.list_item_sort
    if body.category_sort is not None:
        pref.category_sort = body.category_sort
    if body.category_order is not None:
        pref.category_order = json.dumps(body.category_order)
    if body.buyagain_sort is not None:
        pref.buyagain_sort = body.buyagain_sort
    db.commit()
    db.refresh(pref)
    return UserPreferenceRead(
        list_grouping=pref.list_grouping or "category",
        list_item_sort=pref.list_item_sort or "alpha-asc",
        category_sort=pref.category_sort or "alpha-asc",
        category_order=json.loads(pref.category_order) if pref.category_order else None,
        buyagain_sort=pref.buyagain_sort or "frequency",
    )
