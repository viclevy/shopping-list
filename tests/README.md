# Tests

## Backend (pytest)

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The tests run the real app in-process against a throwaway data directory, so they never touch
real data. The AI call is always replaced, so nothing reaches the network and no API key is needed.

| File | What it covers |
|---|---|
| `test_receipt_utils.py` | matching keys, store matching, coupons folded into the line they reduce, the lines-plus-tax check |
| `test_receipt_extraction.py` | retries and error messages of the AI call |
| `test_receipt_images.py` | saving receipt photos (phone rotation, size, kept out of the public uploads folder) |
| `test_receipts_api.py` | reading a photo into a draft, confirming, correcting an earlier check-off, learned matches, merging stores, undo |
| `test_migration.py` | starting the code on a database made before receipts existed |
| `receipt_fixtures.py` | what the AI returns for two real receipts (BJ's and Stop & Shop) |

## Browser tests (Playwright, in Docker)

```bash
tests/e2e/run.sh
```

Builds the app image from the working tree, runs it with only the AI call replaced by the receipt
fixtures, and drives it with Playwright in a container. It needs Docker; the first run pulls the
Playwright image (about 1.7 GB, `docker rmi mcr.microsoft.com/playwright/python:v1.49.0-noble` frees it).
Console errors and warnings fail the run, so a missing translation is caught.

```bash
IMAGE=shopping-list:v1.4.1 tests/e2e/run.sh    # test an image that is already built
SCREENSHOT_DIR=/tmp/shots tests/e2e/run.sh     # keep the screenshots the tests take
```

| File | What it covers |
|---|---|
| `test_receipts_ui.py` | upload, review, confirm, remembered matches, a failed reading and retry, the product picker, changing the store, deleting, Hebrew right-to-left and the other languages |
| `test_local_times.py` | times are shown in the viewer's timezone, not as the stored UTC clock time |
| `serve_with_stub.py` | the real app with a fake AI call you queue readings for (`POST /__stub/next`) |
