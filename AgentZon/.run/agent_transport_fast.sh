#!/usr/bin/env bash
set -euo pipefail
cd /Users/angelabuxo/UPC/ECSDI/Pràctica/ECSDI-Practica/AgentZon
clear
echo ===\ Transportista\ ràpid\ ===
exec /Users/angelabuxo/UPC/ECSDI/Pràctica/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_transportista --host 127.0.0.1 --port 9010 --directory-host 127.0.0.1 --directory-port 9000 --transport-id fast --price-per-kg 8.0 --delivery-days 1
