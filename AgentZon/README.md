# AgentZon

AgentZon és un prototip de sistema multiagent per a l'assignatura ECSDI. Implementa una botiga distribuïda amb cerca de productes, compra i gestió logística basada en ontologia RDF/OWL.

## 1) Generar documentació i graf de l'ontologia

Des de root del repositori:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Generar la documentació HTML de l'ontologia:

```bash
.venv/bin/python -m pylode ontologia/AgentZonOntology.rdf -o ontologia/docs/ontology.html
```

Generar el graf de l'ontologia:

```bash
.venv/bin/rdf2dot ontologia/AgentZonOntology.rdf | dot -Tpng -o ontologia/docs/ontology_graph.png
```

## 2) Executar el sistema distribuït

Obre terminals separats i executa cada agent des de l'arrel del projecte. La interfície humana viu a `/iface`; els agents es comuniquen per `/comm` i el directori per `/Register`.

1. Agent Directory

```bash
.venv/bin/python -m agents.agent_directory --host 127.0.0.1 --port 9000
```

1. Agent Opinador

```bash
.venv/bin/python -m agents.agent_opinador --host 127.0.0.1 --port 9004 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

1. Transportista ràpid

```bash
.venv/bin/python -m agents.agent_transportista --host 127.0.0.1 --port 9010 --transport-id fast --price-per-kg 8.0 --delivery-days 1
```

1. Transportista econòmic

```bash
.venv/bin/python -m agents.agent_transportista --host 127.0.0.1 --port 9011 --transport-id economy --price-per-kg 4.0 --delivery-days 3
```

1. Agent Proveïdor de Pagament (banc extern)

```bash
.venv/bin/python -m agents.agent_proveidor_de_pagament --host 127.0.0.1 --port 9006 --directory-host 127.0.0.1 --directory-port 9000
```

1. Agent Cobrador

```bash
.venv/bin/python -m agents.agent_cobrador --host 127.0.0.1 --port 9005 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

1. Agent Centre Logístic

```bash
.venv/bin/python -m agents.agent_centre_logistic --host 127.0.0.1 --port 9003 --directory-host 127.0.0.1 --directory-port 9000 --transport-fast-host 127.0.0.1 --transport-fast-port 9010 --transport-economy-host 127.0.0.1 --transport-economy-port 9011 --data-dir data
```

1. Agent Compra

```bash
.venv/bin/python -m agents.agent_compra --host 127.0.0.1 --port 9002 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

1. Agent Cercador

```bash
.venv/bin/python -m agents.agent_cercador --host 127.0.0.1 --port 9001 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

Quan tots els agents estiguin en marxa, obre:

`http://127.0.0.1:9001/iface`

Endpoints principals:

- `DirectoryAgent`: `/Register`, `/Info`, `/Stop`
- `CercadorAgent`, `CompraAgent`, `CentreLogisticAgent`, `OpinadorAgent`, `Transportista`, `CobradorAgent`, `ProveidorPagamentAgent`: `/comm`, `/iface`, `/Stop`

L'ordre d'arrencada recomanat és: Directory, Proveïdor de Pagament i Cobrador (gestió del pagament), després Opinador i Transportistes, i finalment Centre Logístic, Compra i Cercador. El Cobrador i el Proveïdor s'han d'aixecar abans del Centre Logístic i la Compra perquè aquests els resolen pel Directory en el moment de cobrar.

## 3) Regenerar dades aleatòries del catàleg

El catàleg RDF de `productes.ttl` i les ubicacions de `ubicacions_productes.ttl` es poden generar aleatòriament a partir d'una plantilla de categories, marques i rangs coherents.

Exemple:

```bash
.venv/bin/python -m services.bootstrap --data-dir data --product-count 24
```

Si vols que el catàleg sigui reproduïble entre execucions:

```bash
.venv/bin/python -m services.bootstrap --data-dir data --product-count 24 --seed 21
```
