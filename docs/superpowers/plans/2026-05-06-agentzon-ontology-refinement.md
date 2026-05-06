# AgentZon Ontology Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate AgentZon to a single Catalan `UpperCamelCase` ontology vocabulary, remove internal-agent ontology concepts, and align all RDF messages, persisted graphs, agents, seed data, and docs with FIPA-ACL-compliant envelopes.

**Architecture:** Keep the deployed agent topology intact and treat this as a semantic-layer migration. First establish the canonical ontology and ACL envelope boundary, then update protocol builders and parsers, then persist the same graph shapes in services and agents, and finally regenerate data fixtures and docs while running repository-wide vocabulary checks.

**Tech Stack:** Python, rdflib, OWL/RDF XML, Turtle, Flask, pytest, FIPA-ACL

---

## File Structure

- `AgentZon/ontologia/AgentZonOntology.rdf`
  Owns the canonical AgentZon vocabulary, class hierarchy, property domains/ranges, and removal of internal-agent concepts.
- `AgentZon/AgentUtil/OntoNamespaces.py`
  Owns the namespace constants and the ontology URI exported to message builders.
- `AgentZon/AgentUtil/ACLMessages.py`
  Owns ACL envelope construction/parsing and must add `acl:ontology` without reintroducing sender/receiver ontology terms.
- `AgentZon/protocols/cerca.py`
  Owns the RDF content of `PeticioCerca` and `ResultatCerca`.
- `AgentZon/protocols/compra.py`
  Owns the RDF content of `PeticioRegistreCompra` and `ConfirmacioRegistreCompra`.
- `AgentZon/protocols/centre_logistic.py`
  Owns the RDF content of `ProducteLocalitzat`, `PeticioTransport`, `RespostaOfertaTransport`, and the final shipping response.
- `AgentZon/services/catalog_service.py`
  Owns SPARQL access to product data and must be updated to refined property names.
- `AgentZon/services/order_service.py`
  Owns `Comanda` and `DadesEnviamentUsuari` persistence.
- `AgentZon/services/history_service.py`
  Owns `HistorialCerca` and `HistorialCompra` persistence.
- `AgentZon/services/logistics_service.py`
  Owns `Lot` persistence and lot-level `PesTotal`.
- `AgentZon/services/bootstrap.py`
  Owns seed graph generation for checked-in and temp test data.
- `AgentZon/agents/agent_cercador.py`
  Owns search flow orchestration and `ResultatCerca` responses.
- `AgentZon/agents/agent_compra.py`
  Owns purchase capture, shipping persistence, logistics requests, and purchase-history delegation.
- `AgentZon/agents/agent_centre_logistic.py`
  Owns lot creation, transport negotiation, and shipping-detail response flow.
- `AgentZon/agents/agent_transportista.py`
  Owns `RespostaOfertaTransport` generation.
- `AgentZon/agents/agent_opinador.py`
  Owns purchase-history registration flow.
- `AgentZon/data/*.ttl`
  Checked-in RDF fixtures that must not keep any legacy IRI.
- `AgentZon/tests/test_acl_messages.py`
  Covers message-envelope round-trip behavior.
- `AgentZon/tests/test_logistics_flow.py`
  Covers lot persistence and transport negotiation.
- `AgentZon/tests/test_purchase_flow.py`
  Covers browser-style search, purchase, and shipping flow.
- `AgentZon/docs/AgentZon/IMPLEMENTATION_AND_ONTOLOGY.md`
  Must describe the refined ontology boundary and remove `AgentIntern`.
- `AgentZon/docs/AgentZon/Entrega-3.md`
  Must describe classes, attributes, and relations using the refined vocabulary.

### Task 1: Canonical Ontology and ACL Boundary

**Files:**
- Create: `AgentZon/tests/test_ontology_alignment.py`
- Modify: `AgentZon/tests/test_acl_messages.py:8-47`
- Modify: `AgentZon/AgentUtil/OntoNamespaces.py:8-20`
- Modify: `AgentZon/AgentUtil/ACLMessages.py:21-67`
- Modify: `AgentZon/ontologia/AgentZonOntology.rdf:51-544`
- Modify: `AgentZon/ontologia/AgentZonOntology.rdf:561-1020`

- [ ] **Step 1: Write the failing tests**

```python
# AgentZon/tests/test_ontology_alignment.py
import unittest

from rdflib import Graph, OWL, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON


class OntologyAlignmentTests(unittest.TestCase):
    def test_refined_ontology_removes_internal_agent_branch_and_legacy_terms(self):
        graph = Graph()
        graph.parse("AgentZon/ontologia/AgentZonOntology.rdf", format="xml")

        self.assertIn((AZON.TeProducte, RDF.type, OWL.ObjectProperty), graph)
        self.assertIn((AZON.PesTotal, RDF.type, OWL.DatatypeProperty), graph)
        self.assertNotIn((AZON.AgentIntern, None, None), graph)
        self.assertNotIn((AZON.AgentCercador, None, None), graph)
        self.assertNotIn((AZON.AgentCompra, None, None), graph)
        self.assertNotIn((AZON.emissor, None, None), graph)
        self.assertNotIn((AZON.receptor, None, None), graph)
        self.assertNotIn((AZON.teProducte, None, None), graph)


if __name__ == "__main__":
    unittest.main()
```

```python
# AgentZon/tests/test_acl_messages.py
from AgentZon.AgentUtil.OntoNamespaces import ONTOLOGY_URI

message_graph = build_message(
    content_graph,
    ACL.request,
    sender=sender,
    receiver=receiver,
    content=content,
    ontology=ONTOLOGY_URI,
    msgcnt=1,
)

properties = get_message_properties(message_graph)
self.assertEqual(properties["ontology"], ONTOLOGY_URI)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest AgentZon/tests/test_acl_messages.py AgentZon/tests/test_ontology_alignment.py -q`
Expected: FAIL with `TypeError: build_message() got an unexpected keyword argument 'ontology'` and ontology assertions about missing `TeProducte` / `PesTotal` and still-present `AgentIntern` / `emissor` / `receptor`.

- [ ] **Step 3: Write the minimal implementation**

```python
# AgentZon/AgentUtil/OntoNamespaces.py
from rdflib import Namespace, URIRef


ONTOLOGY_URI = URIRef("http://www.semanticweb.org/agentzon")
AZON = Namespace(f"{ONTOLOGY_URI}#")
AGN = Namespace("http://www.agentes.org#")


def bind_namespaces(graph):
    graph.bind("azon", AZON)
    graph.bind("agn", AGN)
    graph.bind("acl", "http://www.nuin.org/ontology/fipa/acl#")
    graph.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    graph.bind("owl", "http://www.w3.org/2002/07/owl#")
    graph.bind("foaf", "http://xmlns.com/foaf/0.1/")
    return graph
```

```python
# AgentZon/AgentUtil/ACLMessages.py
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

```xml
<!-- AgentZon/ontologia/AgentZonOntology.rdf -->
<!-- Remove the complete object-property blocks for #emissor and #receptor -->

<owl:ObjectProperty rdf:about="http://www.semanticweb.org/agentzon#TeProducte">
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#Comanda"/>
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#Lot"/>
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#HistorialCompra"/>
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#PeticioRegistreCompra"/>
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#ProducteLocalitzat"/>
    <rdfs:range rdf:resource="http://www.semanticweb.org/agentzon#Producte"/>
    <rdfs:label xml:lang="ca">TeProducte</rdfs:label>
</owl:ObjectProperty>

<owl:DatatypeProperty rdf:about="http://www.semanticweb.org/agentzon#PesTotal">
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#Lot"/>
    <rdfs:domain rdf:resource="http://www.semanticweb.org/agentzon#PeticioTransport"/>
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#float"/>
    <rdfs:label xml:lang="ca">PesTotal</rdfs:label>
</owl:DatatypeProperty>
```

```text
# AgentZon/ontologia/AgentZonOntology.rdf
Apply the full IRI rename table from the approved design spec to every `agentzon#...` occurrence in the ontology file:

assignatATransportista -> AssignatATransportista
esRespostaA -> EsRespostaA
generaRecomanacio -> GeneraRecomanacio
mostraProducte -> MostraProducte
sobreComanda -> SobreComanda
sobreLot -> SobreLot
sobreProducte -> SobreProducte
teDadesBancaries -> TeDadesBancaries
teDadesEnviament -> TeDadesEnviament
teFeedback -> TeFeedback
teProducte -> TeProducte
ubicatACentre -> UbicatACentre
acceptada -> Acceptada
carrer -> Carrer
categoria -> Categoria
ciutat -> Ciutat
comentari -> Comentari
costTransport -> CostTransport
dataAlta -> DataAlta
dataCompra -> DataCompra
dataEntrega -> DataEntrega
descripcio -> Descripcio
estat -> Estat
idCentreLogistic -> IdCentreLogistic
idComanda -> IdComanda
idDevolucio -> IdDevolucio
idFeedback -> IdFeedback
idLot -> IdLot
idPagament -> IdPagament
idProducte -> IdProducte
idTransportista -> IdTransportista
idUsuari -> IdUsuari
importPagament -> ImportPagament
marca -> Marca
metodePagament -> MetodePagament
motiuDevolucio -> MotiuDevolucio
nom -> Nom
nomTransportista -> NomTransportista
pes -> Pes
preu -> Preu
preuMaxim -> PreuMaxim
preuMinim -> PreuMinim
prioritat -> Prioritat
puntuacio -> Puntuacio
requereixLogisticaExterna -> RequereixLogisticaExterna
skuExtern -> SkuExtern
teCategoria -> CategoriaConsulta
teMarca -> MarcaConsulta
teText -> TextConsulta
totalResultats -> TotalResultats
```

```xml
<!-- AgentZon/ontologia/AgentZonOntology.rdf -->
<!-- Remove the full AgentIntern branch and keep only external actors under Actor -->
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#Actor">
    <rdfs:comment xml:lang="ca">Entitat externa o humana que participa en el sistema.</rdfs:comment>
    <rdfs:label xml:lang="ca">Actor</rdfs:label>
</owl:Class>

<owl:Class rdf:about="http://www.semanticweb.org/agentzon#Usuari">
    <rdfs:subClassOf rdf:resource="http://www.semanticweb.org/agentzon#Actor"/>
</owl:Class>

<owl:Class rdf:about="http://www.semanticweb.org/agentzon#Transportista">
    <rdfs:subClassOf rdf:resource="http://www.semanticweb.org/agentzon#Actor"/>
</owl:Class>

<owl:Class rdf:about="http://www.semanticweb.org/agentzon#VenedorExtern">
    <rdfs:subClassOf rdf:resource="http://www.semanticweb.org/agentzon#Actor"/>
</owl:Class>

<owl:Class rdf:about="http://www.semanticweb.org/agentzon#Banc">
    <rdfs:subClassOf rdf:resource="http://www.semanticweb.org/agentzon#Actor"/>
</owl:Class>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest AgentZon/tests/test_acl_messages.py AgentZon/tests/test_ontology_alignment.py -q`
Expected: PASS with the new ACL ontology metadata and refined ontology invariants.

- [ ] **Step 5: Commit**

```bash
git add AgentZon/tests/test_acl_messages.py AgentZon/tests/test_ontology_alignment.py AgentZon/AgentUtil/OntoNamespaces.py AgentZon/AgentUtil/ACLMessages.py AgentZon/ontologia/AgentZonOntology.rdf
git commit -m "refactor: establish refined ontology vocabulary"
```

### Task 2: Search Protocol and Search-History Migration

**Files:**
- Modify: `AgentZon/protocols/cerca.py:9-75`
- Modify: `AgentZon/services/catalog_service.py:10-60`
- Modify: `AgentZon/services/history_service.py:10-21`
- Modify: `AgentZon/agents/agent_cercador.py:63-134`
- Modify: `AgentZon/tests/test_acl_messages.py:8-47`
- Modify: `AgentZon/tests/test_purchase_flow.py:131-171`

- [ ] **Step 1: Write the failing tests**

```python
# AgentZon/tests/test_acl_messages.py
from rdflib import Literal
from AgentZon.AgentUtil.OntoNamespaces import AZON

self.assertEqual(message_graph.value(content, AZON.TextConsulta), Literal("headphones"))
self.assertEqual(message_graph.value(content, AZON.CategoriaConsulta), Literal("audio"))
self.assertEqual(message_graph.value(content, AZON.MarcaConsulta), Literal("Acme"))
```

```python
# AgentZon/tests/test_purchase_flow.py
search_history_text = (data_dir / "historial_cerques.ttl").read_text(encoding="utf-8")
self.assertIn("TextConsulta", search_history_text)
self.assertIn("CategoriaConsulta", search_history_text)
self.assertIn("MarcaConsulta", search_history_text)
self.assertIn("MostraProducte", search_history_text)
self.assertNotIn("teText", search_history_text)
self.assertNotIn("teCategoria", search_history_text)
self.assertNotIn("teMarca", search_history_text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest AgentZon/tests/test_acl_messages.py AgentZon/tests/test_purchase_flow.py -q`
Expected: FAIL because `cerca.py`, `history_service.py`, and `catalog_service.py` still emit or query legacy terms such as `teText`, `teCategoria`, `teMarca`, and `mostraProducte`.

- [ ] **Step 3: Write the minimal implementation**

```python
# AgentZon/protocols/cerca.py
def build_peticio_cerca(request_id, text="", category="", brand="", min_price=None, max_price=None):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[request_id]
    graph.add((content, RDF.type, AZON.PeticioCerca))
    graph.add((content, AZON.TextConsulta, Literal(text)))
    graph.add((content, AZON.CategoriaConsulta, Literal(category)))
    graph.add((content, AZON.MarcaConsulta, Literal(brand)))
    if min_price is not None:
        graph.add((content, AZON.PreuMinim, Literal(min_price, datatype=XSD.float)))
    if max_price is not None:
        graph.add((content, AZON.PreuMaxim, Literal(max_price, datatype=XSD.float)))
    return graph, content


def parse_peticio_cerca(graph, content):
    return {
        "text": str(graph.value(content, AZON.TextConsulta, default=Literal(""))),
        "category": str(graph.value(content, AZON.CategoriaConsulta, default=Literal(""))),
        "brand": str(graph.value(content, AZON.MarcaConsulta, default=Literal(""))),
        "min_price": _literal_to_float(graph.value(content, AZON.PreuMinim)),
        "max_price": _literal_to_float(graph.value(content, AZON.PreuMaxim)),
    }


def build_resultat_cerca(result_id, products, request_content=None):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[result_id]
    graph.add((content, RDF.type, AZON.ResultatCerca))
    graph.add((content, AZON.TotalResultats, Literal(len(products))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    for product in products:
        subject = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.MostraProducte, subject))
        graph.add((subject, RDF.type, AZON.Producte))
        graph.add((subject, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((subject, AZON.Nom, Literal(product["name"])))
        graph.add((subject, AZON.Descripcio, Literal(product["description"])))
        graph.add((subject, AZON.Categoria, Literal(product["category"])))
        graph.add((subject, AZON.Marca, Literal(product["brand"])))
        graph.add((subject, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
        graph.add((subject, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    return graph, content
```

```python
# AgentZon/services/catalog_service.py
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
```

```python
# AgentZon/services/history_service.py
def record_search(path, criteria, products):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"search-{len(graph)}"]
    graph.add((record, RDF.type, AZON.HistorialCerca))
    graph.add((record, AZON.TextConsulta, Literal(criteria.get("text", ""))))
    graph.add((record, AZON.CategoriaConsulta, Literal(criteria.get("category", ""))))
    graph.add((record, AZON.MarcaConsulta, Literal(criteria.get("brand", ""))))
    if criteria.get("min_price") is not None:
        graph.add((record, AZON.PreuMinim, Literal(criteria["min_price"])))
    if criteria.get("max_price") is not None:
        graph.add((record, AZON.PreuMaxim, Literal(criteria["max_price"])))
    graph.add((record, AZON.TotalResultats, Literal(len(products))))
    for product in products:
        graph.add((record, AZON.MostraProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(path, graph)
```

```python
# AgentZon/agents/agent_cercador.py
from AgentZon.AgentUtil.OntoNamespaces import ONTOLOGY_URI

response_graph, response_content = build_resultat_cerca(
    f"result-{next_counter()}",
    products,
    request_content=content,
)
response = build_message(
    response_graph,
    ACL.inform,
    sender=AGENT.uri,
    receiver=properties.get("sender"),
    content=response_content,
    ontology=ONTOLOGY_URI,
    msgcnt=next_counter(),
)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest AgentZon/tests/test_acl_messages.py AgentZon/tests/test_purchase_flow.py -q`
Expected: PASS with refined search-property names in both the protocol RDF and persisted search history.

- [ ] **Step 5: Commit**

```bash
git add AgentZon/protocols/cerca.py AgentZon/services/catalog_service.py AgentZon/services/history_service.py AgentZon/agents/agent_cercador.py AgentZon/tests/test_acl_messages.py AgentZon/tests/test_purchase_flow.py
git commit -m "refactor: migrate search protocol vocabulary"
```

### Task 3: Order Persistence and Purchase-History Structure

**Files:**
- Create: `AgentZon/tests/test_order_graphs.py`
- Modify: `AgentZon/protocols/compra.py:11-58`
- Modify: `AgentZon/services/order_service.py:11-48`
- Modify: `AgentZon/services/history_service.py:25-34`
- Modify: `AgentZon/agents/agent_compra.py:76-126`
- Modify: `AgentZon/agents/agent_opinador.py:55-95`

- [ ] **Step 1: Write the failing tests**

```python
# AgentZon/tests/test_order_graphs.py
import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON
from AgentZon.services.history_service import record_purchase
from AgentZon.services.order_service import build_order, save_order, save_user_shipping_data
from AgentZon.services.rdf_store import load_graph


class OrderGraphTests(unittest.TestCase):
    def test_order_graph_links_shipping_and_products(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            orders_path = base / "comandes.ttl"
            shipping_path = base / "dades_enviament_usuari.ttl"

            shipping = {
                "user_id": "USER-1",
                "user_name": "Pol",
                "street_address": "Carrer Major 1",
                "city": "Barcelona",
                "priority": "standard",
                "payment_method": "visa",
            }
            products = [{"product_id": "P1001", "name": "Wireless Headphones", "weight": 1.5}]
            order = build_order(shipping, products)

            save_user_shipping_data(shipping_path, order)
            save_order(orders_path, order)

            graph = load_graph(orders_path)
            order_node = AZON[f"order-{order['order_id']}"]
            shipping_node = AZON[f"shipping-{order['order_id']}"]

            self.assertIn((order_node, RDF.type, AZON.Comanda), graph)
            self.assertIn((order_node, AZON.TeDadesEnviament, shipping_node), graph)
            self.assertIn((order_node, AZON.TeProducte, AZON["product-P1001"]), graph)

    def test_purchase_history_links_back_to_the_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "historial_compres.ttl"
            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "user_name": "Pol",
                "products": [{"product_id": "P1001"}],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "street_address": "Carrer Major 1",
                    "city": "Barcelona",
                    "priority": "standard",
                    "payment_method": "visa",
                },
            }

            record_purchase(history_path, order)
            graph = load_graph(history_path)
            history_node = AZON["purchase-ORDER-1"]

            self.assertIn((history_node, RDF.type, AZON.HistorialCompra), graph)
            self.assertIn((history_node, AZON.SobreComanda, AZON["order-ORDER-1"]), graph)
            self.assertIn((history_node, AZON.TeProducte, AZON["product-P1001"]), graph)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest AgentZon/tests/test_order_graphs.py -q`
Expected: FAIL because `order_service.py` has no `build_order` / `save_order` split, `TeDadesEnviament` is missing from `Comanda`, and `history_service.py` still writes only loose identifier literals.

- [ ] **Step 3: Write the minimal implementation**

```python
# AgentZon/services/order_service.py
def build_order(shipping_data, products):
    return {
        "order_id": f"ORDER-{uuid4().hex[:8].upper()}",
        "user_id": shipping_data["user_id"],
        "user_name": shipping_data["user_name"],
        "products": products,
        "shipping_data": shipping_data,
    }


def save_user_shipping_data(shipping_path, order):
    graph = load_graph(shipping_path)
    bind_namespaces(graph)
    shipping = order["shipping_data"]
    node = AZON[f"shipping-{order['order_id']}"]
    graph.add((node, RDF.type, AZON.DadesEnviamentUsuari))
    graph.add((node, AZON.IdUsuari, Literal(shipping["user_id"])))
    graph.add((node, AZON.Nom, Literal(shipping["user_name"])))
    graph.add((node, AZON.Carrer, Literal(shipping["street_address"])))
    graph.add((node, AZON.Ciutat, Literal(shipping["city"])))
    graph.add((node, AZON.Prioritat, Literal(shipping["priority"])))
    graph.add((node, AZON.MetodePagament, Literal(shipping["payment_method"])))
    save_graph(shipping_path, graph)


def save_order(orders_path, order):
    graph = load_graph(orders_path)
    bind_namespaces(graph)
    node = AZON[f"order-{order['order_id']}"]
    shipping_node = AZON[f"shipping-{order['order_id']}"]
    graph.add((node, RDF.type, AZON.Comanda))
    graph.add((node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((node, AZON.Nom, Literal(order["user_name"])))
    graph.add((node, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((node, AZON.Carrer, Literal(order["shipping_data"]["street_address"])))
    graph.add((node, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.add((node, AZON.TeDadesEnviament, shipping_node))
    for product in order["products"]:
        graph.add((node, AZON.TeProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(orders_path, graph)
```

```python
# AgentZon/protocols/compra.py
def build_peticio_registre_compra(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-request-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]

    graph.add((content, RDF.type, AZON.PeticioRegistreCompra))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((content, AZON.SobreComanda, order_node))

    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.IdUsuari, Literal(order["user_id"])))

    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.TeProducte, product_node))
        graph.add((order_node, AZON.TeProducte, product_node))

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_registre_compra(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.TeProducte):
        products.append({"product_id": str(graph.value(product_node, AZON.IdProducte))})

    return {
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "products": products,
    }


def build_confirmacio_registre_compra(order_id, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-confirmation-{order_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreCompra))
    graph.add((content, AZON.IdComanda, Literal(order_id)))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{order_id}"]))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )
```

```python
# AgentZon/services/history_service.py
def record_purchase(path, order):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"purchase-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]
    graph.add((record, RDF.type, AZON.HistorialCompra))
    graph.add((record, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((record, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((record, AZON.SobreComanda, order_node))
    for product in order["products"]:
        graph.add((record, AZON.TeProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(path, graph)
```

```python
# AgentZon/agents/agent_compra.py
from AgentZon.services.order_service import build_order, save_order, save_user_shipping_data

def pla_registrar_dades_d_usuari(selected_product_ids, form_data):
    shipping = {
        "user_id": form_data["user_id"],
        "user_name": form_data["user_name"],
        "street_address": form_data["street_address"],
        "city": form_data["city"],
        "priority": form_data["priority"],
        "payment_method": form_data["payment_method"],
    }
    products = get_products_by_ids(CATALOG_PATH, selected_product_ids)
    order = build_order(shipping, products)
    save_user_shipping_data(SHIPPING_PATH, order)
    save_order(ORDERS_PATH, order)
    return order
```

```python
# AgentZon/agents/agent_opinador.py
def pla_registre_de_compra(request_data):
    order = {
        "order_id": request_data["order_id"],
        "user_id": request_data["user_id"],
        "user_name": "history-user",
        "products": request_data["products"],
        "shipping_data": request_data.get("shipping_data", {}),
    }
    record_purchase(HISTORY_PATH, order)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest AgentZon/tests/test_order_graphs.py -q`
Expected: PASS with `Comanda -> TeDadesEnviament -> DadesEnviamentUsuari` and `HistorialCompra -> SobreComanda -> Comanda`.

- [ ] **Step 5: Commit**

```bash
git add AgentZon/tests/test_order_graphs.py AgentZon/protocols/compra.py AgentZon/services/order_service.py AgentZon/services/history_service.py AgentZon/agents/agent_compra.py AgentZon/agents/agent_opinador.py
git commit -m "refactor: model order and history relations"
```

### Task 4: Logistics RDF Structure and Transport Negotiation

**Files:**
- Modify: `AgentZon/protocols/centre_logistic.py:12-178`
- Modify: `AgentZon/services/logistics_service.py:13-50`
- Modify: `AgentZon/agents/agent_centre_logistic.py:62-125`
- Modify: `AgentZon/agents/agent_transportista.py:50-92`
- Modify: `AgentZon/tests/test_logistics_flow.py:10-189`

- [ ] **Step 1: Write the failing tests**

```python
# AgentZon/tests/test_logistics_flow.py
from AgentZon.AgentUtil.OntoNamespaces import AZON

self.assertEqual(float(graph.value(lot, AZON.PesTotal)), 3.5)
self.assertEqual(
    {str(value) for value in graph.objects(lot, AZON.TeProducte)},
    {str(AZON["product-P1"]), str(AZON["product-P2"])},
)
self.assertEqual(
    {str(value) for value in graph.objects(lot, AZON.SobreComanda)},
    {str(AZON["order-ORDER-1"]), str(AZON["order-ORDER-2"])},
)
```

```python
# AgentZon/tests/test_logistics_flow.py
parsed_graph = Graph()
parsed_graph.parse(data=graph, format="xml")
content = get_message_properties(parsed_graph)["content"]
self.assertIsNotNone(parsed_graph.value(content, AZON.SobreLot))
self.assertIsNotNone(parsed_graph.value(content, AZON.AssignatATransportista))
self.assertIsNotNone(parsed_graph.value(content, AZON.EsRespostaA))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest AgentZon/tests/test_logistics_flow.py -q`
Expected: FAIL because the current lot persistence still uses `Pes`, stores raw `idComanda` / `idProducte` literals, and the transport response content is not tied to `SobreLot` / `AssignatATransportista` / `EsRespostaA`.

- [ ] **Step 3: Write the minimal implementation**

```python
# AgentZon/services/logistics_service.py
def create_lot(lots_path, order_id, city, priority, products):
    graph = load_graph(lots_path)
    bind_namespaces(graph)
    node = None
    for lot in graph.subjects(RDF.type, AZON.Lot):
        lot_city = graph.value(lot, AZON.Ciutat)
        lot_priority = graph.value(lot, AZON.Prioritat)
        if str(lot_city) == city and str(lot_priority) == priority:
            node = lot
            break

    if node is None:
        lot_id = f"LOT-{uuid4().hex[:6].upper()}"
        node = AZON[f"lot-{lot_id}"]
        graph.add((node, RDF.type, AZON.Lot))
        graph.add((node, AZON.IdLot, Literal(lot_id)))
        graph.add((node, AZON.Ciutat, Literal(city)))
        graph.add((node, AZON.Prioritat, Literal(priority)))
        total_weight = 0.0
    else:
        lot_id = str(graph.value(node, AZON.IdLot))
        existing_weight = graph.value(node, AZON.PesTotal)
        total_weight = float(existing_weight) if existing_weight is not None else 0.0

    graph.add((node, AZON.SobreComanda, AZON[f"order-{order_id}"]))
    for product in products:
        total_weight += float(product["weight"])
        graph.add((node, AZON.TeProducte, AZON[f"product-{product['product_id']}"]))
    graph.set((node, AZON.PesTotal, Literal(total_weight)))
    save_graph(lots_path, graph)
    return {
        "lot_id": lot_id,
        "order_id": order_id,
        "city": city,
        "priority": priority,
        "total_weight": total_weight,
    }
```

```python
# AgentZon/protocols/centre_logistic.py
def build_productes_localitzats(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"localized-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]

    graph.add((content, RDF.type, AZON.ProducteLocalitzat))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((content, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((content, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.add((content, AZON.SobreComanda, order_node))

    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.TeProducte, product_node))
        graph.add((order_node, AZON.TeProducte, product_node))

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.Compra,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    ), content


def parse_productes_localitzats(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.TeProducte):
        products.append(
            {
                "product_id": str(graph.value(product_node, AZON.IdProducte)),
                "name": str(graph.value(product_node, AZON.Nom)),
                "weight": float(graph.value(product_node, AZON.Pes)),
            }
        )
    return {
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "priority": str(graph.value(content, AZON.Prioritat)),
        "products": products,
    }


def build_peticio_transport(lot, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-request-{lot['lot_id']}"]
    lot_node = AZON[f"lot-{lot['lot_id']}"]

    graph.add((content, RDF.type, AZON.PeticioTransport))
    graph.add((content, AZON.IdLot, Literal(lot["lot_id"])))
    graph.add((content, AZON.IdComanda, Literal(lot["order_id"])))
    graph.add((content, AZON.Ciutat, Literal(lot["city"])))
    graph.add((content, AZON.Prioritat, Literal(lot["priority"])))
    graph.add((content, AZON.PesTotal, Literal(lot["total_weight"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{lot['order_id']}"]))
```

```python
# AgentZon/protocols/centre_logistic.py
def build_resposta_oferta_transport(offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-offer-{offer['transport_id']}-{offer['lot_id']}"]
    lot_node = AZON[f"lot-{offer['lot_id']}"]
    transport_node = AZON[f"transport-{offer['transport_id']}"]

    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.IdLot, Literal(offer["lot_id"])))
    graph.add((content, AZON.IdComanda, Literal(offer["order_id"])))
    graph.add((content, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(offer["city"])))
    graph.add((content, AZON.DataEntrega, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{offer['order_id']}"]))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))


def parse_peticio_transport(graph, content):
    return {
        "lot_id": str(graph.value(content, AZON.IdLot)),
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "priority": str(graph.value(content, AZON.Prioritat)),
        "total_weight": float(graph.value(content, AZON.PesTotal)),
    }


def build_shipping_details_response(order_id, city, offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    return build_resposta_oferta_transport(
        {
            "lot_id": offer["lot_id"],
            "order_id": order_id,
            "transport_id": offer["transport_id"],
            "transport_name": offer["transport_name"],
            "city": city,
            "delivery_date": offer["delivery_date"],
            "price": offer["price"],
        },
        sender=sender,
        receiver=receiver,
        request_content=request_content,
        msgcnt=msgcnt,
    )
```

```python
# AgentZon/agents/agent_centre_logistic.py
request_data = parse_productes_localitzats(message_graph, content)
lot = pla_assignar_producte_a_lot(request_data)
offers = pla_cerca_de_transportista(lot)
response = pla_de_transportista_escollit(lot, offers, properties.get("sender"), content)
```

```python
# AgentZon/agents/agent_transportista.py
def generar_oferta_transport(request_data):
    return {
        "lot_id": request_data["lot_id"],
        "order_id": request_data["order_id"],
        "transport_id": TRANSPORT_ID,
        "transport_name": AGENT.name,
        "city": request_data["city"],
        "delivery_date": (date.today() + timedelta(days=DELIVERY_DAYS)).isoformat(),
        "price": round(request_data["total_weight"] * PRICE_PER_KG, 2),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest AgentZon/tests/test_logistics_flow.py -q`
Expected: PASS with `PesTotal`, `TeProducte`, `SobreComanda`, `SobreLot`, and `AssignatATransportista` represented explicitly in the lot and transport graphs.

- [ ] **Step 5: Commit**

```bash
git add AgentZon/protocols/centre_logistic.py AgentZon/services/logistics_service.py AgentZon/agents/agent_centre_logistic.py AgentZon/agents/agent_transportista.py AgentZon/tests/test_logistics_flow.py
git commit -m "refactor: model lot and transport relations"
```

### Task 5: Seed Data, Checked-In RDF, Agents, and Documentation Alignment

**Files:**
- Create: `AgentZon/tests/test_seed_graphs.py`
- Modify: `AgentZon/services/bootstrap.py:12-107`
- Modify: `AgentZon/agents/agent_compra.py:90-145`
- Modify: `AgentZon/data/productes.ttl`
- Modify: `AgentZon/data/comandes.ttl`
- Modify: `AgentZon/data/dades_enviament_usuari.ttl`
- Modify: `AgentZon/data/historial_compres.ttl`
- Modify: `AgentZon/data/historial_cerques.ttl`
- Modify: `AgentZon/data/lots.ttl`
- Modify: `AgentZon/data/ubicacions_productes.ttl`
- Modify: `AgentZon/docs/AgentZon/IMPLEMENTATION_AND_ONTOLOGY.md:9-58`
- Modify: `AgentZon/docs/AgentZon/Entrega-3.md:789-900`
- Modify: `AgentZon/tests/test_purchase_flow.py:80-171`

- [ ] **Step 1: Write the failing tests**

```python
# AgentZon/tests/test_seed_graphs.py
import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON
from AgentZon.services.bootstrap import bootstrap_phase2_data
from AgentZon.services.rdf_store import load_graph


class SeedGraphTests(unittest.TestCase):
    def test_bootstrap_uses_refined_vocabulary_and_explicit_location_relations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)

            locations = load_graph(data_dir / "ubicacions_productes.ttl")
            mapping = AZON["location-P1001"]

            self.assertIn((mapping, RDF.type, AZON.UbicacioProducte), locations)
            self.assertIn((mapping, AZON.SobreProducte, AZON["product-P1001"]), locations)
            self.assertIn((mapping, AZON.UbicatACentre, AZON["centre-BCN"]), locations)


if __name__ == "__main__":
    unittest.main()
```

```python
# AgentZon/tests/test_purchase_flow.py
history_text = (data_dir / "historial_compres.ttl").read_text(encoding="utf-8")
orders_text = (data_dir / "comandes.ttl").read_text(encoding="utf-8")
lots_text = (data_dir / "lots.ttl").read_text(encoding="utf-8")

self.assertIn("TeDadesEnviament", orders_text)
self.assertIn("SobreComanda", history_text)
self.assertIn("TeProducte", lots_text)
self.assertIn("PesTotal", lots_text)
self.assertNotIn("teProducte", orders_text)
self.assertNotIn("idComanda", history_text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest AgentZon/tests/test_seed_graphs.py AgentZon/tests/test_purchase_flow.py -q`
Expected: FAIL because the current seed graphs and checked-in data still use legacy names and `UbicacioProducte` still stores IDs instead of explicit `SobreProducte` / `UbicatACentre` relations.

- [ ] **Step 3: Write the minimal implementation**

```python
# AgentZon/services/bootstrap.py
def _build_products_graph():
    graph = Graph()
    bind_namespaces(graph)
    for item in products:
        subject = AZON[f"product-{item['id']}"]
        graph.add((subject, RDF.type, AZON.Producte))
        graph.add((subject, AZON.IdProducte, Literal(item["id"])))
        graph.add((subject, AZON.Nom, Literal(item["name"])))
        graph.add((subject, AZON.Descripcio, Literal(item["description"])))
        graph.add((subject, AZON.Categoria, Literal(item["category"])))
        graph.add((subject, AZON.Marca, Literal(item["brand"])))
        graph.add((subject, AZON.Preu, Literal(item["price"], datatype=XSD.float)))
        graph.add((subject, AZON.Pes, Literal(item["weight"], datatype=XSD.float)))
    return graph


def _build_locations_graph():
    graph = Graph()
    bind_namespaces(graph)
    centre = AZON["centre-BCN"]
    graph.add((centre, RDF.type, AZON.CentreLogistic))
    graph.add((centre, AZON.IdCentreLogistic, Literal("CL-BCN")))
    graph.add((centre, AZON.Ciutat, Literal("Barcelona")))

    for product_id in ["P1001", "P1002", "P2001", "P3001"]:
        product = AZON[f"product-{product_id}"]
        mapping = AZON[f"location-{product_id}"]
        graph.add((mapping, RDF.type, AZON.UbicacioProducte))
        graph.add((mapping, AZON.SobreProducte, product))
        graph.add((mapping, AZON.UbicatACentre, centre))
    return graph
```

```python
# AgentZon/agents/agent_compra.py
def pla_producte_als_nostres_magatzems(order):
    centre_agent = resolve_agent(DSO.CentreLogisticAgent)
    message, _ = build_productes_localitzats(
        order,
        sender=AGENT.uri,
        receiver=centre_agent.uri,
        msgcnt=next_counter(),
    )
    return extract_shipping_details(MESSAGE_SENDER(message, centre_agent.address))
```

```text
# Regenerate the checked-in Turtle fixtures after bootstrap and service changes
python - <<'PY'
from pathlib import Path
from AgentZon.services.bootstrap import bootstrap_phase2_data

bootstrap_phase2_data(Path("AgentZon/data"))
PY
```

```markdown
# AgentZon/docs/AgentZon/IMPLEMENTATION_AND_ONTOLOGY.md
- `Actor`
- `Usuari`, `VenedorExtern`, `Transportista`, `Banc`
- `Comunicacio`
- `Accio` and `Resposta`

- `acl:sender` and `acl:receiver` belong to the FIPA-ACL envelope and are not AgentZon ontology relations.
- `TeProducte`, `TeDadesEnviament`, `SobreComanda`, `SobreLot`, and `UbicatACentre` are the canonical runtime relations.
- `PesTotal` belongs to `Lot` and `PeticioTransport`; `Pes` stays on `Producte`.
```

```markdown
# AgentZon/docs/AgentZon/Entrega-3.md
Replace the ontology-description section so the runtime concepts match the refined model:

- `Actor` keeps only external actors.
- `Comanda` has attributes `IdComanda`, `IdUsuari`, `Nom`, `Carrer`, `Ciutat`, `Prioritat` and relations `TeProducte`, `TeDadesEnviament`.
- `Lot` has attributes `IdLot`, `Ciutat`, `Prioritat`, `PesTotal` and relations `TeProducte`, `SobreComanda`, `AssignatATransportista`.
- `PeticioCerca` uses `TextConsulta`, `CategoriaConsulta`, `MarcaConsulta`, `PreuMinim`, `PreuMaxim`.
- `ResultatCerca` uses `MostraProducte`, `TotalResultats`, `EsRespostaA`.
- `PeticioTransport` / `RespostaOfertaTransport` use `SobreLot`, `SobreComanda`, `PesTotal`, `AssignatATransportista`.
```

- [ ] **Step 4: Run the tests and verification sweep**

Run: `pytest AgentZon/tests/test_acl_messages.py AgentZon/tests/test_ontology_alignment.py AgentZon/tests/test_order_graphs.py AgentZon/tests/test_seed_graphs.py AgentZon/tests/test_logistics_flow.py AgentZon/tests/test_purchase_flow.py -q`
Expected: PASS with the full refined RDF model across envelope, protocols, persistence, logistics, seed data, and browser-style flows.

Run: `rg -n "AgentIntern|emissor|receptor|teProducte|teText|teCategoria|teMarca|idComanda|idProducte|costTransport|nomTransportista" AgentZon`
Expected: only the design/spec/plan documents may mention the legacy strings; no runtime code, ontology file, or Turtle data file should contain them.

- [ ] **Step 5: Commit**

```bash
git add AgentZon/tests/test_seed_graphs.py AgentZon/services/bootstrap.py AgentZon/agents/agent_compra.py AgentZon/data/productes.ttl AgentZon/data/comandes.ttl AgentZon/data/dades_enviament_usuari.ttl AgentZon/data/historial_compres.ttl AgentZon/data/historial_cerques.ttl AgentZon/data/lots.ttl AgentZon/data/ubicacions_productes.ttl AgentZon/docs/AgentZon/IMPLEMENTATION_AND_ONTOLOGY.md AgentZon/docs/AgentZon/Entrega-3.md AgentZon/tests/test_purchase_flow.py
git commit -m "docs: align data and docs with refined ontology"
```

## Self-Review

- Spec coverage:
  - Naming migration is covered in Task 1.
  - FIPA-ACL boundary and `acl:ontology` are covered in Task 1 and Task 2.
  - Search protocol and history are covered in Task 2.
  - `Comanda`, `DadesEnviamentUsuari`, and purchase history are covered in Task 3.
  - `Lot`, `PeticioTransport`, `RespostaOfertaTransport`, and explicit transport-agent negotiation are covered in Task 4.
  - Seed data, checked-in RDF files, and docs are covered in Task 5.
- Placeholder scan:
  - No deferred implementation markers remain.
  - All commands, files, and code snippets are concrete.
- Type consistency:
  - Runtime names are consistent around `TeProducte`, `TeDadesEnviament`, `SobreComanda`, `SobreLot`, `MostraProducte`, `TextConsulta`, and `PesTotal`.
  - `Pes` remains product-level only; `PesTotal` is the lot/transport aggregate.
