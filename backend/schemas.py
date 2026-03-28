from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---
class UserCreate(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PasswordUpdate(BaseModel):
    password: str


# --- Store ---
class StoreCreate(BaseModel):
    name: str


class StoreRead(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Product ---
class ProductPhotoRead(BaseModel):
    id: int
    filename: str
    original_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductStoreRead(BaseModel):
    store_id: int
    store_name: str
    price: Optional[float] = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    store_ids: Optional[List[int]] = None
    prices: Optional[Dict[int, Optional[float]]] = None  # store_id -> price


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    store_ids: Optional[List[int]] = None
    prices: Optional[Dict[int, Optional[float]]] = None


class ProductRead(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    photos: List[ProductPhotoRead] = []
    stores: List[ProductStoreRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Shopping List ---
class ShoppingListItemCreate(BaseModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: float = 1
    unit: Optional[str] = None


class ShoppingListItemUpdate(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[str] = None


class ShoppingListItemRead(BaseModel):
    id: int
    product: ProductRead
    quantity: float
    unit: Optional[str] = None
    added_by: str
    added_at: datetime

    model_config = {"from_attributes": True}


class CheckOffRequest(BaseModel):
    store_id: Optional[int] = None
    price: Optional[float] = None


# --- History ---
class HistoryEventRead(BaseModel):
    id: int
    product_name: str
    product_id: int
    action: str
    username: str
    timestamp: datetime
    store_name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    details: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Analytics ---
class SpendingPeriod(BaseModel):
    period: str
    total: float


class SpendingByStore(BaseModel):
    store_name: str
    total: float


class SpendingByCategory(BaseModel):
    category: str
    total: float


class FrequentItem(BaseModel):
    product_id: int
    product_name: str
    count: int
    last_purchased: Optional[datetime] = None


class MemberContribution(BaseModel):
    username: str
    items_added: int
    items_bought: int
    total_spent: float
