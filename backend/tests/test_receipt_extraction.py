"""The AI call: retries, and errors that say what went wrong. The SDK call itself is replaced."""

import pytest
from google.genai import errors as genai_errors

import receipt_extraction as rx
from receipt_fixtures import bjs


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(rx.time, "sleep", lambda seconds: None)


def replace_call(monkeypatch, behaviour):
    """Replace the SDK call; behaviour(n) gets the call number (1 based) and returns a receipt or raises."""
    calls = {"n": 0}

    def fake(images, prompt):
        calls["n"] += 1
        return behaviour(calls["n"])

    monkeypatch.setattr(rx, "_call_gemini", fake)
    return calls


def server_error(code, status, message="busy"):
    error_class = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return error_class(code, {"error": {"message": message, "status": status}})


def test_a_busy_service_is_retried_until_it_answers(monkeypatch):
    def behaviour(n):
        if n < 3:
            raise server_error(503, "UNAVAILABLE")
        return bjs()

    calls = replace_call(monkeypatch, behaviour)
    result = rx.extract([b"x"], [(1, "Milk")])
    assert calls["n"] == 3
    assert len(result.lines) == 7


@pytest.mark.parametrize("error, attempts, message", [
    (server_error(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key."), 1, "API key"),
    (server_error(403, "PERMISSION_DENIED", "denied"), 1, "API key"),
    (server_error(404, "NOT_FOUND", "model gone"), 1, "model was not found"),
    (server_error(429, "RESOURCE_EXHAUSTED", "quota"), 4, "over its quota"),
    (server_error(503, "UNAVAILABLE"), 4, "busy"),
    (server_error(400, "INVALID_ARGUMENT", "something else"), 1, "could not read the receipt"),
    (ValueError("bad json"), 4, "could not understand"),
])
def test_failures_are_explained_and_only_temporary_ones_are_retried(monkeypatch, error, attempts, message):
    def behaviour(n):
        raise error

    calls = replace_call(monkeypatch, behaviour)
    with pytest.raises(rx.ExtractionError) as raised:
        rx.extract([b"x"], [])
    assert message in str(raised.value)
    assert calls["n"] == attempts


def test_a_reading_with_no_items_is_reported(monkeypatch):
    replace_call(monkeypatch, lambda n: rx.ExtractedReceipt(
        store_name="x", purchased_at="", lines=[], subtotal=None, tax=0, total=0))
    with pytest.raises(rx.ExtractionError, match="No items"):
        rx.extract([b"x"], [])


def test_the_known_products_are_offered_to_the_model():
    prompt = rx.build_prompt([(12, "Butter"), (13, "Cottage Cheese")])
    assert "12: Butter" in prompt and "13: Cottage Cheese" in prompt


def test_the_catalog_is_capped():
    catalog = [(i, "Product %d" % i) for i in range(rx.MAX_CATALOG + 50)]
    prompt = rx.build_prompt(catalog)
    assert "Product %d" % (rx.MAX_CATALOG - 1) in prompt
    assert "Product %d" % rx.MAX_CATALOG not in prompt


def test_a_missing_key_is_reported_without_calling_out(monkeypatch):
    monkeypatch.setattr(rx.settings, "gemini_api_key", "")
    with pytest.raises(rx.ExtractionError, match="GEMINI_API_KEY"):
        rx._call_gemini([b"x"], "prompt")


def test_an_unknown_provider_is_reported(monkeypatch):
    monkeypatch.setattr(rx.settings, "receipt_provider", "nope")
    with pytest.raises(rx.ExtractionError, match="RECEIPT_PROVIDER"):
        rx.extract([b"x"], [])
