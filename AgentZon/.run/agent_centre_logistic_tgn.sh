#!/usr/bin/env bash
set -euo pipefail
cd $'/Users/angelabuxo/UPC/ECSDI/PraÃ\200ctica/ECSDI-Practica/AgentZon'
clear
echo $'=== Agent Centre Log√\255stic TGN ==='
exec $'/Users/angelabuxo/UPC/ECSDI/PraÃ\200ctica/ECSDI-Practica/AgentZon/.venv/bin/python' -m agents.agent_centre_logistic --host 127.0.0.1 --port 9008 --centre-id CL-TGN --centre-city Tarragona --directory-host 127.0.0.1 --directory-port 9000 --transport-fast-host 127.0.0.1 --transport-fast-port 9010 --transport-economy-host 127.0.0.1 --transport-economy-port 9011 --data-dir data
