import os
from datetime import datetime

import pytest

import photo_utils
import receipt_extraction as rx
from helpers import hours_ago, jpeg
from models import HistoryEvent, Product, ProductStore, ReceiptItemMap
from receipt_fixtures import bjs, stop_shop

RECEIPTS_DIR = photo_utils.RECEIPT_DIR


# ---------- reading a photo into a draft ----------

def test_a_receipt_photo_becomes_a_draft_to_review(shop):
    cottage = shop.product("Cottage Cheese", "Dairy")
    butter = shop.product("Butter", "Dairy")
    shop.product("Bananas", "Produce")  # so "Produce" is a category the app already uses

    response = shop.upload(stop_shop(matched=(cottage, butter, None)))
    assert response.status_code == 201, response.text
    draft = response.json()
    lines = draft["lines"]

    assert draft["status"] == "pending"
    assert draft["store_name"] == "Stop & Shop"  # matched from the logo text STOP&SHOP
    assert draft["purchased_local"] == "2026-09-20T10:44"
    assert draft["uploaded_by"] == "admin"
    assert len(lines) == 4
    assert draft["check"]["balanced"]  # 18.00 of lines + 0.01 tax = the 18.01 BALANCE, with no subtotal printed
    assert draft["check"]["lines_sum"] == pytest.approx(18.00)

    assert lines[0]["product_id"] == cottage and lines[0]["match_source"] == "suggested"
    assert lines[2]["product_id"] is None and lines[2]["suggested_name"] == "Large Strawberries"
    assert lines[3]["line_type"] == "fee" and lines[3]["ignored"]  # the bag charge is not a product
    assert lines[0]["suggested_category"] == "Dairy" and lines[2]["suggested_category"] == "Produce"
    assert lines[3]["suggested_category"] is None  # CONVENIENCE ITEMS is not a category we use


def test_totals_that_do_not_add_up_are_flagged(shop):
    reading = stop_shop()
    reading.total = 25.00
    draft = shop.upload(reading).json()
    assert draft["check"]["balanced"] is False
    assert draft["check"]["expected_total"] == pytest.approx(18.01)


def test_receipt_photos_need_a_login_and_are_not_public(shop, anonymous):
    draft = shop.upload(stop_shop()).json()
    image_url = "/api/receipts/%d/images/%d" % (draft["id"], draft["image_ids"][0])

    assert shop.client.get(image_url).headers["content-type"] == "image/jpeg"
    assert anonymous.get(image_url).status_code in (401, 403)
    assert anonymous.get("/api/receipts").status_code in (401, 403)
    assert anonymous.get("/uploads/" + os.listdir(RECEIPTS_DIR)[0]).status_code == 404


def test_bad_uploads_are_refused(shop):
    not_an_image = [("files", ("x.jpg", b"nope", "image/jpeg"))]
    assert shop.upload(files=not_an_image).status_code == 400
    four_photos = [("files", ("r%d.jpg" % i, jpeg(), "image/jpeg")) for i in range(4)]
    assert shop.upload(files=four_photos).status_code == 400


def test_a_failed_reading_is_kept_and_can_be_retried(shop):
    failed = shop.upload(rx.ExtractionError("The AI service is busy. Try again in a minute.")).json()
    assert failed["status"] == "failed"
    assert "busy" in failed["error"]
    assert failed["lines"] == [] and len(failed["image_ids"]) == 1  # the photo is not lost

    shop.ai.append(stop_shop())
    retried = shop.client.post("/api/receipts/%d/extract" % failed["id"]).json()
    assert retried["status"] == "pending" and retried["error"] is None
    assert len(retried["lines"]) == 4


# ---------- confirming ----------

def test_every_line_must_be_reviewed_and_needs_a_product(shop):
    cottage = shop.product("Cottage Cheese")
    draft = shop.upload(stop_shop()).json()
    url = "/api/receipts/%d/confirm" % draft["id"]
    first = draft["lines"][0]

    only_one = {"store_id": shop.store["Stop & Shop"], "purchased_at": hours_ago(1),
                "lines": [{"id": first["id"], "product_id": cottage, "quantity": 1, "amount": 5.49}]}
    assert shop.client.post(url, json=only_one).status_code == 400

    no_product = dict(only_one, lines=[{"id": first["id"], "quantity": 1, "amount": 5.49}])
    assert shop.client.post(url, json=no_product).status_code == 422


def test_confirming_records_purchases_and_corrects_an_earlier_check_off(shop, morning):
    result = morning.result
    assert (result["recorded"], result["updated"], result["new_products"], result["removed_from_list"]) == (2, 1, 1, 2)
    assert result["receipt"]["status"] == "confirmed"
    assert shop.client.get("/api/list").json() == []  # the bought items left the list

    # butter was checked off at 4.50 in the app: corrected to the receipt, not counted twice
    (butter_event,) = shop.check_offs(morning.butter)
    assert butter_event.price == pytest.approx(4.79)
    assert butter_event.receipt_id == morning.draft["id"]
    assert butter_event.store_id == shop.store["Stop & Shop"]

    assert shop.spent_by_store()["Stop & Shop"] == pytest.approx(5.49 + 4.79 + 7.62)  # tax and bag fee are not items


def test_a_new_product_and_the_store_price_come_from_the_receipt(shop, morning, db):
    strawberries = db.query(Product).filter(Product.name == "Large Strawberries").one()
    assert strawberries.category == "Produce"
    link = db.query(ProductStore).filter(
        ProductStore.product_id == morning.butter, ProductStore.store_id == shop.store["Stop & Shop"]
    ).one()
    assert link.price == pytest.approx(4.79)


def test_what_the_lines_meant_is_learned_by_store(shop, morning, db):
    learned = {m.match_key: m.ignore for m in db.query(ReceiptItemMap).filter(ReceiptItemMap.store_id == shop.store["Stop & Shop"])}
    assert set(learned) == {"text:DAISY CC 4% 16Z", "text:LOL SPRD BTR 15Z", "text:SB LARGE STRWBRY"}


def test_a_receipt_cannot_be_confirmed_or_changed_twice(shop, morning):
    receipt_id = morning.draft["id"]
    again = {"store_id": shop.store["Stop & Shop"], "purchased_at": morning.purchased, "lines": []}
    assert shop.client.post("/api/receipts/%d/confirm" % receipt_id, json=again).status_code == 409
    assert shop.client.put("/api/receipts/%d" % receipt_id, json={"store_id": shop.store["Costco"]}).status_code == 409


def test_the_next_receipt_is_matched_from_what_was_learned(shop, morning):
    draft = shop.upload(stop_shop()).json()  # the AI matches nothing this time
    assert [l["match_source"] for l in draft["lines"][:3]] == ["learned"] * 3
    assert draft["lines"][0]["product_id"] == morning.cottage
    assert draft["lines"][2]["product_name"] == "Large Strawberries"

    result = shop.confirm(draft, shop.store["Stop & Shop"], morning.purchased,
                          [l["product_id"] for l in draft["lines"][:3]] + [None]).json()
    # receipt #1's purchases already belong to a receipt, so none of them are taken over
    assert (result["recorded"], result["updated"]) == (3, 0)


def test_choosing_the_store_by_hand_matches_the_lines(shop, morning):
    draft = shop.upload(stop_shop(store="MYSTERY MART")).json()
    assert draft["store_id"] is None and draft["lines"][0]["match_source"] is None

    updated = shop.client.put("/api/receipts/%d" % draft["id"], json={"store_id": shop.store["Stop & Shop"]}).json()
    assert updated["store_name"] == "Stop & Shop"
    assert updated["lines"][0]["match_source"] == "learned"


def test_a_check_off_from_another_day_is_not_taken_over(shop):
    butter = shop.product("Butter")
    shop.check_off(shop.add_to_list(butter), shop.store["Stop & Shop"], 4.50)  # ticked off just now
    draft = shop.upload(stop_shop(matched=(None, butter, None))).json()

    result = shop.confirm(draft, shop.store["Stop & Shop"], hours_ago(24 * 5), [None, butter, None, None]).json()
    assert (result["recorded"], result["updated"]) == (1, 0)
    assert len(shop.check_offs(butter)) == 2


def test_an_old_receipt_uploaded_late_does_not_overwrite_the_newer_store_price(shop, morning, db):
    old = stop_shop()
    old.lines[0].unit_price = old.lines[0].line_total = 3.00
    draft = shop.upload(old).json()
    result = shop.confirm(draft, shop.store["Stop & Shop"], "2026-01-05T15:00:00Z",
                          [morning.cottage, morning.butter, "Large Strawberries", None])
    assert result.status_code == 200, result.text

    price = db.query(ProductStore).filter(
        ProductStore.product_id == morning.cottage, ProductStore.store_id == shop.store["Stop & Shop"]
    ).one().price
    assert price == pytest.approx(5.49)  # the newer price stays
    january = db.query(HistoryEvent).filter(HistoryEvent.receipt_id == draft["id"], HistoryEvent.product_id == morning.cottage).one()
    assert january.price == pytest.approx(3.00)  # but the purchase is in the history, on its own date
    assert january.timestamp == datetime(2026, 1, 5, 15, 0)


# ---------- a receipt with item codes, a coupon and a round-up ----------

def test_bjs_receipt_folds_the_coupon_and_leaves_out_the_round_up(shop, db):
    draft = shop.upload(bjs()).json()
    lines = draft["lines"]
    assert draft["store_name"] == "BJ's Wholesale Club"  # matched by overlap with BJ's
    assert draft["check"]["balanced"] and draft["check"]["lines_sum"] == pytest.approx(92.10)
    assert lines[3]["net_amount"] == pytest.approx(42.47)  # 44.97 less the 2.50 coupon
    assert lines[4]["line_type"] == "discount" and lines[4]["net_amount"] is None
    assert lines[6]["ignored"]  # the charity round-up

    choices = [l["suggested_name"] for l in lines if l["line_type"] == "product"] + [None]
    result = shop.confirm(draft, shop.store["BJ's Wholesale Club"], "2026-09-10T00:26:00Z", choices).json()
    assert result["recorded"] == 5 and result["new_products"] == 5

    # 94.00 paid = 92.02 of items + 1.90 tax + 0.08 round-up
    assert shop.spent_by_store()["BJ's Wholesale Club"] == pytest.approx(92.02)
    poise = db.query(Product).filter(Product.name == "Poise Liners").one()
    event = db.query(HistoryEvent).filter(HistoryEvent.product_id == poise.id).one()
    assert event.quantity == 3 and event.price * event.quantity == pytest.approx(42.47)  # no rounding drift
    assert event.timestamp == datetime(2026, 9, 10, 0, 26)  # stored as UTC


# ---------- listing, merging, undoing ----------

def test_receipts_are_listed_with_their_status(shop, morning):
    shop.upload(bjs())
    listing = shop.client.get("/api/receipts").json()
    assert sorted(r["status"] for r in listing) == ["confirmed", "pending"]
    by_status = {r["status"]: r for r in listing}
    assert by_status["confirmed"]["line_count"] == 4
    assert by_status["pending"]["line_count"] == 6  # the folded coupon is not a line to review


def test_merging_stores_moves_receipts_and_what_they_taught(shop, morning, db):
    temp = shop.client.post("/api/stores", json={"name": "Temp Store"}).json()["id"]
    draft = shop.upload(stop_shop(store="TEMP STORE")).json()
    choices = [l["suggested_name"] for l in draft["lines"][:3]] + [None]
    assert shop.confirm(draft, temp, morning.purchased, choices).status_code == 200

    assert shop.client.post("/api/stores/%d/merge/%d" % (shop.store["Stop & Shop"], temp)).status_code == 200
    assert shop.client.get("/api/receipts/%d" % draft["id"]).json()["store_name"] == "Stop & Shop"
    assert db.query(ReceiptItemMap).filter(ReceiptItemMap.store_id == temp).count() == 0


def test_deleting_a_receipt_takes_its_purchases_back_out(shop, morning):
    photos_before = len(os.listdir(RECEIPTS_DIR))
    assert shop.client.delete("/api/receipts/%d" % morning.draft["id"]).status_code == 204

    assert shop.client.get("/api/receipts/%d" % morning.draft["id"]).status_code == 404
    assert len(os.listdir(RECEIPTS_DIR)) == photos_before - 1  # its photo is deleted too
    # the check-off the receipt had corrected is given back as it was
    (butter_event,) = shop.check_offs(morning.butter)
    assert butter_event.price == pytest.approx(4.50)
    assert butter_event.receipt_id is None
    assert butter_event.store_id == shop.store["Stop & Shop"]
    assert shop.check_offs(morning.cottage) == []
    assert shop.spent_by_store()["Stop & Shop"] == pytest.approx(4.50)


def test_deleting_a_draft_that_was_never_confirmed(shop):
    draft = shop.upload(stop_shop()).json()
    assert shop.client.delete("/api/receipts/%d" % draft["id"]).status_code == 204
    assert shop.client.get("/api/receipts").json() == []
