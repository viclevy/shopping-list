"""Times are shown in the viewer's own timezone, not as the UTC clock time the server stores."""

from playwright.sync_api import sync_playwright

from common import BASE, PNG, Api, check, finish, login, screenshot, wait_for_app, watch

# The purchase below happened at 14:44 UTC on Sep 20, 2026
PURCHASED_AT = "2026-09-20T14:44:00Z"
ITEM = "Local Time Test Item"

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

    browser.close()

finish()
