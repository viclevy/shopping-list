"""Times and dates are shown in the viewer's own timezone, not as the UTC ones the server stores."""

import datetime as dt

from playwright.sync_api import sync_playwright

from common import BASE, PNG, Api, check, finish, login, screenshot, wait_for_app, watch

# The purchase below happened at 14:44 UTC on Sep 20, 2026
PURCHASED_AT = "2026-09-20T14:44:00Z"
ITEM = "Local Time Test Item"

# For the pages that show only a date. Kiritimati (UTC+14) is on a different calendar date than UTC from
# 10:00 UTC on, and Pago Pago (UTC-11) until 11:00 UTC, so one of them differs for any moment. Neither
# has daylight saving time, so the expected text needs no timezone database.
OFFSETS = {"Pacific/Kiritimati": 14, "Pacific/Pago_Pago": -11}


def date_text(moment, with_year):
    """Like toLocaleDateString('en-US', {month: 'short', day: 'numeric'[, year: 'numeric']})."""
    text = "%s %d" % (moment.strftime("%b"), moment.day)
    return "%s, %d" % (text, moment.year) if with_year else text


def a_zone_on_another_date(stored, with_year=True):
    """(timezone, the date it shows for this stored UTC time, the UTC date that would be wrong)."""
    moment = dt.datetime.fromisoformat(stored.rstrip("Z"))
    zone = "Pacific/Kiritimati" if moment.hour >= 10 else "Pacific/Pago_Pago"
    local = moment + dt.timedelta(hours=OFFSETS[zone])
    assert local.date() != moment.date()
    return zone, date_text(local, with_year), date_text(moment, with_year)


wait_for_app()
with sync_playwright() as p:
    browser = p.chromium.launch()
    api = Api(p)

    # Record one purchase at a known UTC time, through a receipt
    api.next_reading("stop_shop")
    draft = api.post("/api/receipts", multipart={"files": {"name": "receipt.png", "mimeType": "image/png", "buffer": PNG}})
    lines = []
    for line in draft["lines"]:
        if line["line_type"] == "product" and not lines:
            lines.append({"id": line["id"], "new_product_name": ITEM, "quantity": line["quantity"], "amount": line["net_amount"]})
        elif line["line_type"] != "discount":
            lines.append({"id": line["id"], "ignore": True})
    confirmed = api.post("/api/receipts/%d/confirm" % draft["id"], {"store_id": draft["store_id"], "purchased_at": PURCHASED_AT, "lines": lines})
    product_id = next(l["product_id"] for l in confirmed["receipt"]["lines"] if l["product_id"])

    # ---------------- History and a product's history show the viewer's local time ----------------
    for timezone, expected in (("America/New_York", "10:44 AM"), ("Asia/Tokyo", "11:44 PM")):
        context = browser.new_context(viewport={"width": 900, "height": 600}, locale="en-US", timezone_id=timezone)
        page = context.new_page()
        watch(page, timezone)
        login(page)

        page.goto(BASE + "/#/history")
        page.wait_for_selector(".event-row")
        meta = " ".join(page.locator(".event-row", has_text=ITEM).locator(".event-meta").inner_text().split())
        check("Sep 20" in meta and expected in meta, "[%s] History shows the purchase at %s: %r" % (timezone, expected, meta))
        if timezone == "America/New_York":
            screenshot(page, "history-local-time")

        page.goto(BASE + "/#/product/%d" % product_id)
        page.wait_for_selector(".history-date")
        date = page.locator(".history-date").first.inner_text()
        check("Sep 20, 2026" in date and expected in date, "[%s] the product page shows it at %s: %r" % (timezone, expected, date))
        context.close()

    # ---------------- pages that show only a date ----------------
    def shown(zone, path, locator):
        """What a page shows to someone in the given timezone; locator(page) finds the text."""
        context = browser.new_context(viewport={"width": 900, "height": 600}, locale="en-US", timezone_id=zone)
        page = context.new_page()
        watch(page, zone)
        login(page)
        page.goto(BASE + path)
        element = locator(page).first
        element.wait_for()
        text = " ".join(element.inner_text().split())
        context.close()
        return text

    def check_date(page_name, text, prefix, local, wrong_utc, zone):
        check(text == "%s %s" % (prefix, local), "[%s] %s shows the local date %r, not the UTC date %r: %r" % (zone, page_name, local, wrong_utc, text))

    first_store = api.get("/api/stores")[0]
    zone, local, utc = a_zone_on_another_date(first_store["created_at"])
    check_date("Stores", shown(zone, "/#/stores", lambda page: page.locator(".store-date")), "Added", local, utc, zone)

    item = next(product for product in api.get("/api/products") if product["name"] == ITEM)
    zone, local, utc = a_zone_on_another_date(item["created_at"])
    check_date("Items", shown(zone, "/#/items", lambda page: page.locator(".product-row", has_text=ITEM).locator(".product-date")),
               "Added", local, utc, zone)

    admin = next(user for user in api.get("/api/users") if user["username"] == "admin")
    zone, local, utc = a_zone_on_another_date(admin["created_at"])
    check_date("Users", shown(zone, "/#/admin/users", lambda page: page.locator(".user-row", has_text="Admin").locator(".user-date")),
               "Created", local, utc, zone)

    # the purchase above is stored as 14:44 UTC on Sep 20, which is already Sep 21 in Kiritimati
    zone, local, utc = a_zone_on_another_date(PURCHASED_AT, with_year=False)
    check_date("Analytics", shown(zone, "/#/analytics", lambda page: page.locator(".freq-row", has_text=ITEM).locator(".freq-date")),
               "last:", local, utc, zone)

    browser.close()

finish()
