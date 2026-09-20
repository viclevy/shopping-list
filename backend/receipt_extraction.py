"""Read a receipt photo into structured lines with a vision model.

This is the only module that talks to the AI service. To switch provider, add a
_call_<provider> function and a branch in extract().
"""

import logging
import time
from typing import List, Literal, Optional, Tuple

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)

RETRY_DELAYS = (2, 5, 12)  # seconds before each retry when the service is busy or rate limited
REQUEST_TIMEOUT_MS = 60_000
MAX_CATALOG = 500  # known products offered to the model for matching


class ExtractionError(Exception):
    """The receipt could not be read. The message is safe to show to users."""


class ExtractedLine(BaseModel):
    item_code: Optional[str] = Field(
        description="Item or UPC number printed on the line, digits only, or null if the store prints none")
    description: str = Field(description="Item text exactly as printed")
    suggested_name: Optional[str] = Field(
        description="Plain product name with abbreviations expanded (e.g. 'Cottage Cheese'), or null if you cannot tell what it is")
    section: Optional[str] = Field(
        description="Department heading printed above the line (e.g. DAIRY), or null")
    line_type: Literal["product", "discount", "fee"]
    quantity: float = Field(description="Number of units bought")
    unit_price: float = Field(description="Price of one unit; negative for discounts")
    line_total: float = Field(description="Amount for the whole line; negative for discounts")
    taxable: bool = Field(description="True if the line carries the store's taxable flag")
    applies_to_line: Optional[int] = Field(
        description="For a discount: the 0-based index in lines of the line it reduces, else null")
    matched_product_id: Optional[int] = Field(
        description="Id of the known product this line is, chosen only from the provided list, or null")


class ExtractedReceipt(BaseModel):
    store_name: str
    purchased_at: str = Field(description="Local date and time, ISO 8601 without timezone")
    lines: List[ExtractedLine]
    subtotal: Optional[float] = Field(description="Printed subtotal, or null when the receipt has none")
    tax: Optional[float] = Field(description="Total tax, 0 if none is printed")
    total: float = Field(description="Amount charged (labelled TOTAL, BALANCE or similar)")


PROMPT = """Read the attached grocery receipt (one receipt, possibly photographed in several parts, in order) and extract it into the schema.

Conventions on US receipts:
- The amount at the end of an item line is the total for that line. If the next line reads "N @ price", quantity is N and unit_price is that price. Otherwise quantity is 1 and unit_price equals the line total.
- A trailing "-" on an amount (e.g. "2.50-") is a negative amount. Coupon and discount lines are line_type "discount" with negative unit_price and line_total, and applies_to_line set to the index in lines of the line they reduce (usually the one just above).
- Bag charges, deposits and charity round-ups are line_type "fee", not products.
- Department headings (DAIRY, PRODUCE, ...) are not lines. Put the heading in `section` of every line below it, until the next heading.
- Sizes and counts inside a description ("5 CT", "16Z") are not the quantity.
- `taxable` is true only when the line carries the store's taxable flag (usually "T").
- `total` is the amount charged, whatever it is labelled. `subtotal` is null if the receipt prints none. `tax` is the sum of the tax lines.
- Skip summary and savings blocks ("you saved ..."), payment details, card and loyalty numbers, staff names, and survey or promo text.
- Dates are MM/DD/YY. Give purchased_at as local 24-hour ISO 8601 without timezone (2026-09-20T10:44:00), using the transaction time at the top.
- Copy `description` exactly as printed. For suggested_name, expand obvious abbreviations into a plain product name. If you cannot tell what an item is, leave suggested_name null instead of guessing.
- Set matched_product_id only when a known product below is clearly the same item. Never invent an id."""


def build_prompt(catalog: List[Tuple[int, str]]) -> str:
    known = "\n".join("%d: %s" % (pid, name) for pid, name in catalog[:MAX_CATALOG])
    return PROMPT + "\n\nKnown products (id: name):\n" + (known or "(none yet)")


def _explain(error: genai_errors.APIError) -> str:
    code = getattr(error, "code", None)
    if "API key" in str(error) or code in (401, 403):
        return "The AI service rejected the API key (GEMINI_API_KEY)."
    if code == 404:
        return "The AI model was not found (GEMINI_MODEL)."
    if code == 429:
        return "The AI service is over its quota. Try again later."
    if code and code >= 500:
        return "The AI service is busy. Try again in a minute."
    return "The AI service could not read the receipt."


def _call_gemini(images: List[bytes], prompt: str) -> ExtractedReceipt:
    if not settings.gemini_api_key:
        raise ExtractionError("No AI service key is configured (GEMINI_API_KEY).")
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
    contents = [types.Part.from_bytes(data=data, mime_type="image/jpeg") for data in images]
    contents.append(prompt)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedReceipt,
            temperature=0,
        ),
    )
    return ExtractedReceipt.model_validate_json(response.text)


def extract(images: List[bytes], catalog: List[Tuple[int, str]]) -> ExtractedReceipt:
    """Read the receipt photos. catalog is (id, name) of known products for matching.

    Blocking (retries sleep), so call it from a worker thread. Raises ExtractionError.
    """
    if settings.receipt_provider != "gemini":
        raise ExtractionError("Unknown receipt provider %r (RECEIPT_PROVIDER)." % settings.receipt_provider)
    prompt = build_prompt(catalog)
    attempts = len(RETRY_DELAYS) + 1
    for attempt in range(attempts):
        last = attempt == attempts - 1
        try:
            result = _call_gemini(images, prompt)
        except ExtractionError:
            raise
        except genai_errors.APIError as e:
            logger.warning("Receipt reading attempt %d/%d failed: %s: %s", attempt + 1, attempts, type(e).__name__, e)
            if getattr(e, "code", None) in (429, 500, 502, 503, 504) and not last:
                time.sleep(RETRY_DELAYS[attempt])
                continue
            raise ExtractionError(_explain(e)) from e
        except httpx.HTTPError as e:
            logger.warning("Receipt reading attempt %d/%d failed: %s: %s", attempt + 1, attempts, type(e).__name__, e)
            if not last:
                time.sleep(RETRY_DELAYS[attempt])
                continue
            raise ExtractionError("The AI service did not answer in time. Try again in a minute.") from e
        except (ValueError, TypeError) as e:  # includes pydantic validation errors and an empty answer
            logger.warning("Receipt reading attempt %d/%d gave an unusable answer: %s", attempt + 1, attempts, e)
            if not last:
                continue
            raise ExtractionError("The AI service gave an answer the app could not understand.") from e
        if not result.lines:
            raise ExtractionError("No items were found on that photo. Is it a grocery receipt?")
        return result
