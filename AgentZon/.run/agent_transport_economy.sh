#!/usr/bin/env bash
set -euo pipefail
cd /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon
clear
echo ===\ Transportista\ econòmic\ ===
exec /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_transportista --host 127.0.0.1 --port 9011 --directory-host 127.0.0.1 --directory-port 9000 --transport-id economy --price-per-kg 4.0 --delivery-days 3
