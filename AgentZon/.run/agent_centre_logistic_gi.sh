#!/usr/bin/env bash
set -euo pipefail
cd /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon
clear
echo $'=== Agent Centre Log√\255stic GI ==='
exec /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_centre_logistic --host 127.0.0.1 --port 9007 --centre-id CL-GI --centre-city Girona --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
