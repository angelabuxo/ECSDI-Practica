# Execucio distribuida d'AgentZon

Aquest flux arrenca cada agent en un proces Flask separat. Els endpoints HTTP
transporten missatges RDF/XML amb estructura FIPA-ACL i el contingut es modela
amb els conceptes de l'ontologia AgentZon. Els endpoints `/Info` exposen
l'estat RDF actual de cada agent en format Turtle per poder-lo inspeccionar i
consultar externament.

Executa les comandes des de l'arrel del repositori `ECSDI-Practica`.
Per evitar problemes de dependències, usa la venv del projecte:
`./AgentZon/.venv/bin/python`.

## Ports locals

| Agent | Port | Endpoints |
| --- | ---: | --- |
| DirectoryAgent | 9000 | `/Register`, `/Info` |
| Agent Cercador | 9001 | `/`, `/Info` |
| Agent Compra | 9002 | `/`, `/comm`, `/Info` |
| Agent Centre Logistic BCN | 9003 | `/comm`, `/Info` |
| Agent Centre Logistic MAD | 9004 | `/comm`, `/Info` |
| Agent Transportista A | 9011 | `/comm`, `/Info` |
| Agent Transportista B | 9012 | `/comm`, `/Info` |

## Ordre d'arrencada local

Terminal 1:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_directory --host 127.0.0.1 --port 9000
```

Terminal 2:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista \
  --id transport-a \
  --cost-base 5 \
  --dies-extra 0 \
  --port 9011
```

Terminal 3:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista \
  --id transport-b \
  --cost-base 8 \
  --dies-extra 1 \
  --port 9012
```

Terminal 4:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_centre_logistic \
  --id magatzem-bcn \
  --ubicacio Barcelona \
  --port 9003
```

Terminal 5:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_centre_logistic \
  --id magatzem-mad \
  --ubicacio Madrid \
  --port 9004
```

Terminal 6:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_compra --port 9002
```

Terminal 7:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_cercador
```

## Inspeccio RDF

Pots consultar l'estat RDF serialitzat en Turtle a:

- `http://127.0.0.1:9000/Info` per veure el directori d'agents registrats.
- `http://127.0.0.1:9001/Info` per veure ontologia i cataleg carregat al Cercador.
- `http://127.0.0.1:9002/Info` per veure comandes, assignacions i dades d'enviament gestionades per l'Agent Compra.
- `http://127.0.0.1:9003/Info` i `http://127.0.0.1:9004/Info` per veure lots, peticions de transport, ofertes i seleccions dels centres logistics.
- `http://127.0.0.1:9011/Info` i `http://127.0.0.1:9012/Info` per veure peticions rebudes i ofertes generades pels transportistes.

Els endpoints `/comm` i `/Register` continuen sent els canals de missatgeria
RDF/XML; `/Info` existeix només com a punt de depuracio i validacio semantica.

## Execucio en maquines diferents

Canvia `--host` a `0.0.0.0` en els agents que hagin d'acceptar connexions
remotes i passa `--address` amb la URL visible des de la resta de maquines.

Exemple:

```bash
./AgentZon/.venv/bin/python -m AgentZon.agents.agent_transportista \
  --id transport-a \
  --cost-base 5 \
  --dies-extra 0 \
  --host 0.0.0.0 \
  --port 9011 \
  --address http://192.168.1.42:9011/comm \
  --directory http://192.168.1.10:9000/Register
```

El DirectoryAgent ha d'estar arrencat abans que la resta d'agents perquè es
puguin registrar correctament. Per a la demostracio distribuida, mantingues
els transportistes i com a minim un centre logistic en processos o maquines
separades de la resta.
