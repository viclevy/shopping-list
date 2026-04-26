import re
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator


def _normalize_text(v: str) -> str:
    """Strip, collapse spaces, and title-case a string."""
    if v is None:
        return v
    v = re.sub(r"\s+", " ", v.strip())
    return v.title() if v else v


def _normalize_category(v: str) -> str:
    """Strip, collapse spaces, and title-case a category string."""
    return _normalize_text(v)


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---
class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip().lower()


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
    include_in_image_search: bool = True


class StoreAliasRead(BaseModel):
    id: int
    alias: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreRead(BaseModel):
    id: int
    name: str
    include_in_image_search: bool
    aliases: List[StoreAliasRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Product ---
class ProductPhotoRead(BaseModel):
    id: int
    filename: str
    original_name: Optional[str] = None
    is_primary: bool = False
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
    favorite_store_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return _normalize_text(v)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_category(v) if v else v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    store_ids: Optional[List[int]] = None
    prices: Optional[Dict[int, Optional[float]]] = None
    favorite_store_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_text(v) if v else v

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_category(v) if v else v


class ProductRead(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    image_url: Optional[str] = None
    favorite_store_id: Optional[int] = None
    favorite_store: Optional[StoreRead] = None
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

    @field_validator("product_name")
    @classmethod
    def normalize_product_name(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_text(v) if v else v


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
    last_price: Optional[float] = None
    last_store_id: Optional[int] = None
    sort_order: Optional[int] = None

    model_config = {"from_attributes": True}


# --- User Preferences ---
VALID_LIST_GROUPING = {"category", "flat"}
VALID_LIST_ITEM_SORT = {"alpha-asc", "alpha-desc", "manual"}
VALID_CATEGORY_SORT = {"alpha-asc", "alpha-desc", "manual", "frequency"}
VALID_BUYAGAIN_SORT = {"frequency", "alpha-asc", "alpha-desc"}


class UserPreferenceRead(BaseModel):
    list_grouping: str = "category"
    list_item_sort: str = "alpha-asc"
    category_sort: str = "alpha-asc"
    category_order: Optional[List[str]] = None
    buyagain_sort: str = "frequency"

    model_config = {"from_attributes": True}


class UserPreferenceUpdate(BaseModel):
    list_grouping: Optional[str] = None
    list_item_sort: Optional[str] = None
    category_sort: Optional[str] = None
    category_order: Optional[List[str]] = None
    buyagain_sort: Optional[str] = None

    @field_validator("list_grouping")
    @classmethod
    def validate_list_grouping(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_LIST_GROUPING:
            raise ValueError(f"list_grouping must be one of {VALID_LIST_GROUPING}")
        return v

    @field_validator("list_item_sort")
    @classmethod
    def validate_list_item_sort(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_LIST_ITEM_SORT:
            raise ValueError(f"list_item_sort must be one of {VALID_LIST_ITEM_SORT}")
        return v

    @field_validator("category_sort")
    @classmethod
    def validate_category_sort(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_CATEGORY_SORT:
            raise ValueError(f"category_sort must be one of {VALID_CATEGORY_SORT}")
        return v

    @field_validator("buyagain_sort")
    @classmethod
    def validate_buyagain_sort(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_BUYAGAIN_SORT:
            raise ValueError(f"buyagain_sort must be one of {VALID_BUYAGAIN_SORT}")
        return v


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


class StorePriceByName(BaseModel):
    store_name: str
    price: float


class BoughtBeforeItem(BaseModel):
    product_id: int
    product_name: str
    category: Optional[str] = None
    image_url: Optional[str] = None
    photo_filename: Optional[str] = None
    purchase_count: int
    last_purchased: Optional[datetime] = None
    score: float
