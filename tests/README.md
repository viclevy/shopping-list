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
