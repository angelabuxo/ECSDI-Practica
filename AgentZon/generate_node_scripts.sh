#!/usr/bin/env bash
# Genera un script d'arrencada per cada agent (per repartir-los manualment)
#
# Ús:
#   cp distributed.env.example distributed.env && vim distributed.env
#   ./generate_node_scripts.sh
#   # Reparteix distributed/nodes/*.sh (un per agent) a cada PC i executa'l alla

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/distributed.env}"
OUT_DIR="$ROOT_DIR/distributed/nodes"
RUNNER="$ROOT_DIR/run_distributed_agent.sh"

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

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Crea primer $ENV_FILE (copia distributed.env.example)." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

mkdir -p "$OUT_DIR"

for agent in "${AGENT_ORDER[@]}"; do
  script="$OUT_DIR/start_${agent}.sh"

  cat >"$script" <<EOF
#!/usr/bin/env bash
# Arrenca l'agent ${agent} (la IP local es detecta automàticament).
# Copia distributed.env i tot el projecte AgentZon a aquest PC abans d'executar.

set -euo pipefail
cd "\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/../.." && pwd)"
export ENV_FILE="\${ENV_FILE:-\$PWD/distributed.env}"
exec ./run_distributed_agent.sh ${agent}
EOF
  chmod +x "$script"
done

cat >"$OUT_DIR/README.txt" <<'EOF'
Scripts generats per arrencada manual distribuïda.

Per cada PC:
  1. Clona/copia el projecte AgentZon (amb .venv i data/)
  2. Copia distributed.env (el mateix fitxer a totes les màquines)
  3. Executa només el script que correspon a aquell agent:
       bash distributed/nodes/start_directory.sh
       bash distributed/nodes/start_cobrador.sh
       ...

Ordre: directory primer, després la resta (espera uns segons entre màquines).
EOF

echo "Generats ${#AGENT_ORDER[@]} scripts a $OUT_DIR/"
echo "Cada script detecta la IP local del PC on s'executa."
echo "distributed.env només necessita DIRECTORY_HOST (compartit)."
