# AgentZon

AgentZon és un prototip de sistema multiagent per a l'assignatura ECSDI. Implementa una botiga distribuïda amb cerca de productes, compra i gestió logística basada en ontologia RDF/OWL.

## 1) Generar documentació i graf de l'ontologia

Des de root del repositori:

```bash
python3 -m venv AgentZon/.venv
source AgentZon/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Generar la documentació HTML de l'ontologia:

```bash
./AgentZon/.venv/bin/python -m pylode AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology.html
```

Generar el graf de l'ontologia:

```bash
owl2plot AgentZon/ontologia/AgentZonOntology.rdf -o AgentZon/ontologia/docs/ontology_graph
```

## 2) Executar el sistema distribuït

Obre terminals separats i executa cada agent des de l'arrel del projecte.

1. Agent Directory

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_directory --host 127.0.0.1 --port 9000
```

1. Agent Opinador

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_opinador --host 127.0.0.1 --port 9004 --directory-host 127.0.0.1 --directory-port 9000 --data-dir AgentZon/data
```

1. Transportista ràpid

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista --host 127.0.0.1 --port 9010 --transport-id fast --price-per-kg 8.0 --delivery-days 1
```

1. Transportista econòmic

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista --host 127.0.0.1 --port 9011 --transport-id economy --price-per-kg 4.0 --delivery-days 3
```

1. Agent Centre Logístic

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_centre_logistic --host 127.0.0.1 --port 9003 --directory-host 127.0.0.1 --directory-port 9000 --transport-fast-host 127.0.0.1 --transport-fast-port 9010 --transport-economy-host 127.0.0.1 --transport-economy-port 9011 --data-dir AgentZon/data
```

1. Agent Compra

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_compra --host 127.0.0.1 --port 9002 --directory-host 127.0.0.1 --directory-port 9000 --data-dir AgentZon/data
```

1. Agent Cercador

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_cercador --host 127.0.0.1 --port 9001 --directory-host 127.0.0.1 --directory-port 9000 --data-dir AgentZon/data
```

Quan tots els agents estiguin en marxa, obre:

`http://127.0.0.1:9001/`