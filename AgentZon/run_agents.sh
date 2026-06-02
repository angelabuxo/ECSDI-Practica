#!/usr/bin/env bash
# Obre una finestra de Terminal per cada agent del sistema distribuït.
# Segueix l'ordre i les comandes de README.md (secció 3) des de l'arrel d'AgentZon/.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
HOST="127.0.0.1"
BROWSER_PATH="${BROWSER_PATH:-/iface}"
DELAY_SECONDS="${DELAY_SECONDS:-0.6}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
else
  echo "ERROR: No s'ha trobat cap entorn virtual (.venv)."
  echo
  echo "Crea'l des de l'arrel d'AgentZon/:"
  echo "  cd \"$ROOT_DIR\""
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  python -m pip install -r requirements.txt"
  exit 1
fi

mkdir -p "$RUN_DIR"

write_launcher() {
  local slug="$1"
  local title="$2"
  shift 2
  local script="$RUN_DIR/${slug}.sh"

  {
    echo '#!/usr/bin/env bash'
    echo 'set -euo pipefail'
    printf 'cd %q\n' "$ROOT_DIR"
    printf 'clear\n'
    printf 'echo %q\n' "=== $title ==="
    printf 'exec %q -m' "$PYTHON"
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    echo
  } >"$script"
  chmod +x "$script"
  printf '%s' "$script"
}

open_terminal() {
  local script="$1"

  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Aquest script obre terminals automàticament només a macOS."
    echo "Executa manualment: $script"
    return
  fi

  # Passa el path com a argv d'AppleScript (evita errors amb espais/accents al path).
  osascript - "$script" <<'APPLESCRIPT'
on run argv
  set scriptPath to item 1 of argv
  tell application "Terminal"
    activate
    do script "bash " & quoted form of scriptPath
  end tell
end run
APPLESCRIPT

  sleep "$DELAY_SECONDS"
}

run_agent() {
  local slug="$1"
  local title="$2"
  shift 2
  open_terminal "$(write_launcher "$slug" "$title" "$@")"
}

echo "AgentZon: obrint 11 terminals (un agent per finestra)..."
echo "Directori de treball: $ROOT_DIR"
echo "Python: $PYTHON"
echo "Launchers: $RUN_DIR"
echo

run_agent agent_directory "Agent Directory" \
  agents.agent_directory --host "$HOST" --port 9000

run_agent agent_proveidor_pagament "Agent Proveïdor de Pagament" \
  agents.agent_proveidor_de_pagament --host "$HOST" --port 9006 \
  --directory-host "$HOST" --directory-port 9000

run_agent agent_cobrador "Agent Cobrador" \
  agents.agent_cobrador --host "$HOST" --port 9005 \
  --directory-host "$HOST" --directory-port 9000 --data-dir data

run_agent agent_opinador "Agent Opinador" \
  agents.agent_opinador --host "$HOST" --port 9004 \
  --directory-host "$HOST" --directory-port 9000 --data-dir data

run_agent agent_transport_fast "Transportista ràpid" \
  agents.agent_transportista --host "$HOST" --port 9010 \
  --directory-host "$HOST" --directory-port 9000 \
  --transport-id fast --price-per-kg 8.0 --delivery-days 1

run_agent agent_transport_economy "Transportista econòmic" \
  agents.agent_transportista --host "$HOST" --port 9011 \
  --directory-host "$HOST" --directory-port 9000 \
  --transport-id economy --price-per-kg 4.0 --delivery-days 3

run_agent agent_centre_logistic_bcn "Agent Centre Logístic BCN" \
  agents.agent_centre_logistic --host "$HOST" --port 9003 \
  --centre-id CL-BCN --centre-city Barcelona \
  --directory-host "$HOST" --directory-port 9000 \
  --data-dir data

run_agent agent_centre_logistic_gi "Agent Centre Logístic GI" \
  agents.agent_centre_logistic --host "$HOST" --port 9007 \
  --centre-id CL-GI --centre-city Girona \
  --directory-host "$HOST" --directory-port 9000 \
  --data-dir data

run_agent agent_centre_logistic_tgn "Agent Centre Logístic TGN" \
  agents.agent_centre_logistic --host "$HOST" --port 9008 \
  --centre-id CL-TGN --centre-city Tarragona \
  --directory-host "$HOST" --directory-port 9000 \
  --data-dir data

run_agent agent_compra "Agent Compra" \
  agents.agent_compra --host "$HOST" --port 9002 \
  --directory-host "$HOST" --directory-port 9000 --data-dir data

run_agent agent_cercador "Agent Cercador" \
  agents.agent_cercador --host "$HOST" --port 9001 \
  --directory-host "$HOST" --directory-port 9000 --data-dir data

echo "Tots els agents s'han llançat en terminals separades."
echo "Quan estiguin actius, obre: http://${HOST}:9001${BROWSER_PATH}"

if [[ "$(uname -s)" == "Darwin" && "$OPEN_BROWSER" == "1" ]]; then
  sleep 2
  open "http://${HOST}:9001${BROWSER_PATH}" || true
fi
