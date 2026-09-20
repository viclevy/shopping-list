import math
import re
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator


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
    quantity: Optional[float] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (math.isfinite(v) and v > 0):
            raise ValueError("quantity must be a positive number")
        return v


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


# --- Receipts ---
class ReceiptLineRead(BaseModel):
    id: int
    position: int
    raw_text: str
    item_code: Optional[str] = None
    section: Optional[str] = None
    line_type: str  # product, discount, fee
    quantity: float = 1
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    net_amount: Optional[float] = None  # paid for the line after its discounts (not set on discounts)
    taxable: bool = False
    applies_to: Optional[int] = None
    suggested_name: Optional[str] = None
    suggested_category: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    match_source: Optional[str] = None  # learned, suggested
    ignored: bool = False


class ReceiptCheck(BaseModel):
    lines_sum: float
    expected_total: float  # lines plus tax
    balanced: bool


class ReceiptRead(BaseModel):
    id: int
    status: str  # pending, failed, confirmed
    error: Optional[str] = None
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    store_text: Optional[str] = None
    purchased_local: Optional[str] = None
    purchased_at: Optional[datetime] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    check: Optional[ReceiptCheck] = None
    uploaded_by: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    image_ids: List[int] = []
    lines: List[ReceiptLineRead] = []


class ReceiptSummary(BaseModel):
    id: int
    status: str
    store_name: Optional[str] = None
    store_text: Optional[str] = None
    purchased_local: Optional[str] = None
    purchased_at: Optional[datetime] = None
    total: Optional[float] = None
    line_count: int
    uploaded_by: str
    created_at: datetime


class ReceiptStoreUpdate(BaseModel):
    store_id: Optional[int] = None


class ReceiptConfirmLine(BaseModel):
    id: int
    ignore: bool = False
    product_id: Optional[int] = None
    new_product_name: Optional[str] = None
    category: Optional[str] = None  # only used when creating the product
    quantity: float = 1
    amount: float = 0  # paid for the whole line, after discounts

    @field_validator("new_product_name", "category")
    @classmethod
    def normalize_text(cls, v: Optional[str]) -> Optional[str]:
        return (_normalize_text(v) or None) if v else None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if not (math.isfinite(v) and v > 0):
            raise ValueError("quantity must be a positive number")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if not (math.isfinite(v) and v >= 0):
            raise ValueError("amount must be zero or more")
        return v

    @model_validator(mode="after")
    def need_a_product(self):
        if not self.ignore and bool(self.product_id) == bool(self.new_product_name):
            raise ValueError("choose an existing product or give a new product name")
        return self


class ReceiptConfirm(BaseModel):
    store_id: int
    purchased_at: datetime  # when the purchase happened; naive values are taken as UTC
    lines: List[ReceiptConfirmLine]


class ReceiptConfirmResult(BaseModel):
    receipt: ReceiptRead
    recorded: int  # purchases added to the history
    updated: int  # earlier check-offs corrected from the receipt instead of counted twice
    new_products: int
    removed_from_list: int
