#!/bin/sh
cd "$(dirname "$0")"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "grok-remote needs Python 3.10+ (python3 not found)"; exit 1; }
"$PY" -c "import aiohttp" 2>/dev/null || "$PY" -m pip install --user aiohttp || { echo "could not install aiohttp; run: $PY -m pip install aiohttp"; exit 1; }
exec "$PY" server.py "$@"
