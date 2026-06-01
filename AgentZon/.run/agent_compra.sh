#!/usr/bin/env bash
set -euo pipefail
cd /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon
clear
echo ===\ Agent\ Compra\ ===
exec /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_compra --host 127.0.0.1 --port 9002 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
