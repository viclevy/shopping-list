"""Runs the real app with only the AI call replaced by receipt fixtures, for the browser tests.

    POST /__stub/next  {"fixture": "stop_shop" | "stop_shop_suggested" | "bjs" | "error"}

queues what the next reading returns. With nothing queued a reading returns the plain
Stop & Shop receipt. "stop_shop_suggested" is the same receipt with two lines already matched
to the known products Cottage Cheese and Butter, the way the AI does when it recognises them.
"""

import os
import sys

sys.path.insert(0, os.getcwd())  # the app (the image's working directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # receipt_fixtures.py, mounted next to this file

import uvicorn  # noqa: E402
from fastapi import Body  # noqa: E402

import receipt_extraction as rx  # noqa: E402
from receipt_fixtures import bjs, stop_shop  # noqa: E402

queue = []


def fake_extract(images, catalog):
    fixture = queue.pop(0) if queue else "stop_shop"
    print("reading #%s: %s (%d image(s), %d known products)" % (len(queue), fixture, len(images), len(catalog)), flush=True)
    if fixture == "error":
        raise rx.ExtractionError("The AI service is busy. Try again in a minute.")
    if fixture == "bjs":
        return bjs()
    if fixture == "stop_shop_suggested":
        ids = {name: pid for pid, name in catalog}
        return stop_shop(matched=(ids.get("Cottage Cheese"), ids.get("Butter"), None))
    return stop_shop()


rx.extract = fake_extract

import main  # noqa: E402


@main.app.post("/__stub/next")
def queue_next(fixture: str = Body(..., embed=True)):
    queue.append(fixture)
    return {"queued": len(queue)}


uvicorn.run(main.app, host="0.0.0.0", port=8080, log_level="warning")
