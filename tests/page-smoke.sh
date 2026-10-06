#!/usr/bin/env bash
CHROME="${CHROME:-$(command -v google-chrome-stable || command -v google-chrome || command -v chromium || echo chrome)}"
HUB="${HUB:-http://127.0.0.1:2421}"
KEY="${XR_KEY:-$(cat "$(dirname "$0")/../.ui-secret" 2>/dev/null)}"
PAGE="${1:-motion-lab.html}"
WANT="${2:-lab ok}"
DOM=$("$CHROME" --headless=new --disable-gpu --enable-unsafe-swiftshader --virtual-time-budget=15000 --dump-dom "$HUB/static/$PAGE?key=$KEY" 2>/dev/null)
T=$(printf '%s' "$DOM" | grep -o "<title>[^<]*</title>")
printf '%s -> %s\n' "$PAGE" "$T"
printf '%s' "$T" | grep -q "$WANT" && echo "PASS" || { echo "FAIL: module did not reach its sentinel"; exit 1; }
