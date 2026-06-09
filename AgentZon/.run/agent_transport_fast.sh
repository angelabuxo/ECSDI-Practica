#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
elif [[ -x ../.venv/bin/python ]]; then
  PYTHON=../.venv/bin/python
else
  echo "ERROR: No s'ha trobat cap entorn virtual (.venv)." >&2
  exit 1
fi
clear
echo $'=== Transportista r\303\240pid ==='
exec "$PYTHON" -m agents.agent_transportista --host 127.0.0.1 --port 9010 --directory-host 127.0.0.1 --directory-port 9000 --transport-id fast --price-per-kg 8.0 --delivery-days 1
