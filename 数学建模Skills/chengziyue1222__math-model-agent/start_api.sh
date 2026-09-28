#!/usr/bin/env sh
# Minimal launcher for Nova API on a Linux cloud server.
set -eu

APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-"$APP_ROOT/.venv/bin/python"}
HOST=${NOVA_API_HOST:-0.0.0.0}
PORT=${NOVA_API_PORT:-8000}

if [ -z "${NOVA_API_KEY:-}" ]; then
  echo "NOVA_API_KEY must be supplied as an environment variable." >&2
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  exit 1
fi

cd "$APP_ROOT"
export PYTHONPATH="$APP_ROOT/code${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN" -m nova_api --host "$HOST" --port "$PORT"
