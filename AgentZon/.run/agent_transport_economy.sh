#!/usr/bin/env bash
set -euo pipefail
cd $'/Users/angelabuxo/UPC/ECSDI/PraÃ\200ctica/ECSDI-Practica/AgentZon'
clear
echo ===\ Transportista\ econ√≤mic\ ===
exec $'/Users/angelabuxo/UPC/ECSDI/PraÃ\200ctica/ECSDI-Practica/AgentZon/.venv/bin/python' -m agents.agent_transportista --host 127.0.0.1 --port 9011 --transport-id economy --price-per-kg 4.0 --delivery-days 3
