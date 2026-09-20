"""Shared test setup.

The app is imported against a throwaway data directory, so the tests never touch real data.
Every test that uses `client` starts from an empty database with only the admin user and the
default stores. The AI call is replaced through the `ai` fixture; nothing here reaches the network.
"""

import atexit
import os
import shutil
import tempfile
from types import SimpleNamespace

# Must happen before any app module is imported: config and database read these at import time
DATA_DIR = tempfile.mkdtemp(prefix="shopping-list-tests-")
os.environ.update(DATA_DIR=DATA_DIR, ADMIN_PASSWORD="test-password", JWT_SECRET="test-secret", GEMINI_API_KEY="")
atexit.register(shutil.rmtree, DATA_DIR, ignore_errors=True)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import photo_utils  # noqa: E402
import receipt_extraction  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from helpers import hours_ago, jpeg  # noqa: E402
from main import app  # noqa: E402
from models import HistoryEvent  # noqa: E402
from receipt_fixtures import stop_shop  # noqa: E402

RECEIPTS_DIR = photo_utils.RECEIPT_DIR


@pytest.fixture
def client():
    """A test client logged in as admin, on an empty database."""
    Base.metadata.drop_all(bind=engine)
    shutil.rmtree(RECEIPTS_DIR, ignore_errors=True)
    with TestClient(app) as test_client:  # startup creates the tables, the admin and the default stores
        login = test_client.post("/api/auth/login", json={"username": "admin", "password": "test-password"})
        test_client.headers.update({"Authorization": "Bearer " + login.json()["access_token"]})
        yield test_client


@pytest.fixture
def anonymous(client):
    """A client that is not logged in (use together with `client`, which sets the database up)."""
    return TestClient(app)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def ai(monkeypatch):
    """The AI call. Append what each reading should return (or an exception to raise)."""
    queue = []

    def fake_extract(images, catalog):
        result = queue.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(receipt_extraction, "extract", fake_extract)
    return queue


class Shop:
    """Helpers for setting up a shopping trip through the API."""

    def __init__(self, client, ai):
        self.client = client
        self.ai = ai
        self.store = {s["name"]: s["id"] for s in client.get("/api/stores").json()}

    def product(self, name, category=None):
        response = self.client.post("/api/products", json={"name": name, "category": category})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def add_to_list(self, product_id):
        response = self.client.post("/api/list", json={"product_id": product_id, "quantity": 1})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def check_off(self, list_item_id, store_id, price, quantity=1):
        response = self.client.post(
            "/api/list/%d/check-off" % list_item_id, json={"store_id": store_id, "price": price, "quantity": quantity}
        )
        assert response.status_code == 200, response.text

    def upload(self, reading=None, files=None):
        """Upload a receipt photo; `reading` is what the AI call will return for it."""
        if reading is not None:
            self.ai.append(reading)
        files = files or [("files", ("receipt.jpg", jpeg(), "image/jpeg"))]
        return self.client.post("/api/receipts", files=files)

    def confirm(self, draft, store_id, purchased_at, choices, amounts=None):
        """Confirm a draft. `choices` has one entry per line that is not a discount, in order:
        None to skip it, an int for an existing product id, a str for a new product name,
        or a (name, category) tuple for a new product. `amounts` maps a line's index to a paid amount."""
        reviewable = [line for line in draft["lines"] if line["line_type"] != "discount"]
        assert len(choices) == len(reviewable)
        lines = []
        for index, (line, choice) in enumerate(zip(reviewable, choices)):
            if choice is None:
                lines.append({"id": line["id"], "ignore": True})
                continue
            entry = {"id": line["id"], "quantity": line["quantity"], "amount": (amounts or {}).get(index, line["net_amount"])}
            if isinstance(choice, int):
                entry["product_id"] = choice
            elif isinstance(choice, tuple):
                entry["new_product_name"], entry["category"] = choice
            else:
                entry["new_product_name"] = choice
            lines.append(entry)
        return self.client.post(
            "/api/receipts/%d/confirm" % draft["id"],
            json={"store_id": store_id, "purchased_at": purchased_at, "lines": lines},
        )

    def check_offs(self, product_id):
        """The purchases recorded for a product."""
        with SessionLocal() as session:
            return (
                session.query(HistoryEvent)
                .filter(HistoryEvent.product_id == product_id, HistoryEvent.action == "checked_off")
                .all()
            )

    def spent_by_store(self):
        rows = self.client.get("/api/analytics/by-store").json()
        return {row["store_name"]: row["total"] for row in rows}


@pytest.fixture
def shop(client, ai):
    return Shop(client, ai)


@pytest.fixture
def morning(shop):
    """The Stop & Shop trip: butter was already checked off in the app at the wrong price,
    then the receipt (matching two lines to known products) is read and confirmed an hour ago."""
    cottage = shop.product("Cottage Cheese", "Dairy")
    butter = shop.product("Butter", "Dairy")
    shop.product("Bananas", "Produce")  # so "Produce" is a category the app already uses
    shop.check_off(shop.add_to_list(butter), shop.store["Stop & Shop"], 4.50)
    shop.add_to_list(butter)
    shop.add_to_list(cottage)

    draft = shop.upload(stop_shop(matched=(cottage, butter, None))).json()
    purchased = hours_ago(1)
    result = shop.confirm(
        draft, shop.store["Stop & Shop"], purchased, [cottage, butter, ("large strawberries", "Produce"), None]
    )
    assert result.status_code == 200, result.text
    return SimpleNamespace(cottage=cottage, butter=butter, draft=draft, result=result.json(), purchased=purchased)
