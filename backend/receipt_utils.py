"""Pure helpers for receipt import (no database, no network)."""

import math
import re
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

_KEY_JUNK = re.compile(r"[^A-Z0-9%]+")
_SQUASH_JUNK = re.compile(r"[^a-z0-9]")

# A receipt total may differ from lines + tax by a cent when the store rounds tax per item
TOTAL_TOLERANCE = 0.011


def finite(value, default=None):
    """The value if it is a finite number, else the default."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return value
    return default


def match_key(item_code: Optional[str], description: Optional[str]) -> Optional[str]:
    """Stable key for what a receipt line means at a store.

    Stores that print an item code get "code:<digits>"; the rest fall back to the
    normalized description ("text:DAISY CC 4% 16Z"). None when there is nothing to key on.
    """
    code = re.sub(r"\D", "", item_code or "")
    if code:
        return "code:" + code
    text = _KEY_JUNK.sub(" ", (description or "").upper()).strip()
    return "text:" + text if text else None


def squash(name: Optional[str]) -> str:
    """Lowercase letters and digits only, so "STOP&SHOP" and "Stop & Shop" compare equal."""
    return _SQUASH_JUNK.sub("", (name or "").lower())


def match_store(printed: Optional[str], candidates: Iterable[Tuple[int, List[str]]]) -> Optional[int]:
    """Pick the store a receipt was printed for.

    candidates is (store_id, [name and aliases]). An exact match after squashing wins;
    otherwise the store whose name overlaps the printed one the most (BJ's -> BJ's Wholesale Club).
    """
    p = squash(printed)
    if len(p) < 3:
        return None
    best_id, best_score = None, 0
    for store_id, names in candidates:
        for name in names:
            n = squash(name)
            if len(n) < 3:
                continue
            if p == n:
                return store_id
            if p in n or n in p:
                score = min(len(p), len(n))
                if score > best_score:
                    best_id, best_score = store_id, score
    return best_id


def net_amounts(lines) -> dict:
    """Position -> what was paid for each non-discount line, after the discounts attached to it.

    lines: objects with position, line_type, line_total and applies_to. A discount belongs to
    the line named by applies_to, or else the product line just above it.
    """
    amounts = {l.position: (l.line_total or 0.0) for l in lines if l.line_type != "discount"}
    product_positions = [l.position for l in lines if l.line_type == "product"]
    for line in lines:
        if line.line_type != "discount":
            continue
        target = line.applies_to if line.applies_to in amounts else None
        if target is None:
            earlier = [pos for pos in product_positions if pos < line.position]
            target = max(earlier) if earlier else None
        if target is not None:
            amounts[target] += line.line_total or 0.0
    return {pos: round(amount, 2) for pos, amount in amounts.items()}


def check_totals(lines, tax: Optional[float], total: Optional[float]) -> Optional[dict]:
    """Do the printed lines plus tax add up to the printed total? None when there is no total."""
    if total is None:
        return None
    lines_sum = round(sum((l.line_total or 0.0) for l in lines), 2)
    expected = round(lines_sum + (tax or 0.0), 2)
    return {
        "lines_sum": lines_sum,
        "expected_total": expected,
        "balanced": abs(expected - total) <= TOTAL_TOLERANCE,
    }


def category_from_section(section: Optional[str], known_categories: Iterable[str]) -> Optional[str]:
    """Use a receipt's department heading (DAIRY) as a category when it names one we already use."""
    wanted = re.sub(r"\s+", " ", (section or "").strip()).lower()
    if not wanted:
        return None
    for category in known_categories:
        if category.lower() == wanted:
            return category
    return None


_NAME_WORD = re.compile(r"[a-z]{4,}")


def category_from_similar_product(name: Optional[str], named_products: Iterable[Tuple[str, str]]) -> Optional[str]:
    """Guess a category for a new item from an already-categorized product with a similar name.

    named_products is (name, category). Matched on shared whole words of 4+ letters (so "Cottage
    Cheese" can borrow "Dairy" from an existing "Cheddar Cheese") to avoid noise from short words.
    """
    words = set(_NAME_WORD.findall((name or "").lower()))
    if not words:
        return None
    best_category, best_score = None, 0
    for product_name, category in named_products:
        score = len(words & set(_NAME_WORD.findall(product_name.lower())))
        if score > best_score:
            best_category, best_score = category, score
    return best_category


def clean_local_time(text: Optional[str]) -> Optional[str]:
    """Normalize a printed date/time to ISO 'YYYY-MM-DDTHH:MM' (local, no timezone), or None."""
    try:
        parsed = datetime.fromisoformat((text or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M")
