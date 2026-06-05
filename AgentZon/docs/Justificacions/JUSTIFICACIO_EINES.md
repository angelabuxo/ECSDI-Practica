# Justificació de les eines emprades a AgentZon

Aquest document explica, eina per eina, **per què** i **com** hem fet servir cadascuna de les
tecnologies de la pràctica, demostrant que ens hem cenyit **únicament** a allò que descriu la
documentació de laboratori del professor (`REFERENCE/ecsdiLab.md`, idèntica al PDF) i que ho hem
fet **de la manera que ell ho explica i exemplifica** (agents d'exemple del Capítol 6).

Cada apartat indica:
- **On ho diu el professor** (capítol/secció de `ecsdiLab.md`).
- **Com ho fem nosaltres** (fitxer i línies del projecte).
- **Per què** la nostra implementació és la mateixa que la documentada.

> Objectiu: si el professor pregunta "per què heu fet servir això?", aquí hi ha la resposta amb
> referències concretes al seu propi document.

---

## Taula resum

| Eina / patró | On ho explica el professor | On ho fem nosaltres | Veredicte |
|---|---|---|---|
| **Flask** (servidor REST de l'agent) | Cap. 3.1–3.2.1 | tots els `agents/agent_*.py`, `AgentUtil/FlaskServer.py` | ✅ Igual que els exemples |
| **requests** (peticions entre agents) | Cap. 3.3 | `AgentUtil/ACLMessages.py` (`send_message`) | ✅ `requests.get(url, params=...)` |
| **rdflib** (grafs, nodes, literals) | Cap. 4.2.1–4.2.2 | `protocols/*.py`, `services/rdf_store.py`, `AgentUtil/ACLMessages.py` | ✅ `Graph`, `Namespace`, `add`, `value`, `parse`, `serialize` |
| **SPARQL sobre graf local** | Cap. 4.2.4 | `services/catalog_service.py` | ✅ `graph.query("""PREFIX… SELECT…""")` |
| **FIPA-ACL com a `ClosedNamespace`** | Cap. 6.1 | `AgentUtil/ACL.py`, `AgentUtil/ACLMessages.py` | ✅ `build_message` / `get_message_properties` |
| **Directory Service Ontology (DSO)** | Cap. 6.1 | `AgentUtil/DSO.py`, `agents/agent_directory.py` | ✅ `DSO.Register`, `DSO.Search`, `FOAF.Agent`/`FOAF.name` |
| **Protocol request → not-understood/confirm/inform** | Cap. 6.1–6.2 | tots els `/comm` | ✅ Mateix protocol |
| **Protocols d'ownership entre agents** | Cap. 6.1–6.2 | `protocols/cerca.py`, `protocols/compra.py`, `protocols/opinador.py`, `protocols/pagament.py` | ✅ Mateix patró ACL/RDF, sense accessos directes a BDs alienes |
| **Generació aleatòria de dades** | Cap. 5.2 (`RandomInfo.py`) | `services/bootstrap.py` | ✅ Mateixa idea |
| **Concurrència amb `multiprocessing`** | Cap. 2 + Cap. 6 | `config.py` (`serve_agent`) + tots els `main()` | ✅ `Process` + `Queue` + `join` |
| **SPARQLWrapper** | Cap. 4.3 | *(no usat — justificat)* | ✅ No aplica al nostre domini |
| **flask-restful** | Cap. 3.2 (extensió opcional) | *(no usat — justificat)* | ✅ Opcional |

---

## 1. Flask — el servidor REST de cada agent

**On ho diu el professor (Cap. 3.1, 3.2, 3.2.1):**
> "La arquitectura de servicios web basada en REST […] la usaremos como metodología de desarrollo
> de sistemas multiagentes desplegados en un entorno distribuido."
> "Una aplicación de Flask se implementa a partir de la clase Flask. […] Una ruta se define con el
> decorador `@app.route('/path/to/operation')`."
> "Podemos configurarla mediante los parámetros `host` y `port` […] `app.run(host=…, port=…)`."

També al Cap. 6.2 descriu que un agent d'informació té exactament tres rutes: `/comm`, `/iface` i
`/Stop`.

**Com ho fem nosaltres:** cada agent és una `app = Flask(__name__)` amb les mateixes rutes que
els exemples. El Directory afegeix `/Register` i `/Info`, tal com `SimpleDirectoryService`
(Cap. 6.1). L'aturada usa el mateix helper del professor:

```1:17:AgentZon/AgentUtil/FlaskServer.py
"""Helpers for stopping Flask servers launched by AgentZon agents.

@author: javier
"""

__author__ = "javier"

from flask import request


def shutdown_server():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        return False
    func()
    return True
```

**Per què:** és literalment la metodologia que imposa el laboratori per desplegar el sistema
multiagent (un servei REST per agent). No hem introduït cap altre framework web.

---

## 2. requests — la comunicació entre agents

**On ho diu el professor (Cap. 3.3):**
> "La librería Requests permite hacer peticiones a un servidor web de manera sencilla."
> "Los parámetros se pasan a las peticiones como un diccionario python, por ejemplo
> `r = requests.get('http://…', params=peticion)`."

El Cap. 6.2 afegeix que l'enviament de missatges entre agents es fa amb
`AgentUtil.send_message`, que "se encarga de serializar el mensaje, enviarlo a la dirección del
agente destino, esperar la respuesta y convertirla en un grafo RDF".

**Com ho fem nosaltres:** exactament això. `send_message` serialitza el graf, fa el `GET` amb
`params`, i torna a convertir la resposta en graf:

```39:45:AgentZon/AgentUtil/ACLMessages.py
def send_message(gmess, address, timeout=10):
    payload = gmess.serialize(format="xml")
    response = requests.get(address, params={"content": payload}, timeout=timeout)
    response.raise_for_status()
    graph = Graph()
    graph.parse(data=response.text, format="xml")
    return graph
```

**Per què:** és el patró de comunicació documentat (`requests.get` amb `params`). No fem servir
cap altra llibreria HTTP ni cap protocol alternatiu.

Després del refactor d'ownership hem afegit missatges com `PeticioConsultaProductes`,
`PeticioRegistreCerca`, `PeticioConsultaCompresUsuari`, `PeticioConsultaDadesBancariesVenedor` o
`PeticioRegistreProducteExternCompra`, però **tots** continuen passant exactament pel mateix camí:
`Graph` RDF → `build_message(...)` → `requests.get(..., params={"content": ...})` → resposta
`inform`/`confirm` parsejada amb `rdflib`. Per tant, la tècnica no canvia; només augmenta el nombre
de casos d'ús coberts per l'arquitectura del laboratori.

---

## 3. rdflib — la representació del contingut dels missatges i les dades

**On ho diu el professor (Cap. 4.2.1, 4.2.2):**
> "La librería rdflib permite crear, manipular, consultar y almacenar grafos RDF (y OWL)."
> "La estructura básica […] es el objeto `Graph`. […] Podemos definir un espacio de nombres […]
> mediante la clase `Namespace`. […] Podemos añadir tripletas a un grafo mediante el método `add`."
> "Para cargar un fichero […] utilizar el método `parse`. […] Para grabar […] el método
> `serialize`."

**Com ho fem nosaltres:**
- Espais de noms amb `Namespace` (p. ex. `AZON`, `AGN`, `DSO`, `ACL`).
- Construcció de missatges amb `Graph()` + `add((s, p, o))` a tots els `protocols/*.py`.
- Persistència amb `parse`/`serialize` a `services/rdf_store.py`.
- Lectura de propietats amb `graph.value(subject=…, predicate=…)`, tal com els exemples del Cap. 6.

Exemple de construcció d'un missatge FIPA-ACL amb `add` (Cap. 4.2.1):

```21:36:AgentZon/AgentUtil/ACLMessages.py
def build_message(gmess, perf, sender=None, receiver=None, content=None, ontology=None, msgcnt=0):
    mssid = f"message-{hash(sender)}-{msgcnt:04d}"
    ms = URIRef(mssid)
    gmess.bind("acl", ACL)
    gmess.add((ms, RDF.type, OWL.NamedIndividual))
    gmess.add((ms, RDF.type, ACL.FipaAclMessage))
    gmess.add((ms, ACL.performative, perf))
    if sender is not None:
        gmess.add((ms, ACL.sender, sender))
    if receiver is not None:
        gmess.add((ms, ACL.receiver, receiver))
    if content is not None:
        gmess.add((ms, ACL.content, content))
    if ontology is not None:
        gmess.add((ms, ACL.ontology, ontology))
    return gmess
```

**Per què:** rdflib és l'eina obligatòria de web semàntica del laboratori i la fem servir amb les
mateixes primitives que documenta (`Graph`, `Namespace`, `add`, `value`, `parse`, `serialize`).

---

## 4. SPARQL — consultes sobre el graf local

**On ho diu el professor (Cap. 4.2.4):**
> "El acceso a consultas más complejas […] se puede realizar utilizando el lenguaje SPARQL mediante
> los métodos `query` y `update`."
> Exemple: `res = g.query("""PREFIX foaf: <…> SELECT … WHERE { … }""")`.

**Com ho fem nosaltres:** el catàleg de productes es consulta amb `graph.query(...)` i prefixos
`PREFIX`, exactament com l'exemple del document:

```10:26:AgentZon/services/catalog_service.py
def search_products(catalog_path, criteria):
    graph = load_graph(catalog_path)
    query = """
        PREFIX azon: <http://www.semanticweb.org/agentzon#>
        SELECT ?id ?name ?description ?category ?brand ?price ?weight
        WHERE {
            ?product a azon:Producte ;
                azon:IdProducte ?id ;
                azon:Nom ?name ;
                azon:Descripcio ?description ;
                azon:Categoria ?category ;
                azon:Marca ?brand ;
                azon:Preu ?price ;
                azon:Pes ?weight .
        }
    """
    rows = graph.query(query)
```

**Per què:** és el mètode que el professor descriu per consultar un graf RDF local
(`Graph.query`). No necessitem res més perquè les nostres dades són locals (vegeu §10).

---

## 5. FIPA-ACL — l'embolcall estàndard dels missatges

**On ho diu el professor (Cap. 6.1):**
> "Este mensaje sigue el formato de FIPA-ACL. El vocabulario de esta ontología se importa de la
> clase `AgentUtil.ACL` como un `ClosedNamespace`."
> "Para facilitar el tratamiento del mensaje la función `ACLMessages.get_message_properties` extrae
> los campos del mensaje como un diccionario."
> "La función `ACLMessages.build_message` se encarga de construir el mensaje FIPA-ACL."

**Com ho fem nosaltres:** importem `ACL` com a `ClosedNamespace` (a `AgentUtil/ACL.py`) i fem servir
els mateixos `build_message` i `get_message_properties` per construir i llegir els missatges
(vegeu el codi de `ACLMessages.py` citat a §3 i a continuació):

```49:69:AgentZon/AgentUtil/ACLMessages.py
def get_message_properties(msg):
    props = {
        "performative": ACL.performative,
        "sender": ACL.sender,
        "receiver": ACL.receiver,
        "ontology": ACL.ontology,
        "conversation-id": ACL["conversation-id"],
        "in-reply-to": ACL["in-reply-to"],
        "content": ACL.content,
    }

    message = msg.value(predicate=RDF.type, object=ACL.FipaAclMessage)
    if message is None:
        return {}

    data = {}
    for key, predicate in props.items():
        value = msg.value(subject=message, predicate=predicate)
        if value is not None:
            data[key] = value
    return data
```

**Per què:** el laboratori imposa FIPA-ACL com a protocol de comunicació i ens dóna aquestes dues
funcions; les fem servir tal qual, sense reinventar el format del missatge.

Això és especialment rellevant per al refactor d'ownership: quan `Compra` necessita snapshots del
catàleg, `Retornador` necessita compres d'usuari, o `VenedorExtern` necessita el perfil bancari,
no es llegeixen fitxers `.ttl` aliens. Es fa una **petició ACL `request`** a l'agent propietari i
es rep una **resposta ACL `inform`/`confirm`** amb contingut RDF. El patró segueix sent el del
Capítol 6; simplement l'apliquem també a les consultes internes entre agents.

---

## 6. Directory Service (DSO + FOAF) — registre i descoberta d'agents

**On ho diu el professor (Cap. 6.1):**
> "Las acciones posibles están definidas en la ontología Directory Service Ontology […]. Estas se
> importan de la clase `AgentUtil.DSO` […]. Este agente solo implementa el proceso de dos acciones
> `DSO.Register` y `DSO.Search`."
> "Esta información se representa usando DSO y FOAF […] se usa la clase `FOAF.Agent` […] y la
> relación `FOAF.Name`."

**Com ho fem nosaltres:** el nostre `agent_directory.py` registra amb `FOAF.Agent` + `FOAF.name` i
processa només `DSO.Register` i `DSO.Search`, igual que `SimpleDirectoryService`:

```62:67:AgentZon/agents/agent_directory.py
    name = message_graph.value(content, FOAF.name)
    ...
    DIRECTORY_GRAPH.add((uri, RDF.type, FOAF.Agent))
    DIRECTORY_GRAPH.add((uri, FOAF.name, name))
```

I el registre de cada agent es fa amb una acció `DSO.Register` dins d'un missatge `request`
(`AgentUtil/ACLMessages.py`, `register_agent`, línies 103–123).

**Per què:** el Directory és l'únic punt fix del sistema (com diu el professor) i el modelem amb
la seva ontologia DSO + FOAF, sense afegir vocabulari de registre propi més enllà del mínim que ell
permet ("se puede extender DSO").

---

## 7. Protocol d'interacció (not-understood / confirm / inform)

**On ho diu el professor (Cap. 6.1, 6.2):**
> "Si recibimos un mensaje que no corresponde con lo que esperamos debemos contestar diciendo que
> no lo hemos entendido (`not-understood`), si es una petición de registro debemos confirmar la
> acción (`confirm`) y si es de búsqueda hemos de informar del resultado (`inform`)."

**Com ho fem nosaltres:** el `/comm` del Directory respon `not-understood` si el missatge no és
vàlid o no és un `request`, `confirm` en un registre i `inform` en una cerca:

```113:129:AgentZon/agents/agent_directory.py
        return build_message(
            ...
            ACL["not-understood"],
            ...
    if action == DSO.Register:
        ...
    elif action == DSO.Search:
        ...
        response = build_message(
            ...
            ACL["not-understood"],
```

La resta d'agents segueixen el mateix esquema al seu `/comm`.

**Per què:** és exactament el protocol de peticions entre agents descrit al Capítol 6.

---

## 8. Generació aleatòria de dades de productes

**On ho diu el professor (Cap. 5.2):**
> "Una posibilidad es que generéis de manera aleatoria una base de datos de productos. […] En el
> repositorio […] tenéis el script `RandomInfo.py` que os puede servir de ejemplo."

**Com ho fem nosaltres:** `services/bootstrap.py` genera el catàleg (`productes.ttl`) i les
ubicacions de forma aleatòria però **reproduïble** (amb `seed`), instanciant les classes de la
nostra ontologia.

**Per què:** seguim la recomanació del professor de generar dades sintètiques a partir de
l'ontologia, ja que no hi ha una font gratuïta real (com explica ell mateix sobre amazon.com).

---

## 9. Concurrència amb `multiprocessing` — l'agent com a servidor + comportament

**On ho diu el professor (Cap. 2.1 i Cap. 6):**
> "Un agente está compuesto de diferentes comportamientos que se ejecutan de manera concurrente.
> […] utilizaremos diferentes hilos concurrentes."
> I als exemples (Cap. 6.1–6.3): `ab1 = Process(target=agentbehavior1); ab1.start(); app.run(...);
> ab1.join()`. El comportament fa el **registre al directori** i "se queda esperando leyendo de la
> cola […]. Este proceso acaba cuando recibe un 0 a través de la cola."

A més, `multiprocessing` és una de les llibreries que el Cap. 1.1 marca com a **necessàries** per a
la pràctica.

**Com ho fem nosaltres:** hem centralitzat aquest patró a `config.py::serve_agent`, que tots els
agents criden al seu `main()`. Llança un `Process` (el `agentbehavior1` del professor) que registra
l'agent i espera a una `Queue`, mentre `app.run` corre en paral·lel; en aturar, diposita un `0` a la
cua i fa `join`:

```118:139:AgentZon/config.py
def serve_agent(app, hostname, port, register_fn=None):
    """Arrenca el comportament concurrent en un Process + el servidor Flask.

    Segueix el patró dels exemples del professor:
    `Process(target=agentbehavior1, args=(cola,))` + `app.run(...)` + `join()`.
    El registre al directori passa dins del comportament concurrent.
    """
    try:
        context = multiprocessing.get_context("fork")
    except ValueError:  # plataformes sense fork (p.ex. Windows): context per defecte
        context = multiprocessing.get_context()
    queue = context.Queue()
    behaviour = context.Process(target=_agent_behaviour, args=(queue, register_fn))
    behaviour.daemon = True
    behaviour.start()
    try:
        app.run(host=hostname, port=port, debug=False, use_reloader=False)
    finally:
        queue.put(0)
        behaviour.join(timeout=5)
        if behaviour.is_alive():
            behaviour.terminate()
```

```98:115:AgentZon/config.py
def _agent_behaviour(queue, register_fn):
    """Comportament concurrent de l'agent.

    Replica `agentbehavior1` dels exemples (SimpleInfoAgent/SimpleDirectoryService):
    fa el registre al directori (si escau) i després queda a l'espera fins que el
    procés principal hi diposita un 0 a la cua per aturar-lo netament.
    """
    if register_fn is not None:
        register_fn()
    while True:
        try:
            if queue.get(timeout=1.0) == 0:
                return
        except queue_lib.Empty:
            # Si el procés principal (el servidor Flask) ha mort, ens aturem
            # per no quedar com a procés orfe.
            if os.getppid() == 1:
                return
```

A més, fem servir `concurrent.futures.ThreadPoolExecutor` per al **paral·lelisme intern** d'un agent
(p. ex. l'Agent Compra envia en paral·lel el registre bancari, l'historial i la logística;
`agent_compra.py`), cosa coherent amb la idea del Cap. 2.1 que un agent executa comportaments de
manera concurrent.

**Per què:** és el patró canònic dels agents d'exemple (`Process` + `Queue` + `join`) i compleix el
requisit del laboratori d'utilitzar `multiprocessing`. Així el sistema explota la distribució (un
procés per agent) i la concurrència, evitant solucions purament seqüencials.

---

## 10. Eines del laboratori que NO fem servir (i per què és correcte)

### SPARQLWrapper (Cap. 4.3)
**Què és segons el professor:** "SPARQLWrapper es una clase de python que facilita el hacer
consultas a un SPARQL point", amb l'exemple de consultar **DBpedia** (un *endpoint* remot).

**Per què no l'usem:** totes les nostres dades són **locals** (fitxers `.ttl` carregats a un
`Graph`), i el mateix document diu que per consultar un graf local s'usa `Graph.query` (Cap. 4.2.4),
que és el que fem (§4). SPARQLWrapper només té sentit contra un *endpoint* SPARQL extern, que el
nostre domini no té. Mantenim `AgentUtil/SPARQLPoints.py` (les constants d'exemple del professor)
present però sense usar-lo, per no introduir dependències innecessàries.

### flask-restful (Cap. 3.2)
**Què és segons el professor:** "una extensión que simplifica algunas tareas en el desarrollo de
servicios web REST".

**Per què no l'usem:** és **opcional** ("una extensión"), i els propis agents d'exemple del Capítol 6
funcionen amb Flask "pelat" i `@app.route`. Nosaltres fem el mateix, de manera que no cal
l'extensió.

---

## 11. Conclusió per al professor

Tot el sistema AgentZon està construït **exclusivament** amb les eines del laboratori i seguint els
**patrons dels agents d'exemple** del Capítol 6:

- Flask per als serveis REST (Cap. 3), `requests` per a la comunicació (Cap. 3.3).
- rdflib per a grafs/ontologies (Cap. 4.2) i SPARQL local amb `Graph.query` (Cap. 4.2.4).
- FIPA-ACL com a `ClosedNamespace` amb `build_message`/`get_message_properties` (Cap. 6.1).
- Directory Service amb DSO + FOAF i el protocol `request`→`not-understood`/`confirm`/`inform`
  (Cap. 6.1–6.2).
- Dades generades aleatòriament a partir de l'ontologia (Cap. 5.2).
- Concurrència amb `multiprocessing` (`Process` + `Queue` + `join`), tal com els exemples
  (Cap. 2 i Cap. 6).

Les úniques eines que el document menciona i que **no** apareixen (SPARQLWrapper i flask-restful)
estan justificades: la primera és per a *endpoints* remots que no tenim, i la segona és una extensió
opcional que els mateixos exemples no necessiten.
