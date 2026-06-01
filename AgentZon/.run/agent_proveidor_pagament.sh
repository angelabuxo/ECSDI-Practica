#!/usr/bin/env bash
set -euo pipefail
cd /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon
clear
echo ===\ Agent\ Proveïdor\ de\ Pagament\ ===
exec /Users/polmontanera/Desktop/Q6\ 2526/ECSDI/ECSDI-Practica/AgentZon/.venv/bin/python -m agents.agent_proveidor_de_pagament --host 127.0.0.1 --port 9006 --directory-host 127.0.0.1 --directory-port 9000
