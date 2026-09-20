"""The receipt screens in a real browser: upload, review, confirm, remembered matches, a failed
reading and retry, the product picker, changing the store, deleting, other languages."""

import re
import time

from playwright.sync_api import sync_playwright

from common import BASE, Api, check, finish, login, screenshot, wait_for_app, watch

ANY_RECEIPT = re.compile(r".*#/receipts/\d+$")


def upload_photo(page):
    """Stage one photo (any image will do, the AI call is replaced) and have it read."""
    png = page.screenshot()
    page.set_input_files("input[type=file][multiple]", {"name": "receipt.png", "mimeType": "image/png", "buffer": png})
    page.wait_for_selector(".thumb")
    page.get_by_role("button", name="Read receipt").click()
    page.wait_for_url(ANY_RECEIPT)


def selected_store(page):
    return page.eval_on_selector("#receipt-store", "e => e.options[e.selectedIndex].text")


def record_purchases(page):
    page.get_by_role("button", name="Record purchases").click()
    page.wait_for_selector(".success")
    return page.locator(".success").inner_text()


wait_for_app()
with sync_playwright() as p:
    browser = p.chromium.launch()

    api = Api(p)
    cottage = api.post("/api/products", {"name": "Cottage Cheese", "category": "Dairy"})["id"]
    butter = api.post("/api/products", {"name": "Butter", "category": "Dairy"})["id"]
    api.post("/api/products", {"name": "Bananas", "category": "Produce"})
    api.post("/api/list", {"product_id": cottage, "quantity": 1})
    api.post("/api/list", {"product_id": butter, "quantity": 1})

    # ---------------- mobile ----------------
    context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                  has_touch=True, locale="en-US", timezone_id="America/New_York")
    page = context.new_page()
    watch(page, "mobile")
    page.on("dialog", lambda dialog: dialog.accept())
    login(page)
    page.wait_for_selector(".list-item")
    check(page.locator(".list-item").count() == 2, "the seeded list has 2 items")

    page.click(".hamburger-btn")
    page.click('.mobile-nav a[href="#/receipts"]')
    page.wait_for_selector("h2:has-text('Receipts')")
    page.get_by_text("No receipts yet.").wait_for()
    time.sleep(0.5)  # let the menu finish sliding away
    screenshot(page, "1-mobile-receipts-empty")

    # --- receipt 1: Stop & Shop, two lines already matched by the AI
    api.next_reading("stop_shop_suggested")
    upload_photo(page)
    page.wait_for_selector(".line")
    check(selected_store(page) == "Stop & Shop", "the store is matched from STOP&SHOP: %s" % selected_store(page))
    check(page.input_value("#receipt-when") == "2026-09-20T10:44", "the time is prefilled: %s" % page.input_value("#receipt-when"))
    check("add up" in page.locator(".ok").inner_text(), "the totals balance")
    check(page.locator(".line").count() == 4, "4 lines")
    check(page.locator(".line").nth(0).locator(".chosen strong").inner_text() == "Cottage Cheese", "line 1 is matched")
    check(page.locator(".line").nth(0).locator(".badge.suggested").count() == 1, "line 1 shows the 'suggested' badge")
    check(page.locator(".line").nth(2).locator(".new-product input").nth(0).input_value() == "Large Strawberries", "line 3 proposes a new product")
    check(page.locator(".line").nth(2).locator(".new-product input").nth(1).input_value() == "Produce", "line 3 takes its category from the PRODUCE heading")
    check(page.locator(".line.skipped").count() == 1 and page.locator(".line.skipped .badge").inner_text() == "Fee", "the bag charge starts skipped as a fee")
    check(page.get_by_role("button", name="Record purchases").is_enabled(), "confirming is possible")
    check(page.locator(".thumb").count() == 1, "the receipt photo is shown (loaded with the login)")
    screenshot(page, "2-mobile-review", full_page=True)

    page.locator(".thumb").click()
    check(page.locator(".viewer img").is_visible(), "the photo opens full size")
    page.locator(".viewer").click()

    summary = record_purchases(page)
    check("3 purchases recorded" in summary and "1 new product created" in summary and "2 items removed from your list" in summary,
          "summary: %r" % summary)
    check(page.locator(".status.confirmed").count() == 1, "the receipt shows as recorded")
    recorded = page.locator(".recorded-lines").inner_text()
    check("Cottage Cheese" in recorded and "Butter" in recorded and "Large Strawberries" in recorded, "the recorded lines name the products")
    screenshot(page, "3-mobile-recorded", full_page=True)

    page.goto(BASE + "/#/")
    page.wait_for_selector(".app-header")
    time.sleep(1)
    check(page.locator(".list-item").count() == 0, "the bought items left the shopping list")

    # the time typed as 10:44 in New York is what History shows for the purchase
    page.goto(BASE + "/#/history")
    page.wait_for_selector(".event-row")
    purchase = page.locator(".event-row", has_text="Cottage Cheese").filter(has=page.locator(".event-action.checked_off")).first
    meta = purchase.locator(".event-meta").inner_text()
    check("10:44 AM" in meta, "History shows the purchase at the receipt's time: %r" % " ".join(meta.split()))

    # --- receipt 2: everything is remembered from receipt 1
    page.goto(BASE + "/#/receipts")
    page.wait_for_selector(".receipt-row")
    upload_photo(page)
    page.wait_for_selector(".line")
    check(page.locator(".badge.learned").count() == 3, "second receipt: 3 lines are remembered (%d)" % page.locator(".badge.learned").count())
    check(page.locator(".line").nth(2).locator(".chosen strong").inner_text() == "Large Strawberries", "the new product was learned too")
    check("3 purchases recorded" in record_purchases(page), "the second receipt is recorded")

    # --- receipt 3: the reading fails, then a retry gives the BJ's receipt
    page.goto(BASE + "/#/receipts")
    page.wait_for_selector(".receipt-row")
    api.next_reading("error")
    api.next_reading("bjs")
    upload_photo(page)
    page.wait_for_selector("h3")
    check("couldn't be read" in page.locator("h3").inner_text(), "a failed reading is explained")
    check("busy" in page.locator(".error").first.inner_text(), "with the reason: %r" % page.locator(".error").first.inner_text())
    screenshot(page, "4-mobile-failed")
    page.get_by_role("button", name="Try again").click()
    page.wait_for_selector(".line")
    check(selected_store(page) == "BJ's Wholesale Club", "BJ's is matched: %s" % selected_store(page))
    check(page.locator(".line").count() == 6, "6 lines to review, the coupon folded into Poise: %d" % page.locator(".line").count())
    poise = page.locator(".line", has_text="POISE LINER")
    check(poise.locator(".numbers input").nth(1).input_value() == "42.47", "Poise shows its amount after the coupon")
    check("was $44.97" in poise.locator(".hint").inner_text(), "with a note about the coupon")
    check(page.locator(".line.skipped", has_text="DANAFARBER").count() == 1, "the round-up donation starts skipped")
    check("add up" in page.locator(".ok").inner_text(), "BJ's totals balance")
    screenshot(page, "5-mobile-bjs", full_page=True)

    # the product picker: swap an unknown line for an existing product
    first = page.locator(".line").nth(0)
    first.get_by_role("button", name="Choose an existing product").click()
    check(first.locator(".picker input").input_value() == "Ghirardelli Chocolate", "the picker starts from the suggested name")
    first.locator(".picker input").fill("cott")
    first.locator(".suggestions li", has_text="Cottage Cheese").dispatch_event("mousedown")
    check(first.locator(".chosen strong").inner_text() == "Cottage Cheese", "an existing product can be picked")
    first.locator(".numbers input").nth(1).fill("abc")
    check(page.get_by_role("button", name="Record purchases").is_disabled(), "an invalid amount blocks confirming")
    first.locator(".numbers input").nth(1).fill("29.98")
    check(page.get_by_role("button", name="Record purchases").is_enabled(), "fixing it allows confirming again")

    # choosing another store keeps what was edited
    page.select_option("#receipt-store", label="Costco")
    time.sleep(1)
    check(selected_store(page) == "Costco", "the store can be changed")
    check(page.locator(".line").nth(0).locator(".chosen strong").inner_text() == "Cottage Cheese", "an edited line survives a store change")

    page.get_by_role("button", name="Delete receipt").click()
    page.wait_for_url("**/#/receipts")
    page.wait_for_selector(".receipt-row")
    check(page.locator(".receipt-row").count() == 2, "the deleted draft is gone from the list: %d rows" % page.locator(".receipt-row").count())
    check(page.locator(".status.confirmed").count() == 2, "two recorded receipts are listed")
    screenshot(page, "6-mobile-receipts-list", full_page=True)

    # ---------------- desktop ----------------
    desktop = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US", timezone_id="America/New_York")
    dpage = desktop.new_page()
    watch(dpage, "desktop")
    login(dpage)
    dpage.goto(BASE + "/#/receipts")
    dpage.wait_for_selector(".receipt-row")
    check(dpage.locator('.header-nav a[href="#/receipts"]').count() == 1, "the desktop navigation has Receipts")
    upload_photo(dpage)
    dpage.wait_for_selector(".line")
    screenshot(dpage, "7-desktop-review", full_page=True)
    review_url = dpage.url

    # ---------------- other languages ----------------
    for language in ("he", "de", "ja", "es"):
        dpage.evaluate("l => localStorage.setItem('language', l)", language)
        dpage.goto(BASE + "/#/receipts")
        dpage.reload()
        dpage.wait_for_selector(".receipt-row")
        dpage.goto(review_url)
        dpage.reload()
        dpage.wait_for_selector(".line")
        text = dpage.locator(".receipt-view").inner_text()
        check("receipts." not in text and "common." not in text, "%s: no untranslated keys on screen" % language)
        if language == "he":
            check(dpage.evaluate("document.documentElement.dir") == "rtl", "Hebrew is right-to-left")
        screenshot(dpage, "8-%s-review" % language, full_page=True)
    dpage.evaluate("localStorage.setItem('language', 'en')")

    browser.close()

finish()
