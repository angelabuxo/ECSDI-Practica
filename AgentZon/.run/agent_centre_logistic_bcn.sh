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
echo $'=== Agent Centre Log�\255stic BCN ==='
exec "$PYTHON" -m agents.agent_centre_logistic --host 127.0.0.1 --port 9003 --centre-id CL-BCN --centre-city Barcelona --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
