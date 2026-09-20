#!/usr/bin/env bash
# Browser tests: builds the app image from the working tree, runs it with the AI call replaced by
# receipt fixtures, and drives it with Playwright inside Docker. The first run pulls the Playwright
# image (about 1.7 GB).
#
#   tests/e2e/run.sh                              build shopping-list:e2e from the working tree and test it
#   IMAGE=shopping-list:v1.4.1 tests/e2e/run.sh   test an image that is already built
#   SCREENSHOT_DIR=/tmp/shots tests/e2e/run.sh    keep the screenshots the tests take
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
PLAYWRIGHT_VERSION=1.49.0
PLAYWRIGHT_IMAGE=mcr.microsoft.com/playwright/python:v$PLAYWRIGHT_VERSION-noble
NET=sl-e2e-$$
APP=sl-e2e-app-$$

IMAGE=${IMAGE:-}
if [ -z "$IMAGE" ]; then
  IMAGE=shopping-list:e2e
  echo "== building $IMAGE from the working tree"
  docker build -q -t "$IMAGE" "$ROOT" >/dev/null
fi

cleanup() {
  docker rm -f "$APP" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== starting the app ($IMAGE) with the AI call replaced"
docker network create "$NET" >/dev/null
docker run -d --name "$APP" --network "$NET" -e ADMIN_PASSWORD=e2e-pw -e JWT_SECRET=e2e \
  -v "$ROOT/backend/tests/receipt_fixtures.py:/tests/receipt_fixtures.py:ro" \
  -v "$HERE/serve_with_stub.py:/tests/serve_with_stub.py:ro" \
  "$IMAGE" python /tests/serve_with_stub.py >/dev/null

SHOTS=()
if [ -n "${SCREENSHOT_DIR:-}" ]; then
  mkdir -p "$SCREENSHOT_DIR"
  SHOTS=(-v "$SCREENSHOT_DIR:/out" -e SCREENSHOT_DIR=/out)
fi

echo "== running the browser tests"
docker run --rm --network "$NET" --ipc=host -e "BASE=http://$APP:8080" ${SHOTS[@]+"${SHOTS[@]}"} \
  -v "$HERE:/e2e:ro" "$PLAYWRIGHT_IMAGE" sh -c "
    pip install -q --break-system-packages playwright==$PLAYWRIGHT_VERSION >/dev/null 2>&1
    cd /e2e
    status=0
    python test_receipts_ui.py || status=1
    python test_local_times.py || status=1
    exit \$status"
