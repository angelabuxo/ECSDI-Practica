#!/usr/bin/env bash
# Arrenca UN agent AgentZon en mode distribuït (una màquina de la xarxa).
#
# Ús:
#   cp distributed.env.example distributed.env   # primera vegada
#   # edita distributed.env: només DIRECTORY_HOST (IP del PC del Directory)
#   ./run_distributed_agent.sh directory         # al PC del Directory (primer!)
#   ./run_distributed_agent.sh cobrador          # al PC del Cobrador
#   ...
#
# Ordre recomanat (espera uns segons entre màquines si cal):
#   directory → cobrador → opinador → retornador → transport_fast →
#   transport_economy → centre_bcn → centre_gi → centre_tgn →
#   venedor_extern → compra → cercador
#
# Llista d'agents vàlids:
#   ./run_distributed_agent.sh --list

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/distributed.env}"

AGENT_ORDER=(
  directory
  cobrador
  opinador
  retornador
  transport_fast
  transport_economy
  centre_bcn
  centre_gi
  centre_tgn
  venedor_extern
  compra
  cercador
)

usage() {
  cat <<'EOF'
Ús: ./run_distributed_agent.sh <agent>

Agents: directory cobrador opinador retornador transport_fast transport_economy
        centre_bcn centre_gi centre_tgn venedor_extern compra cercador

Variables d'entorn (a distributed.env):
  DIRECTORY_HOST    IP del PC on corre el Directory (compartida per totes les màquines)
  LOCAL_HOST        Força la IP local si la detecció automàtica falla

Altres:
  ENV_FILE          Ruta al fitxer de configuració (per defecte: ./distributed.env)
  DATA_DIR          Carpeta de dades (per defecte: data)

Opcions:
  --local-ip        Mostra la IP local detectada i surt
EOF
}

list_agents() {
  printf '%s\n' "${AGENT_ORDER[@]}"
}

resolve_python() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "$ROOT_DIR/.venv/bin/python"
  elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    echo "$REPO_ROOT/.venv/bin/python"
  else
    echo "ERROR: No s'ha trobat cap entorn virtual (.venv)." >&2
    echo "Crea'l des de AgentZon/: python3 -m venv .venv && pip install -r requirements.txt" >&2
    exit 1
  fi
}

load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: No existeix $ENV_FILE" >&2
    echo "Copia distributed.env.example → distributed.env i defineix DIRECTORY_HOST." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$ENV_FILE"

  : "${DIRECTORY_HOST:?Falta DIRECTORY_HOST a $ENV_FILE}"
  : "${DIRECTORY_PORT:=9000}"
}

detect_local_ip() {
  local ip=""

  if [[ -n "${LOCAL_HOST:-}" ]]; then
    printf '%s' "$LOCAL_HOST"
    return 0
  fi

  if command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}')"
  fi

  if [[ -z "$ip" && "$(uname -s)" == "Darwin" ]]; then
    ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
  fi

  if [[ -z "$ip" ]]; then
    ip="$(python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || true)"
  fi

  if [[ -z "$ip" ]]; then
    echo "ERROR: No s'ha pogut detectar la IP local d'aquest PC." >&2
    echo "Afegeix LOCAL_HOST=<la_teva_ip> a $ENV_FILE" >&2
    exit 1
  fi

  printf '%s' "$ip"
}

resolve_publish_host() {
  detect_local_ip
}

build_command() {
  local agent="$1"
  local host
  local python="$2"
  local data_dir="${DATA_DIR:-data}"
  host="$(resolve_publish_host)"

  case "$agent" in
    directory)
      printf '%s -m agents.agent_directory --host 0.0.0.0 --publish-host %s --port %s' \
        "$python" "$host" "$DIRECTORY_PORT"
      ;;
    cobrador)
      printf '%s -m agents.agent_cobrador --host 0.0.0.0 --publish-host %s --port 9005 --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    opinador)
      printf '%s -m agents.agent_opinador --host 0.0.0.0 --publish-host %s --port 9004 --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    retornador)
      printf '%s -m agents.agent_retornador --host 0.0.0.0 --publish-host %s --port 9009 --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    transport_fast)
      printf '%s -m agents.agent_transportista --host 0.0.0.0 --publish-host %s --port 9010 --directory-host %s --directory-port %s --transport-id fast --price-per-kg 8.0 --delivery-days 1' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT"
      ;;
    transport_economy)
      printf '%s -m agents.agent_transportista --host 0.0.0.0 --publish-host %s --port 9011 --directory-host %s --directory-port %s --transport-id economy --price-per-kg 4.0 --delivery-days 3' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT"
      ;;
    centre_bcn)
      printf '%s -m agents.agent_centre_logistic --host 0.0.0.0 --publish-host %s --port 9003 --centre-id CL-BCN --centre-city Barcelona --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    centre_gi)
      printf '%s -m agents.agent_centre_logistic --host 0.0.0.0 --publish-host %s --port 9007 --centre-id CL-GI --centre-city Girona --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    centre_tgn)
      printf '%s -m agents.agent_centre_logistic --host 0.0.0.0 --publish-host %s --port 9008 --centre-id CL-TGN --centre-city Tarragona --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    venedor_extern)
      printf '%s -m agents.agent_venedor_extern --host 0.0.0.0 --publish-host %s --port 9012 --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    compra)
      printf '%s -m agents.agent_compra --host 0.0.0.0 --publish-host %s --port 9002 --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    cercador)
      printf '%s -m agents.agent_cercador --host 0.0.0.0 --publish-host %s --port 9001 --directory-host %s --directory-port %s --data-dir %s' \
        "$python" "$host" "$DIRECTORY_HOST" "$DIRECTORY_PORT" "$data_dir"
      ;;
    *)
      echo "ERROR: Agent desconegut: $agent" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main() {
  local agent="${1:-}"

  if [[ "$agent" == "--help" || "$agent" == "-h" ]]; then
    usage
    exit 0
  fi
  if [[ "$agent" == "--list" ]]; then
    list_agents
    exit 0
  fi
  if [[ "$agent" == "--local-ip" ]]; then
    load_env
    detect_local_ip
    echo
    exit 0
  fi
  if [[ -z "$agent" ]]; then
    usage >&2
    exit 1
  fi

  load_env
  local python
  python="$(resolve_python)"
  cd "$ROOT_DIR"

  local host
  host="$(resolve_publish_host)"
  local cmd
  cmd="$(build_command "$agent" "$python")"

  echo "=== AgentZon distribuït: $agent ==="
  echo "Màquina ( --publish-host ): $host"
  echo "Escolta ( --host ):         0.0.0.0"
  echo "Directory ( --directory-host ): $DIRECTORY_HOST:$DIRECTORY_PORT"
  echo "Comanda: $cmd"
  echo

  # shellcheck disable=SC2086
  exec $cmd
}

main "$@"
