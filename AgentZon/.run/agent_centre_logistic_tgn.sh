#!/usr/bin/env bash
set -euo pipefail
cd /Users/angelabuxo/UPC/ECSDI/Pràctica/ECSDI-Practica/AgentZon
clear
echo $'=== Agent Centre Log�\255stic TGN ==='
exec /Users/angelabuxo/UPC/ECSDI/Pràctica/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_centre_logistic --host 127.0.0.1 --port 9008 --centre-id CL-TGN --centre-city Tarragona --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
