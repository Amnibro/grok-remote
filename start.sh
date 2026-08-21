#!/bin/sh
cd "$(dirname "$0")"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "grok-remote needs Python 3.10+ (python3 not found)"; exit 1; }
"$PY" -c "import aiohttp" 2>/dev/null || "$PY" -m pip install --user aiohttp || { echo "could not install aiohttp; run: $PY -m pip install aiohttp"; exit 1; }
[ -n "$GROK_AGENT_SECRET" ] || { [ -f .ui-secret ] || "$PY" -c "import secrets;open('.ui-secret','w').write(secrets.token_hex(16))"; GROK_AGENT_SECRET="$(cat .ui-secret)"; export GROK_AGENT_SECRET; }
exec "$PY" server.py "$@"
