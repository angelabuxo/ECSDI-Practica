# Execucio distribuida d'AgentZon

Aquest flux arrenca cada agent en un proces Flask separat. Els endpoints HTTP
transporten missatges RDF/XML amb estructura FIPA-ACL; la logica dels agents
continua treballant amb els conceptes de l'ontologia AgentZon.

Executa les comandes des de l'arrel del repositori `ECSDI-Practica`.

## Ports locals

| Agent | Port | Endpoint principal |
| --- | ---: | --- |
| DirectoryAgent | 9000 | `/Register`, `/Info` |
| Agent Cercador | 9001 | `/` |
| Agent Compra | 9002 | `/`, `/comm` |
| Agent Centre Logistic BCN | 9003 | `/comm` |
| Agent Centre Logistic MAD | 9004 | `/comm` |
| Agent Transportista A | 9011 | `/comm` |
| Agent Transportista B | 9012 | `/comm` |

## Ordre d'arrencada local

Terminal 1:

```bash
python -m AgentZon.agents.agent_directory --host 127.0.0.1 --port 9000
```

Terminal 2:

```bash
python -m AgentZon.agents.agent_transportista \
  --id transport-a \
  --cost-base 5 \
  --dies-extra 0 \
  --port 9011
```

Terminal 3:

```bash
python -m AgentZon.agents.agent_transportista \
  --id transport-b \
  --cost-base 8 \
  --dies-extra 1 \
  --port 9012
```

Terminal 4:

```bash
python -m AgentZon.agents.agent_centre_logistic \
  --id magatzem-bcn \
  --ubicacio Barcelona \
  --port 9003
```

Terminal 5:

```bash
python -m AgentZon.agents.agent_centre_logistic \
  --id magatzem-mad \
  --ubicacio Madrid \
  --port 9004
```

Terminal 6:

```bash
python -m AgentZon.agents.agent_compra --port 9002
```

Terminal 7:

```bash
python -m AgentZon.agents.agent_cercador
```

Consulta el directori a:

```text
http://127.0.0.1:9000/Info
```

## Execucio en maquines diferents

Canvia `--host` a `0.0.0.0` en els agents que hagin d'acceptar connexions
remotes i passa `--address` amb la URL visible des de la resta de maquines.

Exemple:

```bash
python -m AgentZon.agents.agent_transportista \
  --id transport-a \
  --cost-base 5 \
  --dies-extra 0 \
  --host 0.0.0.0 \
  --port 9011 \
  --address http://192.168.1.42:9011/comm \
  --directory http://192.168.1.10:9000/Register
```

El DirectoryAgent ha d'estar arrencat abans que la resta d'agents perquè es
puguin registrar correctament.
