#!/usr/bin/env bash
set -euo pipefail
cd $'/Users/angelabuxo/UPC/ECSDI/PraÌ\200ctica/ECSDI-Practica/AgentZon'
clear
echo ===\ Agent\ Directory\ ===
exec $'/Users/angelabuxo/UPC/ECSDI/PraÌ\200ctica/ECSDI-Practica/AgentZon/.venv/bin/python' -m agents.agent_directory --host 127.0.0.1 --port 9000
