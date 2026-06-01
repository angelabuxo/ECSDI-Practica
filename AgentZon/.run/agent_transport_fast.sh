#!/usr/bin/env bash
set -euo pipefail
cd $'/Users/angelabuxo/UPC/ECSDI/PraÃ\200ctica/ECSDI-Practica/AgentZon'
clear
echo ===\ Transportista\ r√†pid\ ===
exec $'/Users/angelabuxo/UPC/ECSDI/PraÃ\200ctica/ECSDI-Practica/AgentZon/.venv/bin/python' -m agents.agent_transportista --host 127.0.0.1 --port 9010 --transport-id fast --price-per-kg 8.0 --delivery-days 1
