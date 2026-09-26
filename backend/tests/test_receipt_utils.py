from collections import namedtuple

import pytest

import receipt_utils as ru

Line = namedtuple("Line", "position line_type line_total applies_to")

# BJ's: five products, a coupon for the Poise line (position 3), a charity round-up
BJS = [
    Line(0, "product", 29.98, None),
    Line(1, "product", 4.99, None),
    Line(2, "product", 5.59, None),
    Line(3, "product", 44.97, None),
    Line(4, "discount", -2.5, 3),
    Line(5, "product", 8.99, None),
    Line(6, "fee", 0.08, None),
]


@pytest.mark.parametrize("code, text, expected", [
    (None, "DAISY CC 4% 16Z", "text:DAISY CC 4% 16Z"),
    ("74759943988", "GHIRARDELLI", "code:74759943988"),
    (" 36000 44037 ", "x", "code:3600044037"),
    (None, "lol  sprd-btr", "text:LOL SPRD BTR"),
    ("", "  ", None),
    (None, None, None),
])
def test_match_key(code, text, expected):
    assert ru.match_key(code, text) == expected


STORES = [(1, ["Stop & Shop"]), (2, ["BJ's Wholesale Club"]), (3, ["Costco", "Costco Wholesale"])]


@pytest.mark.parametrize("printed, expected", [
    ("STOP&SHOP", 1),
    ("BJ's", 2),
    ("COSTCO WHOLESALE #123", 3),
    ("Trader Joes", None),
    ("", None),
    (None, None),
])
def test_match_store(printed, expected):
    assert ru.match_store(printed, STORES) == expected


def test_a_coupon_is_folded_into_the_line_it_names():
    net = ru.net_amounts(BJS)
    assert net[3] == pytest.approx(42.47)
    assert 4 not in net  # the coupon has no amount of its own
    assert net[6] == pytest.approx(0.08)


def test_a_discount_without_a_target_goes_to_the_product_above():
    lines = [Line(0, "product", 10.0, None), Line(1, "product", 5.0, None), Line(2, "discount", -1.0, None)]
    assert ru.net_amounts(lines)[1] == pytest.approx(4.0)


def test_lines_plus_tax_are_checked_against_the_total():
    assert ru.check_totals(BJS, 1.90, 94.00)["balanced"]
    assert ru.check_totals(BJS, 1.90, 94.00)["lines_sum"] == pytest.approx(92.10)


def test_a_coupon_read_as_positive_is_flagged():
    flipped = BJS[:4] + [Line(4, "discount", 2.5, 3)] + BJS[5:]
    assert not ru.check_totals(flipped, 1.90, 94.00)["balanced"]


def test_a_cent_of_rounding_is_tolerated():
    assert ru.check_totals(BJS, 1.90, 94.01)["balanced"]
    assert not ru.check_totals(BJS, 1.90, 94.05)["balanced"]


def test_without_a_total_there_is_nothing_to_check():
    assert ru.check_totals(BJS, 1.90, None) is None


@pytest.mark.parametrize("text, expected", [
    ("2026-09-20T10:44:00", "2026-09-20T10:44"),
    ("2026-09-20T10:44:00Z", "2026-09-20T10:44"),
    ("2026-09-20", "2026-09-20T00:00"),
    ("garbage", None),
    ("", None),
    (None, None),
])
def test_clean_local_time(text, expected):
    assert ru.clean_local_time(text) == expected


@pytest.mark.parametrize("section, expected", [
    ("DAIRY", "Dairy"),
    ("  produce ", "Produce"),
    ("CONVENIENCE ITEMS", None),
    (None, None),
])
def test_a_department_heading_becomes_a_category_we_already_use(section, expected):
    assert ru.category_from_section(section, ["Dairy", "Produce"]) == expected


NAMED_PRODUCTS = [("Cheddar Cheese", "Dairy"), ("Sliced Strawberries", "Produce")]


@pytest.mark.parametrize("name, expected", [
    ("Cottage Cheese", "Dairy"),  # shares "cheese" with an existing Dairy product
    ("Large Strawberries", "Produce"),  # shares "strawberries" with an existing Produce product
    ("Paper Towels", None),  # no shared word with anything we already categorized
    ("", None),
    (None, None),
])
def test_a_new_item_can_borrow_a_category_from_a_similarly_named_product(name, expected):
    assert ru.category_from_similar_product(name, NAMED_PRODUCTS) == expected


@pytest.mark.parametrize("value, expected", [(1.5, 1.5), (0, 0), (float("nan"), None), (float("inf"), None), ("3", None), (True, None), (None, None)])
def test_finite(value, expected):
    assert ru.finite(value) == expected
