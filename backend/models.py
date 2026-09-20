from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    include_in_image_search = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    aliases = relationship("StoreAlias", back_populates="store", cascade="all, delete-orphan")


class StoreAlias(Base):
    __tablename__ = "store_aliases"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="aliases")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    favorite_store_id = Column(Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    photos = relationship("ProductPhoto", back_populates="product", cascade="all, delete-orphan")
    stores = relationship("ProductStore", back_populates="product", cascade="all, delete-orphan")
    favorite_store = relationship("Store", foreign_keys=[favorite_store_id])


class ProductStore(Base):
    __tablename__ = "product_stores"
    __table_args__ = (UniqueConstraint("product_id", "store_id"),)

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    price = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="stores")
    store = relationship("Store")


class ProductPhoto(Base):
    __tablename__ = "product_photos"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="photos")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Float, default=1)
    unit = Column(String, nullable=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    sort_order = Column(Integer, nullable=True)

    product = relationship("Product")
    user = relationship("User")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    list_grouping = Column(String, default="category")   # "category" | "flat"
    list_item_sort = Column(String, default="alpha-asc")  # "alpha-asc" | "alpha-desc" | "manual"
    category_sort = Column(String, default="alpha-asc")   # "alpha-asc" | "alpha-desc" | "manual" | "frequency"
    category_order = Column(String, nullable=True)         # JSON list of category names for manual sort
    buyagain_sort = Column(String, default="frequency")    # "frequency" | "alpha-asc" | "alpha-desc"

    user = relationship("User")


class HistoryEvent(Base):
    __tablename__ = "history_events"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)  # added, modified, checked_off, removed
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=True)
    price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    details = Column(String, nullable=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True)

    product = relationship("Product")
    user = relationship("User")
    store = relationship("Store")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True)
    status = Column(String, nullable=False, default="pending")  # pending, failed, confirmed
    error = Column(String, nullable=True)  # why reading the photo failed
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True)
    store_text = Column(String, nullable=True)  # store name as printed on the receipt
    purchased_local = Column(String, nullable=True)  # date and time as printed, ISO without timezone
    purchased_at = Column(DateTime, nullable=True)  # UTC, set when the receipt is confirmed
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total = Column(Float, nullable=True)

    user = relationship("User")
    store = relationship("Store")
    images = relationship(
        "ReceiptImage", back_populates="receipt", cascade="all, delete-orphan", order_by="ReceiptImage.position"
    )
    lines = relationship(
        "ReceiptLine", back_populates="receipt", cascade="all, delete-orphan", order_by="ReceiptLine.position"
    )


class ReceiptImage(Base):
    __tablename__ = "receipt_images"

    id = Column(Integer, primary_key=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    receipt = relationship("Receipt", back_populates="images")


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    id = Column(Integer, primary_key=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)
    raw_text = Column(String, nullable=False)  # description exactly as printed
    item_code = Column(String, nullable=True)
    section = Column(String, nullable=True)  # department heading printed above the line
    line_type = Column(String, nullable=False, default="product")  # product, discount, fee
    quantity = Column(Float, default=1)
    unit_price = Column(Float, nullable=True)
    line_total = Column(Float, nullable=True)  # negative for discounts
    taxable = Column(Boolean, default=False)
    applies_to = Column(Integer, nullable=True)  # position of the line a discount reduces
    suggested_name = Column(String, nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    match_source = Column(String, nullable=True)  # learned, suggested
    ignored = Column(Boolean, default=False)
    event_id = Column(Integer, ForeignKey("history_events.id", ondelete="SET NULL"), nullable=True)
    adopted_previous = Column(String, nullable=True)  # JSON of the check-off this line took over, for undo

    receipt = relationship("Receipt", back_populates="lines")
    product = relationship("Product")


class ReceiptItemMap(Base):
    """What a receipt line means at a given store, learned from confirmed receipts."""
    __tablename__ = "receipt_item_map"
    __table_args__ = (UniqueConstraint("store_id", "match_key"),)

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    match_key = Column(String, nullable=False)  # "code:<digits>" or "text:<normalized description>"
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    ignore = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
