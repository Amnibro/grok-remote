#!/bin/sh
cd "$(dirname "$0")" || exit 1
DATA="${GROK_PLUGIN_DATA:-$HOME/.grok/plugin-data/grok-remote}"
VENV="$DATA/venv"
PATH="$HOME/.grok/bin:$HOME/.local/bin:$PATH"; export PATH
hint() { . /etc/os-release 2>/dev/null; case "$ID $ID_LIKE" in *arch*) echo "sudo pacman -S python-aiohttp";; *debian*|*ubuntu*) echo "sudo apt install python3-aiohttp python3-venv";; *fedora*|*rhel*) echo "sudo dnf install python3-aiohttp";; *suse*) echo "sudo zypper install python3-aiohttp";; *) echo "python3 -m pip install aiohttp";; esac; }
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "grok-remote needs Python 3.10+ (python3 not found). Install it, e.g. $(hint | sed 's/-aiohttp//;s/ python3-venv//')"; exit 1; }
"$PY" -c "import sys;sys.exit(sys.version_info<(3,10))" || { echo "grok-remote needs Python 3.10+, found $("$PY" -V 2>&1)"; exit 1; }
"$PY" -c "import aiohttp" 2>/dev/null || { [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import aiohttp" 2>/dev/null && PY="$VENV/bin/python"; }
"$PY" -c "import aiohttp" 2>/dev/null || { echo "aiohttp missing; creating a private venv at $VENV (system python is left untouched)"; mkdir -p "$DATA" && "$PY" -m venv --system-site-packages "$VENV" && "$VENV/bin/python" -m pip install -q --disable-pip-version-check aiohttp && PY="$VENV/bin/python"; }
"$PY" -c "import aiohttp" 2>/dev/null || { echo "could not set up aiohttp. Install it with your package manager: $(hint)"; exit 1; }
command -v grok >/dev/null 2>&1 || echo "warning: grok CLI not on PATH (looked in ~/.grok/bin too); the hub will start but cannot spawn an agent"
[ -n "$GROK_AGENT_SECRET" ] || { [ -s .ui-secret ] || (umask 077; "$PY" -c "import secrets;open('.ui-secret','w').write(secrets.token_hex(16))"); chmod 600 .ui-secret 2>/dev/null; GROK_AGENT_SECRET="$(cat .ui-secret)"; export GROK_AGENT_SECRET; }
exec "$PY" server.py "$@"
