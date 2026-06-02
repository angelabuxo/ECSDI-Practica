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
echo ===\ Agent\ Proveïdor\ de\ Pagament\ ===
exec "$PYTHON" -m agents.agent_proveidor_de_pagament --host 127.0.0.1 --port 9006 --directory-host 127.0.0.1 --directory-port 9000
