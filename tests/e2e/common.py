"""Helpers shared by the browser tests."""

import os
import struct
import sys
import time
import urllib.request
import zlib

BASE = os.environ.get("BASE", "http://localhost:8080")
SCREENSHOT_DIR = os.environ.get("SCREENSHOT_DIR")  # set it to keep screenshots
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "e2e-pw")


def _png():
    """A 1x1 white PNG, built here so its checksums are right by construction."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8 bits, RGB
    pixel_row = b"\x00\xff\xff\xff"  # filter byte + one white pixel
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixel_row)) + chunk(b"IEND", b"")


PNG = _png()  # any image will do as a receipt photo, the AI call is replaced

passed = 0
failed = 0
console_problems = []


def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print("FAIL:", label, flush=True)


def wait_for_app():
    for _ in range(90):
        try:
            urllib.request.urlopen(BASE, timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise SystemExit("the app did not start")


def watch(page, tag):
    """Collect console errors and warnings (a missing translation is a console warning)."""
    def on_console(message):
        if message.type in ("error", "warning"):
            console_problems.append("[%s] %s: %s" % (tag, message.type, message.text))

    page.on("console", on_console)
    page.on("pageerror", lambda error: console_problems.append("[%s] pageerror: %s" % (tag, error)))


def screenshot(page, name, **options):
    if SCREENSHOT_DIR:
        page.screenshot(path="%s/%s.png" % (SCREENSHOT_DIR, name), **options)


def login(page):
    page.goto(BASE + "/#/login")
    page.fill("#username", "admin")
    page.fill("#password", ADMIN_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_selector(".app-header")


class Api:
    """The app's API, called from the test with the admin's login, for setting things up."""

    def __init__(self, playwright):
        self.context = playwright.request.new_context(base_url=BASE)
        token = self.context.post("/api/auth/login", data={"username": "admin", "password": ADMIN_PASSWORD}).json()["access_token"]
        self.headers = {"Authorization": "Bearer " + token}

    def post(self, path, data=None, **options):
        response = self.context.post(path, data=data, headers=self.headers, **options)
        assert response.ok, (path, response.status, response.text())
        return response.json()

    def next_reading(self, fixture):
        """Choose what the next receipt reading returns (see serve_with_stub.py)."""
        return self.post("/__stub/next", {"fixture": fixture})


def finish():
    print()
    for entry in console_problems:
        print("CONSOLE:", entry)
    print("%d checks passed, %d failed, %d console warnings/errors" % (passed, failed, len(console_problems)))
    sys.exit(1 if failed or console_problems else 0)
