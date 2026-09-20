"""What the AI call returns for the two real receipts the receipt import was built from.

Shared by the backend tests and the browser tests (which run the real app with only the
AI call replaced), so it only depends on receipt_extraction.
"""

import receipt_extraction as rx


def line(code, desc, typ, qty, unit, total, taxable=False, applies=None, section=None, suggested=None, matched=None):
    return rx.ExtractedLine(
        item_code=code, description=desc, suggested_name=suggested, section=section, line_type=typ,
        quantity=qty, unit_price=unit, line_total=total, taxable=taxable, applies_to_line=applies,
        matched_product_id=matched,
    )


def bjs():
    """BJ's, 09/09/26: item codes, 2 @ 14.99 lines, a coupon with a trailing minus, a charity round-up."""
    return rx.ExtractedReceipt(
        store_name="BJ's", purchased_at="2026-09-09T20:26:00",
        lines=[
            line("74759943988", "GHIRARDELLI", "product", 2, 14.99, 29.98, taxable=True, suggested="Ghirardelli Chocolate"),
            line("88867011075", "AVOCADO 5 CT", "product", 1, 4.99, 4.99, suggested="Avocados"),
            line("4138309072", "LACTAID MILK", "product", 1, 5.59, 5.59, suggested="Lactaid Milk"),
            line("3600044037", "POISE LINER", "product", 3, 14.99, 44.97, suggested="Poise Liners"),
            line("23389097", "ECPN-POISE L", "discount", 1, -2.5, -2.5, applies=3),
            line("88867003561", "EGGS", "product", 1, 8.99, 8.99, suggested="Eggs"),
            line("361061", "DANAFARBER", "fee", 1, 0.08, 0.08),
        ],
        subtotal=92.10, tax=1.90, total=94.00,
    )


def stop_shop(matched=(None, None, None), store="STOP&SHOP"):
    """Stop & Shop, 09/20/26: no item codes, department headings, no subtotal, a bag fee, total labelled BALANCE."""
    return rx.ExtractedReceipt(
        store_name=store, purchased_at="2026-09-20T10:44:00",
        lines=[
            line(None, "DAISY CC 4% 16Z", "product", 1, 5.49, 5.49, section="DAIRY", suggested="Cottage Cheese", matched=matched[0]),
            line(None, "LOL SPRD BTR 15Z", "product", 1, 4.79, 4.79, section="DAIRY", suggested="Butter Spread", matched=matched[1]),
            line(None, "SB LARGE STRWBRY", "product", 1, 7.62, 7.62, section="PRODUCE", suggested="Large Strawberries", matched=matched[2]),
            line(None, "MR CHCKOUT BAG CHG NP", "fee", 1, 0.10, 0.10, taxable=True, section="CONVENIENCE ITEMS"),
        ],
        subtotal=None, tax=0.01, total=18.01,
    )
