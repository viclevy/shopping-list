import os
import re
import sqlite3

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from auth import hash_password
from config import settings
from database import Base, SessionLocal, engine
from models import HistoryEvent, Product, ProductPhoto, ProductStore, ShoppingListItem, Store, StoreAlias, User, UserPreference
from routers import (
    analytics_router,
    auth_router,
    history_router,
    products_router,
    search_router,
    shopping_list_router,
    stores_router,
    users_router,
    ws_router,
)
from websocket_manager import manager

app = FastAPI(title="Family Shopping List")


@app.middleware("http")
async def no_cache_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire WebSocket manager into shopping list router
shopping_list_router.ws_manager = manager

# --- Routers ---
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/api/users", tags=["users"])
app.include_router(stores_router.router, prefix="/api/stores", tags=["stores"])
app.include_router(products_router.router, prefix="/api/products", tags=["products"])
app.include_router(shopping_list_router.router, prefix="/api/list", tags=["shopping-list"])
app.include_router(history_router.router, prefix="/api/history", tags=["history"])
app.include_router(analytics_router.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(search_router.router, prefix="/api/search", tags=["search"])
app.include_router(ws_router.router, tags=["websocket"])

# --- Static file mounts ---
uploads_dir = os.path.join(settings.data_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Serve Vue SPA (must be last — catches all unmatched routes)
spa_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(spa_dir):
    # Mount static assets (JS, CSS, icons) without html=True
    app.mount("/assets", StaticFiles(directory=os.path.join(spa_dir, "assets")), name="assets")
    app.mount("/icons", StaticFiles(directory=os.path.join(spa_dir, "icons")), name="icons")

    # Serve top-level static files and SPA fallback
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        if full_path.startswith("api/"):
            return Response(status_code=404, content='{"detail":"Not found"}',
                            media_type="application/json")
        file_path = os.path.join(spa_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(spa_dir, "index.html"))

INITIAL_STORES = [
    "Stop & Shop",
    "Shop-Rite",
    "BJ's Wholesale Club",
    "Costco",
    "Whole Foods",
    "Trader Joe's",
]


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    # Lightweight migration: add new columns if missing
    db_path = os.path.join(settings.data_dir, "shopping_list.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        product_cols = [row[1] for row in conn.execute("PRAGMA table_info(products)").fetchall()]
        if "image_url" not in product_cols:
            conn.execute("ALTER TABLE products ADD COLUMN image_url TEXT")
        photo_cols = [row[1] for row in conn.execute("PRAGMA table_info(product_photos)").fetchall()]
        if "is_primary" not in photo_cols:
            conn.execute("ALTER TABLE product_photos ADD COLUMN is_primary BOOLEAN DEFAULT 0")
        store_cols = [row[1] for row in conn.execute("PRAGMA table_info(stores)").fetchall()]
        if "include_in_image_search" not in store_cols:
            conn.execute("ALTER TABLE stores ADD COLUMN include_in_image_search BOOLEAN DEFAULT 1")
        if "favorite_store_id" not in product_cols:
            conn.execute("ALTER TABLE products ADD COLUMN favorite_store_id INTEGER REFERENCES stores(id) ON DELETE SET NULL")
        list_item_cols = [row[1] for row in conn.execute("PRAGMA table_info(shopping_list_items)").fetchall()]
        if "sort_order" not in list_item_cols:
            conn.execute("ALTER TABLE shopping_list_items ADD COLUMN sort_order INTEGER")
        conn.commit()
        conn.close()

    db = SessionLocal()
    try:
        # Normalize existing categories to Title Case
        products_with_cat = db.query(Product).filter(Product.category.isnot(None)).all()
        for p in products_with_cat:
            normalized = re.sub(r"\s+", " ", p.category.strip()).title()
            if normalized != p.category:
                p.category = normalized
        # Normalize existing usernames to lowercase
        all_users = db.query(User).all()
        for u in all_users:
            lowered = u.username.strip().lower()
            if lowered != u.username:
                u.username = lowered

        # Normalize existing product names to Title Case and merge duplicates
        all_products = db.query(Product).all()
        name_map = {}  # normalized_name -> keeper Product
        for p in all_products:
            normalized = re.sub(r"\s+", " ", p.name.strip()).title()
            if normalized in name_map:
                keeper = name_map[normalized]
                # Re-point child FKs from duplicate to keeper
                db.query(ShoppingListItem).filter(ShoppingListItem.product_id == p.id).update(
                    {"product_id": keeper.id}, synchronize_session="fetch")
                db.query(HistoryEvent).filter(HistoryEvent.product_id == p.id).update(
                    {"product_id": keeper.id}, synchronize_session="fetch")
                db.query(ProductPhoto).filter(ProductPhoto.product_id == p.id).update(
                    {"product_id": keeper.id}, synchronize_session="fetch")
                # Merge store associations (skip duplicates)
                for ps in db.query(ProductStore).filter(ProductStore.product_id == p.id).all():
                    existing = db.query(ProductStore).filter(
                        ProductStore.product_id == keeper.id,
                        ProductStore.store_id == ps.store_id,
                    ).first()
                    if existing:
                        if ps.price is not None and existing.price is None:
                            existing.price = ps.price
                        db.delete(ps)
                    else:
                        ps.product_id = keeper.id
                db.delete(p)
            else:
                if normalized != p.name:
                    p.name = normalized
                name_map[normalized] = p

        db.commit()

        # Bootstrap admin user
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=hash_password(settings.admin_password),
                is_admin=True,
            )
            db.add(admin)
            db.commit()

        # Seed initial stores
        for store_name in INITIAL_STORES:
            if not db.query(Store).filter(Store.name == store_name).first():
                db.add(Store(name=store_name))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    kwargs = {"host": "0.0.0.0", "port": settings.port}
    if settings.tls_enabled and settings.tls_cert_file and settings.tls_key_file:
        kwargs["ssl_certfile"] = settings.tls_cert_file
        kwargs["ssl_keyfile"] = settings.tls_key_file
    uvicorn.run(app, **kwargs)
