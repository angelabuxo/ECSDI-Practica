# AgentZon Phase 2 Distributed Run

Run every agent from the repository root with `./AgentZon/.venv/bin/python`.

## Start order

1. Directory agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_directory
```

2. Opinions/history agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_opinador
```

3. Transport agents

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista --port 9010 --transport-id fast --price-per-kg 8.0 --delivery-days 1
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista --port 9011 --transport-id economy --price-per-kg 4.0 --delivery-days 3
```

4. Logistics center

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_centre_logistic
```

5. Purchase agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_compra
```

6. Search agent

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_cercador
```

## Demo flow

Open `http://127.0.0.1:9001/`.

1. Search for products with any combination of text, category, brand, and price range.
2. Select one or more catalog products.
3. Submit the purchase form with user data, delivery address, city, priority, and placeholder payment method.
4. `Agent Compra` stores the order, sends the purchase-history message to `Agent Opinador`, and forwards the localized products to the logistics center.
5. `Agent Centre Logístic` groups the order into one lot, queries the two external transport agents in parallel, chooses the cheapest valid offer, and returns the shipping summary.

## Runtime notes

- Core agents register in the directory automatically at startup.
- The transport agents are explicit external agents. They are not discovered through the directory in this phase.
- The shipped dataset is under `AgentZon/data/`.
- The minimal shared ontology is under `AgentZon/ontologia/AgentZonOntology.rdf`.
