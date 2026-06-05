#!/usr/bin/env bash
# Desplega tots els agents AgentZon via SSH (un agent per màquina).
#
# Requisits:
#   - distributed.env amb DIRECTORY_HOST (copia de distributed.env.example)
#   - deploy.hosts amb agent=ip per cada PC (copia de deploy.hosts.example)
#   - SSH sense contrasenya cap a cada màquina (ssh-copy-id)
#   - El mateix codi i .venv a REMOTE_AGENTZON_DIR de cada PC
#   - SSH_USER definit a distributed.env (o exportat)
#
# Ús:
#   ./deploy_distributed.sh --check      # prova SSH a cada PC (sense desplegar res)
#   ./deploy_distributed.sh --check-setup  # SSH + comprova projecte i .venv remots
#   ./deploy_distributed.sh              # arrenca tots els agents en ordre
#   ./deploy_distributed.sh --dry-run    # mostra les comandes SSH sense executar-les
#   ./deploy_distributed.sh cobrador     # només un agent
#   ./deploy_distributed.sh --stop       # atura agents remots (pkill)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/distributed.env}"
RUNNER="$ROOT_DIR/run_distributed_agent.sh"
DELAY_SECONDS="${DELAY_SECONDS:-3}"
DRY_RUN=0
STOP_MODE=0
CHECK_MODE=0
CHECK_SETUP=0

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
Ús: ./deploy_distributed.sh [opcions] [agent ...]

Opcions:
  --check       Prova connexió SSH a cada IP de deploy.hosts (sense instal·lar res)
  --check-setup Com a --check, i comprova REMOTE_AGENTZON_DIR i .venv/bin/python
  --dry-run     Mostra les comandes SSH sense executar-les
  --stop        Atura processos agents.agent_* als hosts configurats
  --delay SEC   Segons d'espera entre arrencades (per defecte: 3)

Si no passes cap agent, s'arrenquen tots en l'ordre recomanat.
EOF
  cat <<'EOF'

Prova manual ràpida (substitueix usuari i IP):
  ssh -o ConnectTimeout=5 student@10.10.43.2 'echo OK && hostname'
EOF
}

load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: No existeix $ENV_FILE" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  : "${DIRECTORY_HOST:?Falta DIRECTORY_HOST}"
  REMOTE_AGENTZON_DIR="${REMOTE_AGENTZON_DIR:-$ROOT_DIR}"
  SSH_USER="${SSH_USER:-$USER}"
  DEPLOY_HOSTS_FILE="${DEPLOY_HOSTS_FILE:-$ROOT_DIR/deploy.hosts}"
}

host_for_agent() {
  local agent="$1"
  local host="" line var="HOST_${agent}"

  if [[ -f "$DEPLOY_HOSTS_FILE" ]]; then
    line="$(grep -E "^[[:space:]]*${agent}=" "$DEPLOY_HOSTS_FILE" | head -1 | cut -d= -f2- | tr -d '[:space:]')"
    host="$line"
  fi

  if [[ -z "$host" ]]; then
    host="${!var:-}"
  fi

  if [[ -z "$host" ]]; then
    echo "ERROR: No hi ha IP per a l'agent '$agent'." >&2
    echo "Afegeix '${agent}=<ip>' a $DEPLOY_HOSTS_FILE (copia deploy.hosts.example)." >&2
    exit 1
  fi
  printf '%s' "$host"
}

remote_cmd_start() {
  local agent="$1"
  printf 'cd %q && chmod +x run_distributed_agent.sh && ENV_FILE=%q ./run_distributed_agent.sh %q' \
    "$REMOTE_AGENTZON_DIR" "$ENV_FILE" "$agent"
}

remote_cmd_stop() {
  printf 'pkill -f "[Pp]ython.*-m agents\\.agent_" 2>/dev/null || true'
}

run_ssh() {
  local host="$1"
  local remote_cmd="$2"
  local label="$3"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ssh ${SSH_USER}@${host}  # ${label}"
    echo "          ${remote_cmd}"
    return 0
  fi

  echo ">>> ${label} @ ${SSH_USER}@${host}"
  # nohup + background perquè SSH no quedi bloquejat amb serve_agent
  ssh -o ConnectTimeout=10 -o BatchMode=yes "${SSH_USER}@${host}" \
    "nohup bash -lc $(printf '%q' "$remote_cmd") > /tmp/agentzon-${label}.log 2>&1 &"
}

deploy_agent() {
  local agent="$1"
  local host
  host="$(host_for_agent "$agent")"
  run_ssh "$host" "$(remote_cmd_start "$agent")" "$agent"
}

stop_all_hosts() {
  local seen=""
  local host agent
  for agent in "${AGENT_ORDER[@]}"; do
    host="$(host_for_agent "$agent")"
    if [[ " $seen " == *" $host "* ]]; then
      continue
    fi
    seen="$seen $host"
    run_ssh "$host" "$(remote_cmd_stop)" "stop@${host}"
  done
}

unique_hosts() {
  local seen="" host agent
  for agent in "${AGENT_ORDER[@]}"; do
    host="$(host_for_agent "$agent")"
    if [[ " $seen " == *" $host "* ]]; then
      continue
    fi
    seen="$seen $host"
    printf '%s\n' "$host"
  done
}

agents_on_host() {
  local target="$1" host agent names=()
  for agent in "${AGENT_ORDER[@]}"; do
    host="$(host_for_agent "$agent")"
    if [[ "$host" == "$target" ]]; then
      names+=("$agent")
    fi
  done
  (IFS=', '; echo "${names[*]}")
}

check_ssh_host() {
  local host="$1"
  local agents
  agents="$(agents_on_host "$host")"
  local target="${SSH_USER}@${host}"

  printf '%-16s %-28s ' "$host" "$agents"

  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
    "$target" 'echo OK' >/dev/null 2>&1; then
    echo "FAIL (SSH)"
    return 1
  fi

  if [[ "$CHECK_SETUP" -eq 0 ]]; then
    local remote_name
    remote_name="$(ssh -o ConnectTimeout=5 -o BatchMode=yes "$target" 'hostname' 2>/dev/null || true)"
    echo "OK (${remote_name:-ssh})"
    return 0
  fi

  local setup_cmd
  setup_cmd=$(cat <<EOF
if [[ ! -d $(printf '%q' "$REMOTE_AGENTZON_DIR") ]]; then
  echo "MISSING_DIR"
  exit 2
fi
if [[ -x $(printf '%q' "$REMOTE_AGENTZON_DIR")/.venv/bin/python ]]; then
  echo "OK_VENV"
elif [[ -x $(printf '%q' "$REMOTE_AGENTZON_DIR")/../.venv/bin/python ]]; then
  echo "OK_VENV_PARENT"
else
  echo "MISSING_VENV"
  exit 3
fi
EOF
)
  local result
  result="$(ssh -o ConnectTimeout=5 -o BatchMode=yes "$target" "bash -lc $(printf '%q' "$setup_cmd")" 2>/dev/null || true)"
  case "$result" in
    OK_VENV)
      echo "OK (projecte + .venv)"
      ;;
    OK_VENV_PARENT)
      echo "OK (projecte + .venv a l'arrel del repo)"
      ;;
    MISSING_DIR)
      echo "FAIL (no existeix REMOTE_AGENTZON_DIR)"
      return 1
      ;;
    MISSING_VENV)
      echo "FAIL (falta .venv; executa: python3 -m venv .venv && pip install -r requirements.txt)"
      return 1
      ;;
    *)
      echo "FAIL (setup desconegut: ${result:-sense resposta})"
      return 1
      ;;
  esac
}

check_all_hosts() {
  local host failures=0 total=0

  echo "Comprovant SSH (usuari: ${SSH_USER})..."
  if [[ "$CHECK_SETUP" -eq 1 ]]; then
    echo "REMOTE_AGENTZON_DIR=${REMOTE_AGENTZON_DIR}"
  fi
  echo
  printf '%-16s %-28s %s\n' "IP" "Agents" "Resultat"
  printf '%-16s %-28s %s\n' "--------------" "----------------------------" "--------"

  while IFS= read -r host; do
    [[ -z "$host" ]] && continue
    total=$((total + 1))
    if ! check_ssh_host "$host"; then
      failures=$((failures + 1))
    fi
  done < <(unique_hosts)

  echo
  if [[ "$failures" -eq 0 ]]; then
    echo "Tot correcte: ${total}/${total} hosts accessibles per SSH."
    if [[ "$CHECK_SETUP" -eq 0 ]]; then
      echo "Següent pas: ./deploy_distributed.sh --check-setup (projecte + venv) o desplegar."
    fi
    return 0
  fi

  echo "ERROR: ${failures}/${total} hosts han fallat."
  echo "Consells:"
  echo "  - Prova manual: ssh ${SSH_USER}@<IP> 'echo OK'"
  echo "  - Configura clau: ssh-copy-id ${SSH_USER}@<IP>"
  echo "  - Activa 'Remote Login' al Mac o sshd al Linux"
  return 1
}

main() {
  local agents=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        usage
        exit 0
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --stop)
        STOP_MODE=1
        shift
        ;;
      --check)
        CHECK_MODE=1
        shift
        ;;
      --check-setup)
        CHECK_MODE=1
        CHECK_SETUP=1
        shift
        ;;
      --delay)
        DELAY_SECONDS="$2"
        shift 2
        ;;
      -*)
        echo "ERROR: Opció desconeguda: $1" >&2
        usage >&2
        exit 1
        ;;
      *)
        agents+=("$1")
        shift
        ;;
    esac
  done

  if [[ ! -x "$RUNNER" ]]; then
    chmod +x "$RUNNER"
  fi

  load_env

  if [[ "$CHECK_MODE" -eq 1 ]]; then
    check_all_hosts
    exit $?
  fi

  if [[ "$STOP_MODE" -eq 1 ]]; then
    stop_all_hosts
    echo "Aturada remota enviada."
    exit 0
  fi

  if [[ ${#agents[@]} -eq 0 ]]; then
    agents=("${AGENT_ORDER[@]}")
  fi

  echo "Desplegament AgentZon (${#agents[@]} agents, delay=${DELAY_SECONDS}s)"
  echo "SSH_USER=$SSH_USER  REMOTE_AGENTZON_DIR=$REMOTE_AGENTZON_DIR"
  echo

  local i=0
  for agent in "${agents[@]}"; do
    deploy_agent "$agent"
    i=$((i + 1))
    if [[ "$DRY_RUN" -eq 0 && "$i" -lt ${#agents[@]} ]]; then
      sleep "$DELAY_SECONDS"
    fi
  done

  if [[ "$DRY_RUN" -eq 0 ]]; then
    local cercador_host
    cercador_host="$(host_for_agent cercador)"
    echo
    echo "Desplegament enviat. Logs remots: /tmp/agentzon-<agent>.log"
    echo "Interfície (quan tot estigui actiu): http://${cercador_host}:9001/iface"
  fi
}

main "$@"
