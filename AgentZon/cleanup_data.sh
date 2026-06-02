#!/usr/bin/env bash
# Reinicia dades de runtime generades durant l'execució del sistema.
# Executa des de qualsevol ubicació; resol paths respecte a AgentZon/.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
DATA_DIR="${DATA_DIR:-data}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
else
  echo "ERROR: No s'ha trobat cap entorn virtual (.venv)." >&2
  echo >&2
  echo "Crea'l des de l'arrel d'AgentZon/:" >&2
  echo "  cd \"$ROOT_DIR\"" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  source .venv/bin/activate" >&2
  echo "  python -m pip install -r requirements.txt" >&2
  exit 1
fi

cd "$ROOT_DIR"
exec "$PYTHON" -m services.bootstrap --cleanup --data-dir "$DATA_DIR"
