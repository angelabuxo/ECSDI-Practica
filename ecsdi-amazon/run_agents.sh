#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$ROOT_DIR/agents"
LOGS_DIR="$ROOT_DIR/logs"
VENV_ACTIVATE="$ROOT_DIR/.venv/bin/activate"

if [[ ! -d "$AGENTS_DIR" ]]; then
  echo "No s'ha trobat el directori agents a: $AGENTS_DIR"
  exit 1
fi

mkdir -p "$LOGS_DIR"

if [[ -f "$VENV_ACTIVATE" ]]; then
  # shellcheck source=/dev/null
  source "$VENV_ACTIVATE"
else
  echo "Avis: no s'ha trobat .venv a $VENV_ACTIVATE. S'usarà el Python del sistema."
fi

export PYTHONPATH="$ROOT_DIR"
cd "$AGENTS_DIR"

agents=(
  "SimpleDirectoryService.py"
  "ExternalTransportDirectory.py"
  "ProductsAgent.py"
  "QualifierAgent.py"
  "FinancialAgent.py"
  "SellerAgent.py"
  "TransportDealerAgent.py"
  "LogisticHubAgent.py"
  "ExternalTransportAgent1.py"
  "ExternalTransportAgent2.py"
  "BankAgent.py"
  "ExternSellerPersonalAgent.py"
  "UserPersonalAgent.py"
)

echo "Engegant agents..."
for agent in "${agents[@]}"; do
  log_file="$LOGS_DIR/${agent%.py}.log"
  echo "  - $agent (log: $log_file)"
  nohup python3 "$agent" > "$log_file" 2>&1 &
done

echo
echo "Agents engegats en segon pla."
echo "Per veure'ls: ps aux | rg 'python3 .*Agent|python3 .*Directory'"
echo "Per logs:     ls logs && tail -f logs/UserPersonalAgent.log"
echo "Per aturar-los tots: pkill -f '/agents/.*\\.py'"
