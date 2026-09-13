#!/usr/bin/env bash
CHROME="${CHROME:-/c/Users/antho/.cache/puppeteer/chrome/win64-131.0.6778.204/chrome-win64/chrome.exe}"
KEY="${XR_KEY:-***REMOVED***}"
PAGE="${1:-motion-lab.html}"
WANT="${2:-lab ok}"
DOM=$("$CHROME" --headless=new --disable-gpu --enable-unsafe-swiftshader --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:2421/static/$PAGE?key=$KEY" 2>/dev/null)
T=$(printf '%s' "$DOM" | grep -o "<title>[^<]*</title>")
printf '%s -> %s\n' "$PAGE" "$T"
printf '%s' "$T" | grep -q "$WANT" && echo "PASS" || { echo "FAIL: module did not reach its sentinel"; exit 1; }
