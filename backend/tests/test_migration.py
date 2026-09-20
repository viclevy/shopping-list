"""Starting the new code on a database made before receipts existed."""

import os
import sqlite3
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# history_events as it was before receipts: no receipt_id column
OLD_HISTORY_EVENTS = """
CREATE TABLE history_events (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    action VARCHAR NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp DATETIME,
    store_id INTEGER,
    price FLOAT,
    quantity FLOAT,
    unit VARCHAR,
    details VARCHAR
)
"""

START_THE_APP = """
from fastapi.testclient import TestClient
from main import app
with TestClient(app):
    pass
"""


def start_app_on(data_dir):
    env = dict(os.environ, DATA_DIR=str(data_dir), JWT_SECRET="x", ADMIN_PASSWORD="x", GEMINI_API_KEY="")
    subprocess.run([sys.executable, "-W", "ignore", "-c", START_THE_APP], cwd=BACKEND, env=env, check=True, capture_output=True)


def test_startup_adds_receipts_to_an_old_database_and_keeps_its_data(tmp_path):
    path = tmp_path / "shopping_list.db"
    connection = sqlite3.connect(path)
    connection.execute(OLD_HISTORY_EVENTS)
    connection.execute(
        "INSERT INTO history_events (product_id, action, user_id, timestamp, price, quantity) "
        "VALUES (1, 'checked_off', 1, '2026-01-01 10:00:00.000000', 3.5, 1)"
    )
    connection.commit()
    connection.close()

    start_app_on(tmp_path)
    start_app_on(tmp_path)  # a second start must change nothing

    connection = sqlite3.connect(path)
    columns = [row[1] for row in connection.execute("PRAGMA table_info(history_events)")]
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    events = connection.execute("SELECT product_id, action, price, receipt_id FROM history_events").fetchall()
    connection.close()

    assert "receipt_id" in columns
    assert {"receipts", "receipt_images", "receipt_lines", "receipt_item_map"} <= tables
    assert events == [(1, "checked_off", 3.5, None)]
