# AgentZon

AgentZon is the ECSDI multi-agent system prototype included in this repository. The active implementation lives in `AgentZon/` and focuses on the Phase 2 workflow: restricted product search, internal purchase registration, logistics negotiation, and distributed execution with explicit transport agents.

## Project Structure

- `AgentZon/agents/`: Flask entrypoints for the directory, search, purchase, logistics, opinion, and transport agents.
- `AgentZon/protocols/`: RDF/FIPA-ACL message builders and parsers mapped to the shared ontology.
- `AgentZon/services/`: RDF-backed persistence and query helpers for catalog, orders, history, and logistics state.
- `AgentZon/AgentUtil/`: professor-inspired shared utilities for agents, namespaces, Flask shutdown, and ACL messages.
- `AgentZon/data/`: seeded Turtle files used by the prototype.
- `AgentZon/ontologia/AgentZonOntology.rdf`: shared RDF/OWL ontology for the whole system.
- `AgentZon/tests/`: unit, flow, and distributed smoke tests.
- `REFERENCE/`: professor reference material kept for alignment with the course conventions.

## Requirements

The runtime dependencies are listed in `requirements.txt`:

- `Flask`
- `rdflib`
- `requests`

Optional ontology-documentation helpers used by the team are described in `AgentZon/docs/AgentZon/PHASE2_IMPLEMENTATION.md`.

## Ontology Docs And Graph

Generate the ontology HTML documentation with `pylode`:

```bash
./AgentZon/.venv/bin/python -m pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html
```

Generate the ontology graph with `owl2plot`:

```bash
owl2plot AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology_graph
```

## Virtual Environment

Create and activate the project virtual environment with:

```bash
python3 -m venv AgentZon/.venv
source AgentZon/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Execution Guide

Run the six core agent roles in separate terminals from the repository root.

1. Directory agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_directory --host 127.0.0.1 --port 9000
```

2. Opinion agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_opinador --host 127.0.0.1 --port 9004 --directory-host 127.0.0.1 --directory-port 9000 --data-dir AgentZon/data
```

3. Fast transport agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista --host 127.0.0.1 --port 9010 --transport-id fast --price-per-kg 8.0 --delivery-days 1
```

4. Economy transport agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista --host 127.0.0.1 --port 9011 --transport-id economy --price-per-kg 4.0 --delivery-days 3
```

5. Logistics center agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_centre_logistic --host 127.0.0.1 --port 9003 --directory-host 127.0.0.1 --directory-port 9000 --transport-fast-host 127.0.0.1 --transport-fast-port 9010 --transport-economy-host 127.0.0.1 --transport-economy-port 9011 --data-dir AgentZon/data
```

6. Purchase agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_compra --host 127.0.0.1 --port 9002 --directory-host 127.0.0.1 --directory-port 9000 --data-dir AgentZon/data
```

7. Search agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_cercador --host 127.0.0.1 --port 9001 --directory-host 127.0.0.1 --directory-port 9000 --data-dir AgentZon/data
```

Once everything is running, open `http://127.0.0.1:9001/`.

## Logging

Agent entrypoints now initialize the shared logger utility from `AgentZon/AgentUtil/Logging.py`, aligned with the `REFERENCE` and `ecsdi-amazon` style.

- Logger initialization used by agents:

```python
from AgentZon.AgentUtil.Logging import config_logger

logger = config_logger(level=1)
```

- `level=1` enables `INFO` and `ERROR` events.
- `level=0` keeps only `ERROR` events.
- Logs are emitted to the console with the format `[timestamp] - file - level - message`.

To start logging in a new agent, initialize `logger = config_logger(level=1)` near the Flask app creation and use `logger.info(...)`, `logger.warning(...)`, and `logger.error(...)` in lifecycle and communication handlers.

## Hostname Notes

- `--host` forces the bind and published host used by an agent. This is the recommended option for local development and tests.
- If `--host` is omitted and `--open` is also omitted, the agent binds to `0.0.0.0`.
- If `--host` is omitted and `--open` is provided, the agent publishes `socket.gethostname()` through the shared bootstrap helper.

## Tests

Run the most relevant regression suites with:

```bash
./AgentZon/.venv/bin/python -m unittest AgentZon.tests.test_config AgentZon.tests.test_directory_agent AgentZon.tests.test_logistics_flow AgentZon.tests.test_purchase_flow -v
```

For the process-level verification:

```bash
./AgentZon/.venv/bin/python -m unittest AgentZon.tests.test_distributed_smoke -v
```

## Additional Documentation

- `AgentZon/docs/AgentZon/IMPLEMENTATION_AND_ONTOLOGY.md`
- `AgentZon/docs/AgentZon/PHASE2_IMPLEMENTATION.md`
- `AgentZon/DISTRIBUTED_RUN.md`
