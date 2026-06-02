#!/usr/bin/env bash
set -euo pipefail
cd /Users/angelabuxo/UPC/ECSDI/Pràctica/ECSDI-Practica/AgentZon
clear
echo ===\ Agent\ Venedor\ Extern\ ===
exec /Users/angelabuxo/UPC/ECSDI/Pràctica/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_venedor_extern --host 127.0.0.1 --port 9006 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
