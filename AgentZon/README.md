# AgentZon

AgentZon és un prototip de sistema multiagent per a l'assignatura ECSDI. Implementa una botiga distribuïda amb cerca de productes, compra i gestió logística basada en ontologia RDF/OWL.

Per una explicació detallada de l'arquitectura i els fluxos, consulta [`GUIA_NOU_INTEGRANT.md`](GUIA_NOU_INTEGRANT.md).

## Flux híbrid de lots i enviament

El flux de compra i logística és ara híbrid:

- `Compra` retorna immediatament un `ResultatCompra` amb la data estimada (`DataEntrega`) i les reserves de lot localitzades.
- `Centre Logístic` només negocia el transport quan un lot queda `PREPARAT`.
- Un lot passa a `PREPARAT` quan arriba al límit de pes o quan un nou lot ha d'obrir-se perquè l'anterior desbordaria la capacitat.
- Els lots oberts però imminents també es poden promoure amb l'escombrat diari `GET /cron/negotiate-ready-lots`.
- Quan la negociació acaba, `Compra` rep `DadesEnviament` (`ASSIGNAT`) amb la data definitiva i el transportista.
- Quan el lot s'envia, `Compra` rep `ConfirmacioEnviament` (`ENVIAT`) i la comanda queda actualitzada a `/orders/<order_id>`.

## 1) Generar documentació i graf de l'ontologia

Des de `AgentZon/` (amb l'entorn virtual activat; vegeu la secció 2):

```bash
cd AgentZon
python -m pylode ontologia/AgentZonOntology.rdf -o ontologia/docs/ontology.html
```

Generar el graf de l'ontologia (cal tenir instal·lat Graphviz: `dot`):

```bash
rdf2dot ontologia/AgentZonOntology.rdf | dot -Tpng -o ontologia/docs/ontology_graph.png
```

## 2) Preparar l'entorn (un sol cop)

Des de l'arrel del repositori:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

També pots crear el virtualenv dins de `AgentZon/.venv`; el script `run_agents.sh` accepta qualsevol dels dos.

## 3) Executar el sistema distribuït

Totes les comandes d'aquesta secció s'executen des de **`AgentZon/`** (és el directori de treball dels agents). La interfície humana viu a `/iface`; els agents es comuniquen per `/comm` i el directori per `/Register`.

### Opció A (recomanada, macOS)

Un script obre una finestra de Terminal per agent (12 processos):

```bash
cd AgentZon
chmod +x run_agents.sh   # només la primera vegada
./run_agents.sh
```

Variables opcionals: `HOST`, `DELAY_SECONDS`, `OPEN_BROWSER=0` (per no obrir el navegador automàticament).

### Opció B (manual)

Obre **una terminal per agent** i executa les comandes següents des de `AgentZon/`. **L'ordre importa**:

1. Directory  
2. Cobrador  
3. Opinador, Retornador i transportistes  
4. Centres Logístics, Compra i Cercador (aquest últim, el que exposa la UI)

Substitueix `.venv/bin/python` per `../.venv/bin/python` si el virtualenv està a l'arrel del repositori.

**1. Agent Directory**

```bash
.venv/bin/python -m agents.agent_directory --host 127.0.0.1 --port 9000
```

**2. Agent Cobrador**

```bash
.venv/bin/python -m agents.agent_cobrador --host 127.0.0.1 --port 9005 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

**3. Agent Opinador**

```bash
.venv/bin/python -m agents.agent_opinador --host 127.0.0.1 --port 9004 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

**4. Agent Retornador**

```bash
.venv/bin/python -m agents.agent_retornador --host 127.0.0.1 --port 9009 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

**5. Transportista ràpid**

```bash
.venv/bin/python -m agents.agent_transportista --host 127.0.0.1 --port 9010 --directory-host 127.0.0.1 --directory-port 9000 --transport-id fast --price-per-kg 8.0 --delivery-days 1
```

**6. Transportista econòmic**

```bash
.venv/bin/python -m agents.agent_transportista --host 127.0.0.1 --port 9011 --directory-host 127.0.0.1 --directory-port 9000 --transport-id economy --price-per-kg 4.0 --delivery-days 3
```

**7–9. Agents Centre Logístic (BCN, Girona, Tarragona)**

```bash
.venv/bin/python -m agents.agent_centre_logistic --host 127.0.0.1 --port 9003 --centre-id CL-BCN --centre-city Barcelona --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

```bash
.venv/bin/python -m agents.agent_centre_logistic --host 127.0.0.1 --port 9007 --centre-id CL-GI --centre-city Girona --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

```bash
.venv/bin/python -m agents.agent_centre_logistic --host 127.0.0.1 --port 9008 --centre-id CL-TGN --centre-city Tarragona --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

**10. Agent Compra**

```bash
.venv/bin/python -m agents.agent_compra --host 127.0.0.1 --port 9002 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

**11. Agent Cercador**

```bash
.venv/bin/python -m agents.agent_cercador --host 127.0.0.1 --port 9001 --directory-host 127.0.0.1 --directory-port 9000 --data-dir data
```

### Interfície i endpoints

Quan tots els agents estiguin en marxa, obre:

`http://127.0.0.1:9001/iface`

Endpoints principals:

- `DirectoryAgent`: `/Register`, `/Info`, `/Stop`
- `CercadorAgent`, `CompraAgent`, `CentreLogisticAgent`, `OpinadorAgent`, `RetornadorAgent`, `Transportista`, `CobradorAgent`: `/comm`, `/iface`, `/Stop`

Per forçar la negociació dels lots oberts amb entrega imminent:

```bash
curl "http://127.0.0.1:9003/cron/negotiate-ready-lots"
curl "http://127.0.0.1:9007/cron/negotiate-ready-lots"
curl "http://127.0.0.1:9008/cron/negotiate-ready-lots"
```

Per a la demo: el sistema ha de funcionar **realment distribuït**. Pots executar agents en màquines diferents passant `--host` i `--directory-host` amb les IP reals.

### Aturar agents, terminals i ports actius

Si has obert els agents amb `./run_agents.sh` o manualment i vols reiniciar net (errors `Address already in use`, processos penjats, etc.), executa des de qualsevol directori:

```bash
# 1) Aturar tots els processos Python dels agents
pkill -f '[Pp]ython.*-m agents\.agent_' 2>/dev/null || true

# 2) Alliberar els ports reservats per AgentZon (9000–9009, 9010–9011)
for port in 9000 9001 9002 9003 9004 9005 9006 9007 9008 9009 9010 9011; do
  lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null
done
```

Comprovar que no queda res en escolta:

```bash
lsof -nP -iTCP:9000-9011 -sTCP:LISTEN
```

Si has usat `./run_agents.sh` a macOS, tanca també les finestres de Terminal que han quedat obertes (Cmd+W a cada una, o tanca-les des del menú Terminal).

## 4) Regenerar dades de prova

El catàleg RDF de `productes.ttl` i les ubicacions de `ubicacions_productes.ttl` es poden generar aleatòriament.

Des de `AgentZon/`:

```bash
cd AgentZon
.venv/bin/python -m services.bootstrap --data-dir data --product-count 24
```

Per reproduir el mateix catàleg entre execucions:

```bash
.venv/bin/python -m services.bootstrap --data-dir data --product-count 24 --seed 21
```

## 5) Passar els tests

Des de `AgentZon/`:

```bash
cd AgentZon
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Han de passar **tots** els tests. En entorns sandboxats on no es poden obrir ports locals, `test_distributed_smoke` es marca com a `skipped`.
