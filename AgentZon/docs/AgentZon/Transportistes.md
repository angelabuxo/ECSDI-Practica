# Funcionament dels transportistes a AgentZon

## Resum

Els transportistes són agents externs que competeixen per portar els lots que prepara cada centre logístic. Cada transportista:

- es registra automàticament al directori
- rep peticions d'oferta dels centres logístics
- calcula un preu i una data d'entrega
- participa en una ronda simple de contraoferta
- pot acabar acceptat o rebutjat

El flux actual ja està implementat de punta a punta i és híbrid:

- `Compra` retorna immediatament un `ResultatCompra`
- `Centre Logístic` retorna una `ConfirmacioLocalitzacio`
- més endavant, quan el lot queda `ASSIGNAT`, `Compra` rep `DadesEnviament`
- finalment, quan el lot queda `ENVIAT`, `Compra` rep `ConfirmacioEnviament`

En altres paraules:

- `DadesEnviament = ASSIGNAT`
- `ConfirmacioEnviament = ENVIAT`

## Quants transportistes hi ha per defecte

L'script [run_agents.sh](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/run_agents.sh) aixeca dos transportistes d'exemple:

- `fast`: `8.0 EUR/kg` i `1` dia d'entrega
- `economy`: `4.0 EUR/kg` i `3` dies d'entrega

Això és només la configuració de demo. El sistema no està limitat a dos transportistes.

## Components implicats

- `agents/agent_transportista.py`: implementa el comportament d'un transportista concret.
- `agents/agent_centre_logistic.py`: demana ofertes, negocia, selecciona el guanyador i envia les actualitzacions a `Compra`.
- `agents/agent_compra.py`: crea la comanda, retorna `ResultatCompra`, rep `DadesEnviament` i `ConfirmacioEnviament`, i exposa `/orders/<order_id>`.
- `agents/agent_directory.py`: guarda els agents registrats i permet trobar tots els transportistes disponibles.
- `protocols/centre_logistic.py`: defineix els missatges de localització, oferta, contraoferta i actualització d'enviament.
- `services/logistics_service.py`: gestiona lots, estats, repartiment del cost i selecció d'ofertes.
- `services/shipping_tracking_service.py`: guarda el seguiment d'enviament al costat de `Compra`.

## Com es registra un transportista

Quan arrenca, un transportista es registra automàticament al directori com a `TransportistaAgent` amb:

- nom
- URI
- adreça HTTP
- `IdTransportista`

Aquest `IdTransportista` és el que després fan servir els centres logístics per identificar qui ha fet cada oferta.

## Què es pot configurar avui

Cada instància de transportista es configura amb aquests paràmetres:

- `--transport-id`
- `--price-per-kg`
- `--delivery-days`
- `--port`
- `--host`
- `--directory-host`
- `--directory-port`

Els tres primers són els que realment defineixen el comportament comercial:

- `transport_id`: identificador lògic del transportista
- `price_per_kg`: preu per quilo
- `delivery_days`: dies que suma a la data actual per construir la seva oferta

## Com es construeix una oferta

L'oferta inicial actual és molt simple:

- `preu = pes_total_lot * price_per_kg`
- `data_entrega_definitiva = avui + delivery_days`

Avui no hi ha:

- tarifa base fixa
- preus diferents per ciutat o zona
- preus diferents per prioritat
- trams de pes
- limitacions de capacitat del transportista

## Com negocia el centre logístic

El protocol implementat és aquest:

1. El centre logístic descobreix tots els transportistes registrats al directori.
2. Envia una `PeticioTransport` a tots en paral·lel.
3. Cada transportista respon amb una `RespostaOfertaTransport`.
4. El centre calcula una única contraoferta comuna:
   `contraoferta = preu_mes_barat - 0.01`
5. El centre envia aquesta contraoferta a cada transportista.
6. Cada transportista pot:
   - acceptar-la amb `agree`
   - rebutjar-la amb `refuse`
   - respondre amb una nova proposta amb `propose`
7. El centre tria l'oferta final guanyadora.
8. Envia `accept-proposal` al guanyador i `reject-proposal` a la resta.

## Regla de contraoferta del transportista

La regla del transportista també és simple:

- accepta directament si la contraoferta és com a mínim el `85%` del seu preu inicial
- si no arriba a aquest llindar, intenta proposar un preu intermedi
- si no hi ha marge per fer una proposta intermèdia vàlida, rebutja

Aquest llindar del `85%` està fixat al codi de [agent_transportista.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/agents/agent_transportista.py). Avui no es pot configurar per línia de comandes.

## Com s'escull el transportista guanyador

El criteri principal actual és el cost:

- si hi ha ofertes negociades, es tria entre les negociades
- si no n'hi ha, es tria entre les ofertes inicials
- guanya el preu final més baix

En cas d'empat exacte de preu, el codi ordena els candidats per:

- `delivery_date`
- `transport_id`

i després es queda amb el primer.

Per tant, la data d'entrega ajuda a desempatar, però no és el criteri principal de selecció.

## Quan es negocia un lot

Aquí és on el flux actual és híbrid.

### Fase 1: compra i localització

Quan l'usuari compra:

1. `Compra` crea la comanda.
2. `Compra` envia cada grup de productes al centre logístic corresponent.
3. Cada centre crea o reutilitza un lot.
4. El centre respon immediatament amb `ConfirmacioLocalitzacio`.
5. `Compra` retorna un `ResultatCompra` immediat amb la data estimada i les reserves de lot.

En aquest punt encara és normal que no hi hagi transportista assignat.

### Fase 2: preparació del lot

Els lots treballen amb aquests estats:

- `OBERT`
- `PREPARAT`
- `NEGOCIANT`
- `ASSIGNAT`
- `ENVIAT`

Els valors de configuració actuals són:

- `MAX_LOT_WEIGHT_KG = 5.0`
- `READY_DELIVERY_WINDOW_DAYS = 1`

Un lot passa a `PREPARAT` quan passa una d'aquestes coses:

- el pes total del lot arriba a `5.0 kg`
- el lot continua obert però la seva `DataEntrega` ja és imminent i un escombrat el promociona
- una nova reserva faria desbordar el lot actual, i llavors el lot vell es tanca com a `PREPARAT` i se n'obre un de nou

### Fase 3: negociació del transport

Un cop un lot és `PREPARAT`, la negociació no sempre es dispara exactament igual:

- si la reserva que acaba d'entrar deixa el lot retornat en estat `PREPARAT`, el centre pot disparar la negociació automàticament en segon pla
- si un lot antic queda tancat perquè la nova reserva desbordaria la seva capacitat, aquell lot vell queda `PREPARAT` però normalment es processa quan s'executa l'escombrat
- els lots oberts amb entrega imminent també es promocionen i es processen via `/cron/negotiate-ready-lots`

Important: avui no hi ha un scheduler intern que executi aquest escombrat cada dia. L'endpoint existeix, però s'ha de cridar externament o manualment.

L'endpoint és:

```text
GET /cron/negotiate-ready-lots
```

## Què passa després de la negociació

Quan el centre ja ha escollit el transportista:

1. marca el lot com a `ASSIGNAT`
2. envia `DadesEnviament` a `Compra`
3. marca el lot com a `ENVIAT`
4. activa el cobrament intern
5. envia `ConfirmacioEnviament` a `Compra`

Per tant:

- `DadesEnviament` comunica transportista i data definitiva
- `ConfirmacioEnviament` comunica que el lot ja s'ha enviat realment

## Com es reparteix el cost del transport

La negociació es fa per lot, no per producte ni per comanda individual.

Si un lot conté reserves de diverses comandes:

- el centre negocia un únic cost total del lot
- després reparteix aquest cost entre les reserves del lot proporcionalment al pes de cada reserva

Per això el preu que veu `Compra` en cada actualització pot ser el cost repartit de la reserva, no necessàriament el cost total del lot.

## Es poden crear tants transportistes com es vulgui

Sí, arquitectònicament sí.

Cada transportista és simplement una nova instància del procés `agents.agent_transportista`. Pots aixecar tants agents com vulguis sempre que cada instància tingui:

- un `--port` diferent
- un `--transport-id` diferent
- idealment un nom diferent

El directori no imposa cap límit i el centre logístic consulta tots els transportistes registrats.

### Exemple

```bash
cd AgentZon
.venv/bin/python -m agents.agent_transportista \
  --host 127.0.0.1 \
  --port 9012 \
  --directory-host 127.0.0.1 \
  --directory-port 9000 \
  --transport-id premium \
  --price-per-kg 12.5 \
  --delivery-days 1
```

I un altre:

```bash
cd AgentZon
.venv/bin/python -m agents.agent_transportista \
  --host 127.0.0.1 \
  --port 9013 \
  --directory-host 127.0.0.1 \
  --directory-port 9000 \
  --transport-id lowcost \
  --price-per-kg 3.2 \
  --delivery-days 5
```

Si el teu entorn virtual és a l'arrel del repositori i no a `AgentZon/.venv`, substitueix `.venv/bin/python` per `../venv/bin/python`.

## Es poden definir els preus

Sí, però avui només amb aquest model:

- preu variable per quilo via `--price-per-kg`
- data promesa via `--delivery-days`

Per tant, el que pots controlar sense tocar codi és:

- quant cobra per quilo cada transportista
- quants dies promet
- quants transportistes hi ha
- quina combinació de preu i termini competeix a cada negociació

El que no pots definir avui sense tocar codi és:

- un cost fix per enviament
- trams de pes
- preus per ciutat, província o zona
- preus diferents segons la prioritat de l'usuari
- una política pròpia de negociació per transportista
- el llindar del `85%`
- restriccions de capacitat o calendari

## Limitacions pràctiques

### 1. `transport_id` únic

És molt recomanable que cada transportista tingui un `transport_id` únic. Si hi ha duplicats, la correspondència entre ofertes i agents es torna ambigua.

### 2. Molts transportistes impliquen més càrrega

El centre consulta els transportistes en paral·lel amb un `ThreadPoolExecutor`. Funciona bé per a un nombre moderat d'agents, però si n'aixeques molts:

- augmenta el nombre de processos
- augmenta el nombre de peticions HTTP
- la negociació triga més

### 3. No hi ha retard real entre `ASSIGNAT` i `ENVIAT`

El model semàntic separa aquests dos estats, però avui el centre els emet dins del mateix cicle de processament del lot. Això vol dir que la diferència conceptual existeix, però no hi ha una espera temporal realista entre tots dos.

### 4. No hi ha scheduler automàtic del cron

El sistema exposa `GET /cron/negotiate-ready-lots`, però algú l'ha d'executar. Si no, alguns lots `PREPARAT` poden quedar pendents de negociació.

## Fitxers clau

- [agent_transportista.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/agents/agent_transportista.py)
- [agent_centre_logistic.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/agents/agent_centre_logistic.py)
- [agent_compra.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/agents/agent_compra.py)
- [centre_logistic.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/protocols/centre_logistic.py)
- [logistics_service.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/services/logistics_service.py)
- [shipping_tracking_service.py](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/services/shipping_tracking_service.py)
- [run_agents.sh](/Users/polmontanera/Desktop/Q6%202526/ECSDI/ECSDI-Practica/AgentZon/run_agents.sh)

## Com provar el flux dels transportistes

Hi ha dues maneres pràctiques de provar-lo: amb tests automàtics o manualment amb els agents en marxa.

### Opció 1: tests automàtics

Des de dins d'`AgentZon`, executa:

```bash
../venv/bin/python -m pytest \
  tests/test_transport_agent.py \
  tests/test_logistics_flow.py \
  tests/test_purchase_flow.py \
  -q
```

Això comprova, entre altres coses:

- que els transportistes es registren al directori
- que responen a una `PeticioTransport`
- que poden acceptar, rebutjar o contraofertar
- que el centre negocia i escull un guanyador
- que `Compra` rep primer el resultat inicial i després les actualitzacions d'enviament

Si el teu entorn virtual és `AgentZon/.venv`, pots substituir `../venv/bin/python` per `.venv/bin/python`.

### Opció 2: prova manual del sistema distribuït

#### 1. Arrenca els agents

Des de l'arrel del repositori:

```bash
cd AgentZon
bash run_agents.sh
```

#### 2. Obre la interfície

Quan tots els agents estiguin en marxa, obre:

```text
http://127.0.0.1:9001/iface
```

#### 3. Fes una compra

Des de la interfície:

1. Cerca un producte.
2. Inicia la compra.
3. Introdueix les dades d'enviament i la prioritat.

En aquest punt passa això:

- `Compra` crea la comanda
- envia els productes als centres logístics corresponents
- rep una o més `ConfirmacioLocalitzacio`
- retorna un `ResultatCompra` immediat

Per tant, la primera pantalla de resum pot mostrar perfectament:

- transportista pendent
- data estimada
- estat inicial de la comanda

#### 4. Força la negociació dels lots preparats

Si la negociació no s'ha disparat sola, pots forçar l'escombrat manualment:

```bash
curl "http://127.0.0.1:9003/cron/negotiate-ready-lots"
curl "http://127.0.0.1:9007/cron/negotiate-ready-lots"
curl "http://127.0.0.1:9008/cron/negotiate-ready-lots"
```

Això processa:

- lots que ja estan `PREPARAT`
- lots `OBERT` amb `DataEntrega` imminent segons la finestra `READY_DELIVERY_WINDOW_DAYS`

#### 5. Comprova el resultat

Pots mirar-ho de diverses maneres:

- als terminals dels transportistes veuràs les ofertes i la resposta a la contraoferta
- al terminal del centre logístic veuràs quin transportista ha guanyat
- a la pàgina de `Compra` veuràs l'enllaç `/orders/<order_id>`

Quan el flux ha acabat, a `/orders/<order_id>` hauries de veure:

- transportista final assignat
- data definitiva d'entrega
- estat `ENVIAT`

#### 6. Prova transportistes personalitzats

Pots afegir transportistes extra mentre el sistema està funcionant. Per exemple:

```bash
cd AgentZon
.venv/bin/python -m agents.agent_transportista \
  --host 127.0.0.1 \
  --port 9012 \
  --directory-host 127.0.0.1 \
  --directory-port 9000 \
  --transport-id premium \
  --price-per-kg 12.5 \
  --delivery-days 1
```

I un altre:

```bash
cd AgentZon
.venv/bin/python -m agents.agent_transportista \
  --host 127.0.0.1 \
  --port 9013 \
  --directory-host 127.0.0.1 \
  --directory-port 9000 \
  --transport-id lowcost \
  --price-per-kg 3.2 \
  --delivery-days 5
```

Si s'han registrat correctament, els següents lots que entrin en negociació els tindran en compte automàticament.
