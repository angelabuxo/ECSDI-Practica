# Data Ownership Protocol Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce single-agent ownership of every project `.ttl` database and replace every cross-agent file read/write with FIPA-ACL protocols, while preserving the current purchase, logistics, vendor, recommendation, refund, and payment flows.

**Architecture:** Keep the existing three-layer split intact. Owner agents keep their local persistence and expose any needed data through RDF/FIPA-ACL request/inform protocols in their existing `protocols/*.py` modules and `/comm` dispatchers. Non-owner agents stop configuring foreign paths and instead consume snapshots received in messages or ask the owner agent explicitly.

**Tech Stack:** Python 3, Flask, rdflib, local Turtle persistence, SPARQL on local graphs, FIPA-ACL over HTTP GET, unittest

---

## File Structure

- `ontologia/AgentZonOntology.rdf`
  Purpose: declare the new ACL content classes and any extra property domains/ranges needed by owner-query protocols.

- `protocols/cerca.py`
  Purpose: keep product-search messages and add owner-facing product lookup messages for `Cercador`.

- `protocols/compra.py`
  Purpose: keep purchase/history messages and add the vendor-to-`Compra` registration message for shipping responsibility/location ownership.

- `protocols/opinador.py`
  Purpose: keep order/feedback/return messages and add search-registration plus user-purchase query messages for `Cercador` and `Retornador`.

- `protocols/pagament.py`
  Purpose: keep bank/payment/refund messages, add seller-profile query messages, and carry full product invoice lines in internal charges.

- `agents/agent_cercador.py:55-244`
  Purpose: remain sole owner of `productes.ttl`; answer catalog lookup requests and delegate search-history persistence to `Opinador`.

- `agents/agent_compra.py:95-357`
  Purpose: remain sole owner of `dades_enviament_usuari.ttl`, `responsable_enviament_productes.ttl`, `ubicacions_productes.ttl`, and `seguiment_enviaments.ttl`; stop reading the catalog and bank-data stores directly.

- `agents/agent_opinador.py:81-360`
  Purpose: remain sole owner of `historial_cerques.ttl`, `historial_compres.ttl`, and `feedback.ttl`; stop reading `productes.ttl` directly.

- `agents/agent_retornador.py:66-316`
  Purpose: remain sole owner of `devolucions.ttl`; fetch purchases from `Opinador` and compute refund batches from snapshots instead of foreign files.

- `agents/agent_venedor_extern.py:60-320`
  Purpose: own no `.ttl`; delegate product registration side effects to `Cercador`, `Compra`, and `Cobrador`.

- `agents/agent_cobrador.py:65-238`
  Purpose: remain sole owner of `dades_bancaries_usuari.ttl`, `dades_bancaries_venedors_externs.ttl`, and `pagaments.ttl`; stop reading `productes.ttl`.

- `agents/agent_centre_logistic.py:357-474`
  Purpose: keep owning `lots-*.ttl` only, but include full invoice/product-line data when asking `Cobrador` for internal charges.

- `services/order_service.py:12-127`
  Purpose: persist and load rich order/product snapshots instead of only `product_id` links.

- `services/history_service.py:12-110`
  Purpose: preserve search-history and purchase-history richness inside `Opinador`.

- `services/catalog_service.py:18-122`
  Purpose: keep product queries/addition and support product lookups owned by `Cercador`.

- `services/opinador_service.py:23-360`
  Purpose: generate recommendations from `Opinador`-owned search/purchase history plus catalog snapshots fetched through `Cercador`, and evaluate returns/pending feedback from purchase snapshots only.

- `services/retornador_service.py:50-263`
  Purpose: turn return UI and refund batching into pure functions over snapshots returned by `Opinador`.

- `services/logistics_service.py:96-143,404-418`
  Purpose: preserve product price/name in lot items so `Cobrador` can charge without consulting `productes.ttl`.

- `tests/test_agent_data_ownership.py`
  Purpose: regression guard that each agent only configures owned paths and owner-query protocols roundtrip.

- `tests/test_cercador_flow.py`
  Purpose: product lookup and search-history delegation tests for the `Cercador`.

- `tests/test_purchase_flow.py`
  Purpose: verify `Compra` fetches catalog snapshots through `Cercador` and no longer depends on direct catalog access.

- `tests/test_opinador_flow.py`
  Purpose: verify `Opinador` stores rich search/purchase snapshots, generates recommendations without direct catalog reads, and resolves returns without foreign DB access.

- `tests/test_return_policy.py`
  Purpose: verify `Retornador` and `Opinador` can evaluate and batch returns from stored snapshots only.

- `tests/test_venedor_extern_flow.py`
  Purpose: verify `VenedorExtern` no longer writes owner files directly and instead talks to `Compra`/`Cobrador`.

- `tests/test_cobrador_flow.py`
  Purpose: verify internal charges work without direct catalog reads.

- `tests/test_logistics_flow.py`
  Purpose: verify the internal-charge message now carries price lines from `Centre Logístic` to `Cobrador`.

- `docs/AgentZon/Diagrames-Entrega-2.pd`
  Purpose: update Prometheus message arrows and plan dependencies to match the new owner-query protocols.

- `docs/Justificacions/JUSTIFICACIO_EINES.md`
  Purpose: document why the new protocols are still compliant with Flask/requests/rdflib/FIPA-ACL patterns from the lab.

- `docs/Justificacions/GUIA_NOU_INTEGRANT.md`
  Purpose: explain the new owner boundaries and the resulting inter-agent flows to future maintainers.

### Task 1: Ownership Contracts and Protocol Scaffolding

**Files:**
- Modify: `ontologia/AgentZonOntology.rdf`
- Modify: `protocols/cerca.py`
- Modify: `protocols/compra.py`
- Modify: `protocols/opinador.py`
- Modify: `protocols/pagament.py`
- Create: `tests/test_agent_data_ownership.py`

- [ ] **Step 1: Write the failing ownership and protocol tests**

```python
import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AGN, AZON


class AgentDataOwnershipTests(unittest.TestCase):
    def test_runtime_only_assigns_owned_paths(self):
        from agents import (
            agent_cercador,
            agent_compra,
            agent_cobrador,
            agent_opinador,
            agent_retornador,
            agent_venedor_extern,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            directory_agent = Agent("DirectoryAgent", AGN.Directory, "http://directory.test/Register", "http://directory.test/Stop")

            agent_compra.configure_runtime({"agent": Agent("CompraAgent", AGN.Compra, "http://compra.test/comm", "http://compra.test/Stop"), "directory_agent": directory_agent, "data_dir": data_dir})
            self.assertIsNone(getattr(agent_compra, "CATALOG_PATH", None))
            self.assertIsNone(getattr(agent_compra, "USER_BANK_PATH", None))
            self.assertEqual(agent_compra.SHIPPING_PATH.name, "dades_enviament_usuari.ttl")
            self.assertEqual(agent_compra.LOCATIONS_PATH.name, "ubicacions_productes.ttl")
            self.assertEqual(agent_compra.SHIPPING_RESPONSIBILITY_PATH.name, "responsable_enviament_productes.ttl")

            agent_opinador.configure_runtime({"agent": Agent("OpinadorAgent", AGN.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop"), "directory_agent": directory_agent, "data_dir": data_dir, "proactive_enabled": False})
            self.assertIsNone(getattr(agent_opinador, "CATALOG_PATH", None))
            self.assertEqual(agent_opinador.SEARCH_HISTORY_PATH.name, "historial_cerques.ttl")
            self.assertEqual(agent_opinador.PURCHASE_HISTORY_PATH.name, "historial_compres.ttl")
            self.assertEqual(agent_opinador.FEEDBACK_PATH.name, "feedback.ttl")

            agent_retornador.configure_runtime({"agent": Agent("RetornadorAgent", AGN.Retornador, "http://retornador.test/comm", "http://retornador.test/Stop"), "directory_agent": directory_agent, "data_dir": data_dir})
            self.assertIsNone(getattr(agent_retornador, "PURCHASE_HISTORY_PATH", None))
            self.assertIsNone(getattr(agent_retornador, "CATALOG_PATH", None))
            self.assertIsNone(getattr(agent_retornador, "SHIPPING_RESPONSIBILITY_PATH", None))
            self.assertEqual(agent_retornador.REFUNDS_PATH.name, "devolucions.ttl")

            agent_venedor_extern.configure_runtime({"agent": Agent("VenedorExternAgent", AGN.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop"), "directory_agent": directory_agent, "data_dir": data_dir})
            self.assertIsNone(getattr(agent_venedor_extern, "SHIPPING_RESPONSIBILITY_PATH", None))
            self.assertIsNone(getattr(agent_venedor_extern, "LOCATIONS_PATH", None))
            self.assertIsNone(getattr(agent_venedor_extern, "SELLER_BANK_PATH", None))

            agent_cobrador.configure_runtime({"agent": Agent("CobradorAgent", AGN.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop"), "directory_agent": directory_agent, "data_dir": data_dir})
            self.assertIsNone(getattr(agent_cobrador, "CATALOG_PATH", None))

            agent_cercador.configure_runtime({"agent": Agent("CercadorAgent", AGN.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop"), "directory_agent": directory_agent, "data_dir": data_dir})
            self.assertEqual(agent_cercador.CATALOG_PATH.name, "productes.ttl")
            self.assertIsNone(getattr(agent_cercador, "SEARCH_HISTORY_PATH", None))

    def test_owner_query_protocols_roundtrip(self):
        from protocols.cerca import (
            build_peticio_consulta_productes,
            extract_product_snapshots,
            parse_peticio_consulta_productes,
        )
        from protocols.compra import (
            build_confirmacio_registre_producte_extern_compra,
            build_peticio_registre_producte_extern_compra,
            parse_confirmacio_registre_producte_extern_compra,
            parse_peticio_registre_producte_extern_compra,
        )
        from protocols.opinador import (
            build_confirmacio_registre_cerca,
            build_peticio_registre_cerca,
            build_peticio_consulta_compres_usuari,
            build_resultat_consulta_compres_usuari,
            parse_confirmacio_registre_cerca,
            parse_peticio_registre_cerca,
            parse_peticio_consulta_compres_usuari,
            parse_resultat_consulta_compres_usuari,
        )
        from protocols.pagament import (
            build_peticio_consulta_dades_venedor,
            build_resultat_consulta_dades_venedor,
            parse_peticio_consulta_dades_venedor,
            parse_resultat_consulta_dades_venedor,
        )

        lookup = build_peticio_consulta_productes(["P1001", "P1002"], msgcnt=1)
        lookup_content = lookup.value(predicate=RDF.type, object=AZON.PeticioConsultaProductes)
        self.assertEqual(parse_peticio_consulta_productes(lookup, lookup_content), ["P1001", "P1002"])

        search_registration = build_peticio_registre_cerca(
            {
                "user_id": "USER-1",
                "criteria": {"text": "", "category": "periferics", "brand": "KeyCo", "min_price": None, "max_price": None},
                "products": [{"product_id": "P1001", "name": "Teclat", "category": "periferics", "brand": "KeyCo", "price": 50.0, "weight": 0.8}],
            },
            msgcnt=2,
        )
        parsed_search_registration = parse_peticio_registre_cerca(search_registration)
        self.assertEqual(parsed_search_registration["user_id"], "USER-1")
        self.assertEqual(parsed_search_registration["products"][0]["product_id"], "P1001")
        search_confirmation = build_confirmacio_registre_cerca("USER-1", msgcnt=3)
        self.assertEqual(parse_confirmacio_registre_cerca(search_confirmation)["user_id"], "USER-1")

        register = build_peticio_registre_producte_extern_compra(
            {"product_id": "P1030", "seller_id": "SELLER-1", "requires_external_logistics": True, "centre_id": "CL-BCN"},
            msgcnt=4,
        )
        self.assertEqual(parse_peticio_registre_producte_extern_compra(register)["product_id"], "P1030")
        confirmation = build_confirmacio_registre_producte_extern_compra("P1030", msgcnt=5)
        self.assertEqual(parse_confirmacio_registre_producte_extern_compra(confirmation)["product_id"], "P1030")

        purchases = build_resultat_consulta_compres_usuari(
            "USER-1",
            [{"order_id": "ORDER-1", "products": [{"product_id": "P1001", "name": "Teclat", "price": 50.0, "seller_id": "", "requires_external_logistics": False}], "shipping_data": {"city": "Barcelona"}}],
            msgcnt=6,
        )
        self.assertEqual(parse_resultat_consulta_compres_usuari(purchases)[0]["order_id"], "ORDER-1")
        self.assertEqual(parse_peticio_consulta_compres_usuari(build_peticio_consulta_compres_usuari("USER-1", msgcnt=7)), "USER-1")

        profile_request = build_peticio_consulta_dades_venedor("SELLER-1", msgcnt=8)
        self.assertEqual(parse_peticio_consulta_dades_venedor(profile_request), "SELLER-1")
        profile_reply = build_resultat_consulta_dades_venedor({"seller_id": "SELLER-1", "bank_data": "ES12 2100 1234 5678 9012", "seller_name": "Vendor"}, msgcnt=9)
        self.assertEqual(parse_resultat_consulta_dades_venedor(profile_reply)["seller_name"], "Vendor")
```

- [ ] **Step 2: Run the targeted ownership test and verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_agent_data_ownership -v
```

Expected: FAIL with `ImportError` / `AttributeError` for the new protocol builders/parsers and ownership globals that still point to foreign databases.

- [ ] **Step 3: Add the ontology classes and builder/parser scaffolding**

```python
# protocols/cerca.py
def build_peticio_consulta_productes(product_ids, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"product-lookup-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaProductes))
    for product_id in sorted(set(product_ids)):
        product_node = AZON[f"product-{product_id}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_peticio_consulta_productes(graph, content):
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_ids.append(str(graph.value(product_node, AZON.IdProducte)))
    return sorted(product_ids)


def build_resultat_consulta_productes(products, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"product-lookup-result-{msgcnt}"]
    graph.add((content, RDF.type, AZON.ResultatConsultaProductes))
    for product in products:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((product_node, AZON.Nom, Literal(product.get("name", ""))))
        graph.add((product_node, AZON.Categoria, Literal(product.get("category", ""))))
        graph.add((product_node, AZON.Marca, Literal(product.get("brand", ""))))
        graph.add((product_node, AZON.Preu, Literal(product.get("price", 0.0), datatype=XSD.float)))
        graph.add((product_node, AZON.Pes, Literal(product.get("weight", 0.0), datatype=XSD.float)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(graph, ACL.inform, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def extract_product_snapshots(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return [
        {
            "product_id": str(graph.value(product_node, AZON.IdProducte)),
            "name": str(graph.value(product_node, AZON.Nom) or ""),
            "category": str(graph.value(product_node, AZON.Categoria) or ""),
            "brand": str(graph.value(product_node, AZON.Marca) or ""),
            "price": float(graph.value(product_node, AZON.Preu) or 0.0),
            "weight": float(graph.value(product_node, AZON.Pes) or 0.0),
        }
        for product_node in graph.objects(content, AZON.SobreProducte)
    ]


# protocols/compra.py
def build_peticio_registre_producte_extern_compra(payload, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-product-compra-{payload['product_id']}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreProducteExternCompra))
    graph.add((content, AZON.IdProducte, Literal(payload["product_id"])))
    graph.add((content, AZON.IdVenedorExtern, Literal(payload["seller_id"])))
    graph.add((content, AZON.RequereixLogisticaExterna, Literal(bool(payload["requires_external_logistics"]), datatype=XSD.boolean)))
    if payload.get("centre_id"):
        graph.add((content, AZON.IdCentreLogistic, Literal(payload["centre_id"])))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_peticio_registre_producte_extern_compra(graph, content=None):
    if content is None:
        props = get_message_properties(graph)
        content = props["content"]
    return {
        "product_id": str(graph.value(content, AZON.IdProducte)),
        "seller_id": str(graph.value(content, AZON.IdVenedorExtern)),
        "requires_external_logistics": bool((graph.value(content, AZON.RequereixLogisticaExterna) or Literal(False)).toPython()),
        "centre_id": str(graph.value(content, AZON.IdCentreLogistic) or ""),
    }


def build_confirmacio_registre_producte_extern_compra(product_id, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-product-compra-confirmation-{product_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreProducteExternCompra))
    graph.add((content, AZON.IdProducte, Literal(product_id)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(graph, ACL.inform, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_confirmacio_registre_producte_extern_compra(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {"product_id": str(graph.value(content, AZON.IdProducte))}


# protocols/opinador.py
def build_peticio_registre_cerca(search_record, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"search-history-{search_record['user_id']}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreCerca))
    graph.add((content, AZON.IdUsuari, Literal(search_record["user_id"])))
    graph.add((content, AZON.TextConsulta, Literal(search_record["criteria"].get("text", ""))))
    graph.add((content, AZON.CategoriaConsulta, Literal(search_record["criteria"].get("category", ""))))
    graph.add((content, AZON.MarcaConsulta, Literal(search_record["criteria"].get("brand", ""))))
    if search_record["criteria"].get("min_price") is not None:
        graph.add((content, AZON.PreuMinim, Literal(search_record["criteria"]["min_price"], datatype=XSD.float)))
    if search_record["criteria"].get("max_price") is not None:
        graph.add((content, AZON.PreuMaxim, Literal(search_record["criteria"]["max_price"], datatype=XSD.float)))
    for product in search_record.get("products", []):
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.MostraProducte, product_node))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((product_node, AZON.Nom, Literal(product.get("name", ""))))
        graph.add((product_node, AZON.Categoria, Literal(product.get("category", ""))))
        graph.add((product_node, AZON.Marca, Literal(product.get("brand", ""))))
        graph.add((product_node, AZON.Preu, Literal(product.get("price", 0.0), datatype=XSD.float)))
        graph.add((product_node, AZON.Pes, Literal(product.get("weight", 0.0), datatype=XSD.float)))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_peticio_registre_cerca(graph):
    props = get_message_properties(graph)
    content = props["content"]
    products = []
    for product_node in graph.objects(content, AZON.MostraProducte):
        products.append(
            {
                "product_id": str(graph.value(product_node, AZON.IdProducte)),
                "name": str(graph.value(product_node, AZON.Nom) or ""),
                "category": str(graph.value(product_node, AZON.Categoria) or ""),
                "brand": str(graph.value(product_node, AZON.Marca) or ""),
                "price": float(graph.value(product_node, AZON.Preu) or 0.0),
                "weight": float(graph.value(product_node, AZON.Pes) or 0.0),
            }
        )
    return {
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "criteria": {
            "text": str(graph.value(content, AZON.TextConsulta) or ""),
            "category": str(graph.value(content, AZON.CategoriaConsulta) or ""),
            "brand": str(graph.value(content, AZON.MarcaConsulta) or ""),
            "min_price": float(graph.value(content, AZON.PreuMinim)) if graph.value(content, AZON.PreuMinim) is not None else None,
            "max_price": float(graph.value(content, AZON.PreuMaxim)) if graph.value(content, AZON.PreuMaxim) is not None else None,
        },
        "products": products,
    }


def build_confirmacio_registre_cerca(user_id, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"search-history-confirmation-{user_id}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreCerca))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(graph, ACL.inform, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_confirmacio_registre_cerca(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {"user_id": str(graph.value(content, AZON.IdUsuari))}


def build_peticio_consulta_compres_usuari(user_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"user-purchases-{user_id}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaCompresUsuari))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_peticio_consulta_compres_usuari(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return str(graph.value(content, AZON.IdUsuari))


def build_resultat_consulta_compres_usuari(user_id, purchases, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"user-purchases-result-{user_id}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.ResultatConsultaCompresUsuari))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    for purchase in purchases:
        order_node = AZON[f"order-{purchase['order_id']}"]
        graph.add((content, AZON.SobreComanda, order_node))
        graph.add((order_node, RDF.type, AZON.Comanda))
        graph.add((order_node, AZON.IdComanda, Literal(purchase["order_id"])))
        for product in purchase.get("products", []):
            product_node = AZON[f"product-{product['product_id']}"]
            graph.add((order_node, AZON.TeProducte, product_node))
            graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
            graph.add((product_node, AZON.Nom, Literal(product.get("name", ""))))
            graph.add((product_node, AZON.Marca, Literal(product.get("brand", ""))))
            graph.add((product_node, AZON.Preu, Literal(product.get("price", 0.0), datatype=XSD.float)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(graph, ACL.inform, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_resultat_consulta_compres_usuari(graph):
    props = get_message_properties(graph)
    content = props["content"]
    purchases = []
    for order_node in graph.objects(content, AZON.SobreComanda):
        products = []
        for product_node in graph.objects(order_node, AZON.TeProducte):
            products.append(
                {
                    "product_id": str(graph.value(product_node, AZON.IdProducte)),
                    "name": str(graph.value(product_node, AZON.Nom) or ""),
                    "brand": str(graph.value(product_node, AZON.Marca) or ""),
                    "price": float(graph.value(product_node, AZON.Preu) or 0.0),
                }
            )
        purchases.append({"order_id": str(graph.value(order_node, AZON.IdComanda)), "products": products})
    return purchases


# protocols/pagament.py
def build_peticio_consulta_dades_venedor(seller_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"seller-profile-request-{seller_id}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaDadesBancariesVenedor))
    graph.add((content, AZON.IdVenedorExtern, Literal(seller_id)))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_peticio_consulta_dades_venedor(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return str(graph.value(content, AZON.IdVenedorExtern))


def build_resultat_consulta_dades_venedor(profile, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"seller-profile-response-{profile['seller_id']}"]
    graph.add((content, RDF.type, AZON.ResultatConsultaDadesBancariesVenedor))
    graph.add((content, AZON.IdVenedorExtern, Literal(profile["seller_id"])))
    graph.add((content, AZON.DadesBancariesVenedorExtern, Literal(profile["bank_data"])))
    graph.add((content, AZON.Nom, Literal(profile.get("seller_name", ""))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(graph, ACL.inform, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


def parse_resultat_consulta_dades_venedor(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "seller_id": str(graph.value(content, AZON.IdVenedorExtern)),
        "bank_data": str(graph.value(content, AZON.DadesBancariesVenedorExtern) or ""),
        "seller_name": str(graph.value(content, AZON.Nom) or ""),
    }
```

```xml
<!-- ontologia/AgentZonOntology.rdf -->
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#PeticioConsultaProductes"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#ResultatConsultaProductes"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#PeticioRegistreCerca"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#ConfirmacioRegistreCerca"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#PeticioConsultaCompresUsuari"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#ResultatConsultaCompresUsuari"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#PeticioRegistreProducteExternCompra"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#ConfirmacioRegistreProducteExternCompra"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#PeticioConsultaDadesBancariesVenedor"/>
<owl:Class rdf:about="http://www.semanticweb.org/agentzon#ResultatConsultaDadesBancariesVenedor"/>
```

- [ ] **Step 4: Re-run the ownership test and verify it passes**

Run:

```bash
.venv/bin/python -m unittest tests.test_agent_data_ownership -v
```

Expected: PASS for both `test_runtime_only_assigns_owned_paths` and `test_owner_query_protocols_roundtrip`.

- [ ] **Step 5: Commit the protocol/ontology scaffolding**

```bash
git add ontologia/AgentZonOntology.rdf protocols/cerca.py protocols/compra.py protocols/opinador.py protocols/pagament.py tests/test_agent_data_ownership.py
git commit -m "test: scaffold ownership protocols and ontology"
```

### Task 2: Rich Order Snapshots and Remote Catalog Lookup in Compra

**Files:**
- Modify: `services/order_service.py:32-127`
- Modify: `services/history_service.py:61-90`
- Modify: `protocols/compra.py:11-340`
- Modify: `agents/agent_compra.py:95-357`
- Modify: `tests/test_purchase_flow.py`

- [ ] **Step 1: Write failing tests for remote product lookup and rich order persistence**

```python
def test_compra_fetches_selected_products_via_cercador_protocol(self):
    from AgentUtil.Agent import Agent
    from AgentUtil.DSO import DSO
    from agents import agent_cercador, agent_compra, agent_directory, agent_opinador
    from protocols.cerca import build_resultat_consulta_productes
    from protocols.directory import build_register_message
    from services.bootstrap import bootstrap_phase2_data

    agn = Namespace("http://www.agentes.org#")
    directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
    compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
    cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
    opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
    router = LocalMessageRouter()
    lookup_calls = []

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        bootstrap_phase2_data(data_dir, product_count=4, seed=21)
        sample_product = load_catalog_products(data_dir / "productes.ttl")[0]

        agent_directory.configure_runtime({"agent": directory})
        router.register_app(directory.address, agent_directory.app)
        agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir, "proactive_enabled": False})
        router.register_app(opinador.address, agent_opinador.app)

        def compra_sender(message, address):
            if address == cercador.address:
                lookup_calls.append(address)
            return router.send_message(message, address)

        agent_cercador.configure_runtime({"agent": cercador, "directory_agent": directory, "data_dir": data_dir})
        router.register_app(cercador.address, agent_cercador.app)
        agent_compra.configure_runtime({"agent": compra, "directory_agent": directory, "data_dir": data_dir}, message_sender=compra_sender)
        router.register_app(compra.address, agent_compra.app)

        for msgcnt, agent, agent_type in [(1, compra, DSO.CompraAgent), (2, cercador, DSO.CercadorAgent), (3, opinador, DSO.OpinadorAgent)]:
            router.send_message(build_register_message(agent, agent_type, directory, msgcnt=msgcnt), directory.address)

        response, order, _ = agent_compra.process_purchase_request(
            {
                "user_id": "USER-1",
                "payment_method": "visa",
                "shipping_data": {"user_name": "Pol", "street_address": "Gran Via 1", "city": "Barcelona", "priority": "48h"},
                "product_ids": [sample_product["product_id"]],
            },
            acl_sender=compra.uri,
        )

        self.assertEqual(lookup_calls, [cercador.address])
        self.assertEqual(order["products"][0]["name"], sample_product["name"])
        self.assertIn("price", order["products"][0])


def test_order_service_persists_full_product_snapshot(self):
    from services.order_service import load_order, save_order

    with tempfile.TemporaryDirectory() as tmpdir:
        orders_path = Path(tmpdir) / "historial_compres.ttl"
        save_order(
            orders_path,
            {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "user_name": "Pol",
                "products": [{"product_id": "P1001", "name": "Teclat", "category": "periferics", "brand": "KeyCo", "price": 50.0, "weight": 0.8, "seller_id": "SELLER-1", "requires_external_logistics": True}],
                "shipping_data": {"user_id": "USER-1", "user_name": "Pol", "street_address": "Gran Via 1", "city": "Barcelona", "priority": "48h", "payment_method": "visa"},
                "delivery_date": "2026-06-07",
            },
        )
        stored = load_order(orders_path, "ORDER-1")
        self.assertEqual(stored["products"][0]["name"], "Teclat")
        self.assertEqual(stored["products"][0]["seller_id"], "SELLER-1")
        self.assertTrue(stored["products"][0]["requires_external_logistics"])
```

- [ ] **Step 2: Run the focused purchase tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_purchase_flow -v
```

Expected: FAIL because `agent_compra` still imports `get_products_by_ids`, still reads `CATALOG_PATH`, and `save_order` / `load_order` do not persist rich product snapshots.

- [ ] **Step 3: Implement remote product lookup and rich order snapshots**

```python
# agents/agent_compra.py
from protocols.cerca import build_peticio_consulta_productes, extract_product_snapshots
from services.external_vendor_service import load_shipping_responsibility_by_product
from services.logistics_routing_service import load_product_location_candidates


def _fetch_products_from_cercador(product_ids):
    cercador_agent = resolve_agent(DSO.CercadorAgent)
    message = build_peticio_consulta_productes(
        product_ids,
        sender=AGENT.uri,
        receiver=cercador_agent.uri,
        msgcnt=_msgcnt(),
    )
    reply = MESSAGE_SENDER(message, cercador_agent.address)
    return extract_product_snapshots(reply)


def _enrich_products_with_compra_metadata(products):
    responsibility = load_shipping_responsibility_by_product(SHIPPING_RESPONSIBILITY_PATH)
    location_candidates = load_product_location_candidates(LOCATIONS_PATH, [product["product_id"] for product in products])
    enriched = []
    for product in products:
        metadata = responsibility.get(product["product_id"], {})
        candidate_centres = location_candidates.get(product["product_id"], [])
        enriched.append(
            {
                **product,
                "seller_id": metadata.get("seller_id", ""),
                "requires_external_logistics": metadata.get("requires_external_logistics", False),
                "centre_id": candidate_centres[0]["centre_id"] if candidate_centres else "",
            }
        )
    return enriched


def pla_registrar_dades_d_usuari_al_cobrador(order):
    shipping = order["shipping_data"]
    bank_data = f"card-****-{order['user_id']}"
    message = build_peticio_registre_dades_usuari(
        order["user_id"],
        bank_data,
        shipping["payment_method"],
        sender=AGENT.uri,
        receiver=resolve_agent(DSO.CobradorAgent).uri,
        msgcnt=_msgcnt(),
    )
    return extract_confirmacio_registre_dades(MESSAGE_SENDER(message, resolve_agent(DSO.CobradorAgent).address))
```

```python
# services/order_service.py
def save_order(orders_path, order):
    graph = load_graph(orders_path)
    bind_namespaces(graph)
    node = AZON[f"order-{order['order_id']}"]
    graph.add((node, RDF.type, AZON.Comanda))
    graph.set((node, AZON.IdComanda, Literal(order["order_id"])))
    graph.set((node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.set((node, AZON.Nom, Literal(order["user_name"])))
    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.set((product_node, AZON.IdProducte, Literal(product["product_id"])))
        graph.set((product_node, AZON.Nom, Literal(product.get("name", ""))))
        graph.set((product_node, AZON.Categoria, Literal(product.get("category", ""))))
        graph.set((product_node, AZON.Marca, Literal(product.get("brand", ""))))
        graph.set((product_node, AZON.Preu, Literal(float(product.get("price", 0.0)), datatype=XSD.float)))
        graph.set((product_node, AZON.Pes, Literal(float(product.get("weight", 0.0)), datatype=XSD.float)))
        if product.get("seller_id"):
            graph.set((product_node, AZON.IdVenedorExtern, Literal(product["seller_id"])))
        graph.set((product_node, AZON.RequereixLogisticaExterna, Literal(bool(product.get("requires_external_logistics", False)), datatype=XSD.boolean)))
        graph.add((node, AZON.TeProducte, product_node))
    save_graph(orders_path, graph)


def load_order_from_graph(graph, node):
    if (node, RDF.type, AZON.Comanda) not in graph:
        return None
    order_id = str(graph.value(node, AZON.IdComanda) or str(node).rsplit("order-", 1)[-1])
    products = []
    for product_node in graph.objects(node, AZON.TeProducte):
        products.append(
            {
                "product_id": str(graph.value(product_node, AZON.IdProducte)),
                "name": str(graph.value(product_node, AZON.Nom) or ""),
                "category": str(graph.value(product_node, AZON.Categoria) or ""),
                "brand": str(graph.value(product_node, AZON.Marca) or ""),
                "price": float(graph.value(product_node, AZON.Preu) or 0.0),
                "weight": float(graph.value(product_node, AZON.Pes) or 0.0),
                "seller_id": str(graph.value(product_node, AZON.IdVenedorExtern) or ""),
                "requires_external_logistics": bool((graph.value(product_node, AZON.RequereixLogisticaExterna) or Literal(False)).toPython()),
            }
        )
    return {
        "order_id": order_id,
        "user_id": str(graph.value(node, AZON.IdUsuari)),
        "user_name": str(graph.value(node, AZON.Nom)),
        "products": products,
        "product_ids": sorted(product["product_id"] for product in products),
        "delivery_date": str(graph.value(node, AZON.DataEntrega) or ""),
        "shipping_data": {
            "user_name": str(graph.value(node, AZON.Nom)),
            "street_address": str(graph.value(node, AZON.Carrer) or ""),
            "city": str(graph.value(node, AZON.Ciutat) or ""),
            "priority": str(graph.value(node, AZON.Prioritat) or ""),
            "payment_method": str(graph.value(node, AZON.MetodePagament) or ""),
            "user_id": str(graph.value(node, AZON.IdUsuari)),
        },
    }
```

- [ ] **Step 4: Re-run the focused purchase tests and verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_purchase_flow -v
```

Expected: PASS for the new product-lookup and snapshot-persistence tests, plus the existing purchase flow scenarios.

- [ ] **Step 5: Commit the Compra snapshot refactor**

```bash
git add agents/agent_compra.py protocols/compra.py services/history_service.py services/order_service.py tests/test_purchase_flow.py
git commit -m "refactor: make compra consume catalog via cercador"
```

### Task 3: Cercador Owner APIs for Product Lookup and Search-History Delegation

**Files:**
- Modify: `protocols/cerca.py:1-118`
- Modify: `protocols/opinador.py:1-220`
- Modify: `agents/agent_cercador.py:55-244`
- Create: `tests/test_cercador_flow.py`

- [ ] **Step 1: Write failing tests for the new Cercador owner APIs and search-history delegation**

```python
import tempfile
import unittest
from pathlib import Path

from AgentUtil.Agent import Agent
from rdflib import Graph, Namespace

from AgentUtil.OntoNamespaces import AGN
from protocols.cerca import (
    build_peticio_consulta_productes,
    extract_product_snapshots,
)
from protocols.opinador import build_confirmacio_registre_cerca, parse_peticio_registre_cerca
from services.bootstrap import bootstrap_phase2_data


class CercadorFlowTests(unittest.TestCase):
    def test_product_lookup_returns_only_requested_products(self):
        from agents import agent_cercador

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=6, seed=21)
            agent = Agent("CercadorAgent", AGN.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
            agent_cercador.configure_runtime({"agent": agent, "directory_agent": None, "data_dir": data_dir})
            client = agent_cercador.app.test_client()

            message = build_peticio_consulta_productes(["P1001", "P1003"], sender=AGN.Compra, receiver=agent.uri, msgcnt=1)
            response = client.get("/comm", query_string={"content": message.serialize(format="xml")})
            graph = Graph()
            graph.parse(data=response.get_data(as_text=True), format="xml")
            products = extract_product_snapshots(graph)

            self.assertEqual({product["product_id"] for product in products}, {"P1001", "P1003"})

    def test_search_history_registration_is_delegated_to_opinador(self):
        from agents import agent_cercador

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            agn = Namespace("http://www.agentes.org#")
            cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
            opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
            delegated = []

            agent_cercador.configure_runtime({"agent": cercador, "directory_agent": None, "data_dir": data_dir})

            def fake_sender(message, address):
                delegated.append(parse_peticio_registre_cerca(message))
                return build_confirmacio_registre_cerca(
                    "USER-1",
                    sender=opinador.uri,
                    receiver=cercador.uri,
                    msgcnt=2,
                )

            agent_cercador.MESSAGE_SENDER = fake_sender
            agent_cercador.resolve_opinador_agent = lambda: opinador

            agent_cercador.pla_registrar_cerca_a_opinador(
                {"text": "", "category": "periferics", "brand": "KeyCo", "min_price": None, "max_price": None},
                [{"product_id": "P1002", "name": "Ratoli", "category": "periferics", "brand": "KeyCo", "price": 20.0, "weight": 0.2}],
                user_id="USER-1",
            )

            self.assertEqual(delegated[0]["user_id"], "USER-1")
            self.assertEqual(delegated[0]["criteria"]["brand"], "KeyCo")
            self.assertEqual(delegated[0]["products"][0]["product_id"], "P1002")
```

- [ ] **Step 2: Run the Cercador-focused tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_cercador_flow -v
```

Expected: FAIL because `agent_cercador` has no handler for `PeticioConsultaProductes` and still persists search history locally instead of delegating it to `Opinador`.

- [ ] **Step 3: Implement the owner APIs in Cercador and move search persistence behind `Opinador`**

```python
# agents/agent_cercador.py
from protocols.cerca import (
    build_resultat_consulta_productes,
    build_peticio_cerca,
    parse_peticio_consulta_productes,
)
from protocols.opinador import build_peticio_registre_cerca, parse_confirmacio_registre_cerca
from services.catalog_service import get_products_by_ids


def resolve_opinador_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.OpinadorAgent)


def pla_registrar_cerca_a_opinador(criteria, products, user_id):
    if not user_id:
        return None
    opinador = resolve_opinador_agent()
    message = build_peticio_registre_cerca(
        {"user_id": user_id, "criteria": criteria, "products": products},
        sender=AGENT.uri,
        receiver=opinador.uri,
        msgcnt=_msgcnt(),
    )
    reply = MESSAGE_SENDER(message, opinador.address)
    return parse_confirmacio_registre_cerca(reply)


def pla_consulta_productes_acl(gm, content, sender):
    product_ids = parse_peticio_consulta_productes(gm, content)
    products = get_products_by_ids(CATALOG_PATH, product_ids)
    return build_resultat_consulta_productes(products, sender=AGENT.uri, receiver=sender, request_content=content, msgcnt=mss_cnt)


# in configure_runtime(...)
CATALOG_PATH = data_dir / "productes.ttl"


# in browser_iface() after products = pla_de_cerca(criteria)
pla_registrar_cerca_a_opinador(criteria, products, get_client_ip_from_request(request))


# in /comm dispatch
elif accion == AZON.PeticioConsultaProductes:
    gr = pla_consulta_productes_acl(gm, content, msgdic.get("sender"))
```

- [ ] **Step 4: Re-run the Cercador-focused tests and verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_cercador_flow -v
```

Expected: PASS for product lookup and delegated search-history registration.

- [ ] **Step 5: Commit the Cercador owner APIs**

```bash
git add agents/agent_cercador.py protocols/cerca.py protocols/opinador.py tests/test_cercador_flow.py
git commit -m "refactor: delegate search history from cercador to opinador"
```

### Task 4: Opinador Owns Search History and Builds Recommendations Without Direct Catalog Reads

**Files:**
- Modify: `services/opinador_service.py:23-360`
- Modify: `protocols/opinador.py:1-345`
- Modify: `agents/agent_opinador.py:81-360`
- Modify: `tests/test_opinador_flow.py`

- [ ] **Step 1: Write failing tests for search-history ownership and catalog-free recommendation logic**

```python
import tempfile
from pathlib import Path

from rdflib import RDF

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AGN


def test_search_history_registration_persists_in_opinador(self):
    from agents import agent_opinador
    from protocols.opinador import build_peticio_registre_cerca
    from services.history_service import load_search_records

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        agent = Agent("OpinadorAgent", AGN.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        agent_opinador.configure_runtime({"agent": agent, "directory_agent": None, "data_dir": data_dir, "proactive_enabled": False})
        client = agent_opinador.app.test_client()

        message = build_peticio_registre_cerca(
            {
                "user_id": "USER-1",
                "criteria": {"text": "", "category": "periferics", "brand": "KeyCo", "min_price": None, "max_price": None},
                "products": [{"product_id": "P1002", "name": "Ratoli", "category": "periferics", "brand": "KeyCo", "price": 20.0, "weight": 0.2}],
            },
            sender=AGN.Cercador,
            receiver=agent.uri,
            msgcnt=1,
        )
        client.get("/comm", query_string={"content": message.serialize(format="xml")})
        stored = load_search_records(data_dir / "historial_cerques.ttl", user_id="USER-1")
        self.assertEqual(stored[0]["criteria"]["brand"], "KeyCo")
        self.assertEqual(stored[0]["product_ids"], ["P1002"])


def test_opinador_recommendations_use_owned_histories_and_remote_catalog(self):
    from AgentUtil.ACL import ACL
    from AgentUtil.ACLMessages import build_message
    from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI
    from agents import agent_opinador
    from protocols.cerca import build_resultat_cerca
    from services.history_service import record_purchase, record_search

    cercador = Agent("CercadorAgent", AGN.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
    opinador = Agent("OpinadorAgent", AGN.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
    calls = []

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir, "feedback_min_seconds": 0, "proactive_enabled": False})

        record_search(
            data_dir / "historial_cerques.ttl",
            {"text": "", "category": "periferics", "brand": "KeyCo", "min_price": None, "max_price": None},
            [{"product_id": "P1002"}],
            user_id="USER-1",
        )
        record_purchase(
            data_dir / "historial_compres.ttl",
            {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "user_name": "User",
                "purchase_date": "2026-06-01",
                "delivery_date": "2026-06-03",
                "shipping_data": {"city": "Barcelona"},
                "products": [{"product_id": "P1001", "name": "Teclat", "category": "periferics", "brand": "KeyCo", "price": 50.0, "weight": 0.8}],
            },
        )

        def fake_sender(message, address):
            calls.append(address)
            request_content = message.value(predicate=RDF.type, object=AZON.PeticioCerca)
            payload, response_content = build_resultat_cerca(
                "catalog-result-1",
                [
                    {"product_id": "P1001", "name": "Teclat", "description": "", "category": "periferics", "brand": "KeyCo", "price": 50.0, "weight": 0.8},
                    {"product_id": "P1002", "name": "Ratoli", "description": "", "category": "periferics", "brand": "KeyCo", "price": 20.0, "weight": 0.2},
                ],
                request_content=request_content,
            )
            return build_message(
                payload,
                ACL.inform,
                sender=cercador.uri,
                receiver=opinador.uri,
                content=response_content,
                ontology=ONTOLOGY_URI,
                msgcnt=3,
            )

        agent_opinador.MESSAGE_SENDER = fake_sender
        agent_opinador.resolve_cercador_agent = lambda: cercador
        recommendations = agent_opinador.pla_de_creacio_de_suggeriments("USER-1", limit=5)
        self.assertEqual(calls, [cercador.address])
        self.assertEqual(recommendations[0]["product_id"], "P1002")


def test_return_resolution_roundtrip_keeps_accepted_product_details(self):
    from protocols.opinador import build_resolucio_devolucio, parse_resolucio_devolucio

    message = build_resolucio_devolucio(
        {
            "return_id": "RET-1",
            "order_id": "ORDER-1",
            "user_id": "USER-1",
            "amount": 50.0,
            "accepted": True,
            "reason": "OK",
            "product_ids": ["P1001"],
            "products": [{"product_id": "P1001", "name": "Teclat", "price": 50.0, "seller_id": "SELLER-1", "requires_external_logistics": True}],
        },
        msgcnt=1,
    )
    parsed = parse_resolucio_devolucio(message)
    self.assertEqual(parsed["products"][0]["price"], 50.0)
    self.assertEqual(parsed["products"][0]["seller_id"], "SELLER-1")
```

- [ ] **Step 2: Run the Opinador-focused tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_opinador_flow -v
```

Expected: FAIL because `agent_opinador` still lacks `SEARCH_HISTORY_PATH`, has no `/comm` handler for `PeticioRegistreCerca`, and `pla_de_creacio_de_suggeriments` still reads `CATALOG_PATH` directly.

- [ ] **Step 3: Implement `Opinador` as search-history owner with remote catalog fetches**

```python
# agents/agent_opinador.py
from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message
from AgentUtil.DSO import DSO
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI
from protocols.cerca import build_peticio_cerca, extract_result_products
from protocols.opinador import build_confirmacio_registre_cerca, parse_peticio_registre_cerca
from services.history_service import load_purchase_records, load_search_records, record_search
from services.opinador_service import generate_recommendations_from_records


# in configure_runtime(...)
SEARCH_HISTORY_PATH = data_dir / "historial_cerques.ttl"
PURCHASE_HISTORY_PATH = data_dir / "historial_compres.ttl"
FEEDBACK_PATH = data_dir / "feedback.ttl"


def resolve_cercador_agent():
    return resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CercadorAgent)


def pla_registre_cerca_acl(gm, content, sender):
    request_data = parse_peticio_registre_cerca(gm)
    record_search(
        SEARCH_HISTORY_PATH,
        request_data["criteria"],
        request_data["products"],
        user_id=request_data["user_id"],
    )
    return build_confirmacio_registre_cerca(
        request_data["user_id"],
        sender=AGENT.uri,
        receiver=sender,
        request_content=content,
        msgcnt=mss_cnt,
    )


def _fetch_catalog_products():
    cercador = resolve_cercador_agent()
    request_graph, request_content = build_peticio_cerca(f"opinador-catalog-{_msgcnt()}")
    message = build_message(
        request_graph,
        ACL.request,
        sender=AGENT.uri,
        receiver=cercador.uri,
        content=request_content,
        ontology=ONTOLOGY_URI,
        msgcnt=_msgcnt(),
    )
    reply = MESSAGE_SENDER(message, cercador.address)
    return extract_result_products(reply)


def pla_de_creacio_de_suggeriments(user_id=None, limit=5):
    recommendations = generate_recommendations_from_records(
        _fetch_catalog_products(),
        load_search_records(SEARCH_HISTORY_PATH, user_id=user_id),
        load_purchase_records(PURCHASE_HISTORY_PATH, user_id=user_id),
        user_id=user_id,
        limit=limit,
    )
    return recommendations[:limit]


# in /comm dispatch
if accion == AZON.PeticioRegistreCerca:
    gr = pla_registre_cerca_acl(gm, content, msgdic.get("sender"))
```

```python
# services/opinador_service.py
from collections import Counter


def generate_recommendations_from_records(catalog_products, search_records, purchase_records, user_id=None, limit=5):
    purchased_by_id = {}
    for record in purchase_records:
        for product in record.get("products", []):
            purchased_by_id[product["product_id"]] = product
    purchased_ids = set(purchased_by_id)
    category_counter = Counter(product.get("category", "") for product in purchased_by_id.values() if product.get("category"))
    brand_counter = Counter(product.get("brand", "") for product in purchased_by_id.values() if product.get("brand"))
    searched_categories = Counter(record["criteria"]["category"] for record in search_records if record["criteria"]["category"])
    searched_brands = Counter(record["criteria"]["brand"] for record in search_records if record["criteria"]["brand"])
    searched_products = Counter(product_id for record in search_records for product_id in record["product_ids"])
    ranked_products = []
    for product in catalog_products:
        if product["product_id"] in purchased_ids:
            continue
        score = (
            category_counter[product["category"]] * 3
            + brand_counter[product["brand"]] * 2
            + searched_categories[product["category"]]
            + searched_brands[product["brand"]]
            + searched_products[product["product_id"]]
        )
        if score == 0:
            continue
        ranked_products.append((score, product["price"], product["name"], product))
    ranked_products.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in ranked_products[:limit]]


def evaluate_return_request(purchase_history_path, request_data):
    purchase_record = matching_records[-1]
    products_by_id = {product["product_id"]: product for product in purchase_record.get("products", [])}
    accepted_product_ids = [
        product_id
        for product_id in requested_product_ids
        if product_id in products_by_id and _is_product_return_eligible(purchase_history_path, user_id, order_id, product_id, return_reason)
    ]
    amount = request_data.get("amount")
    if amount is None:
        amount = round(sum(products_by_id[product_id].get("price", 0.0) for product_id in accepted_product_ids), 2)
    accepted_products = [products_by_id[product_id] for product_id in accepted_product_ids]
    return _build_return_decision(
        {**request_data, "amount": amount, "product_ids": sorted(accepted_product_ids), "products": accepted_products},
        accepted=bool(accepted_product_ids),
        reason="La devolució compleix les condicions de la política de devolució." if accepted_product_ids else RETURN_REJECTION_MESSAGE,
        accepted_product_ids=sorted(accepted_product_ids),
        requested_product_ids=requested_product_ids,
    )


def get_purchases_pending_feedback(purchase_history_path, feedback_path, user_id, min_days=MIN_DAYS_BEFORE_FEEDBACK, min_seconds=None, reference_date=None, reference_time=None):
    product_by_id = {}
    purchases = load_purchase_records(purchase_history_path, user_id=user_id)
    for purchase in purchases:
        for product in purchase.get("products", []):
            product_by_id[product["product_id"]] = product
    eligible_products.append({**product_by_id[entry["product_id"]], **entry})
```

- [ ] **Step 4: Re-run the Opinador-focused tests and verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_opinador_flow -v
```

Expected: PASS for search-history registration, remote catalog recommendations, rich order query, feedback, and return-resolution tests.

- [ ] **Step 5: Commit the Opinador refactor**

```bash
git add agents/agent_opinador.py protocols/opinador.py services/opinador_service.py tests/test_opinador_flow.py
git commit -m "refactor: make opinador own user search history"
```

### Task 5: Retornador Queries Opinador and Batches Refunds From Snapshots

**Files:**
- Modify: `agents/agent_retornador.py:66-316`
- Modify: `services/retornador_service.py:50-263`
- Modify: `protocols/opinador.py:1-345`
- Modify: `tests/test_return_policy.py`

- [ ] **Step 1: Write failing tests for the new Retornador boundary**

```python
def test_retornador_fetches_user_purchases_via_opinador_protocol(self):
    from AgentUtil.Agent import Agent
    from agents import agent_retornador
    from protocols.opinador import build_resultat_consulta_compres_usuari

    agn = Namespace("http://www.agentes.org#")
    retornador = Agent("RetornadorAgent", agn.Retornador, "http://retornador.test/comm", "http://retornador.test/Stop")
    opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        agent_retornador.configure_runtime({"agent": retornador, "directory_agent": Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop"), "data_dir": data_dir})

        def fake_sender(message, address):
            self.assertEqual(address, opinador.address)
            return build_resultat_consulta_compres_usuari(
                "10.0.0.1",
                [{"order_id": "ORDER-1", "products": [{"product_id": "P1001", "name": "Teclat", "brand": "KeyCo", "price": 50.0, "seller_id": "SELLER-1", "requires_external_logistics": True}], "shipping_data": {"city": "Barcelona"}}],
                sender=opinador.uri,
                receiver=retornador.uri,
                msgcnt=1,
            )

        agent_retornador.MESSAGE_SENDER = fake_sender
        agent_retornador.resolve_opinador_agent = lambda: opinador
        purchased = agent_retornador._load_purchased_products_for_iface("10.0.0.1")
        self.assertEqual(purchased[0]["name"], "Teclat")
        self.assertEqual(purchased[0]["brand"], "KeyCo")


def test_build_refund_batches_uses_snapshot_metadata_without_foreign_paths(self):
    from services.retornador_service import build_refund_batches_from_products

    batches = build_refund_batches_from_products(
        [
            {"product_id": "P1001", "price": 50.0, "seller_id": "", "requires_external_logistics": False},
            {"product_id": "P1030", "price": 79.99, "seller_id": "SELLER-1", "requires_external_logistics": True},
        ]
    )
    self.assertEqual(len(batches), 2)
    self.assertEqual(batches[0]["amount"], 50.0)
    self.assertEqual(batches[1]["seller_id"], "SELLER-1")
```

- [ ] **Step 2: Run the return-policy tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_return_policy -v
```

Expected: FAIL because `Retornador` still depends on `PURCHASE_HISTORY_PATH`, `CATALOG_PATH`, and `SHIPPING_RESPONSIBILITY_PATH`.

- [ ] **Step 3: Implement the Retornador owner-query flow**

```python
# protocols/opinador.py
def build_peticio_consulta_compres_usuari(user_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"user-purchases-{user_id}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaCompresUsuari))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)


# services/retornador_service.py
def build_purchased_products_from_orders(purchases, logger=None):
    purchased_products = []
    for purchase in purchases:
        for product in purchase.get("products", []):
            purchased_products.append(
                {
                    "order_id": purchase["order_id"],
                    "product_id": product["product_id"],
                    "name": product.get("name", product["product_id"]),
                    "brand": product.get("brand", ""),
                }
            )
    return purchased_products


def build_refund_batches_from_products(products):
    internal = []
    external = {}
    for product in products:
        if product.get("seller_id") and product.get("requires_external_logistics"):
            external.setdefault(product["seller_id"], []).append(product)
        else:
            internal.append(product)
    batches = []
    if internal:
        batches.append(
            {
                "seller_id": None,
                "product_ids": sorted(product["product_id"] for product in internal),
                "amount": round(sum(product.get("price", 0.0) for product in internal), 2),
            }
        )
    for seller_id, seller_products in sorted(external.items()):
        batches.append(
            {
                "seller_id": seller_id,
                "product_ids": sorted(product["product_id"] for product in seller_products),
                "amount": round(sum(product.get("price", 0.0) for product in seller_products), 2),
            }
        )
    return batches
```

```python
# agents/agent_retornador.py
def _fetch_user_purchases_from_opinador(user_id):
    opinador = resolve_opinador_agent()
    message = build_peticio_consulta_compres_usuari(
        user_id,
        sender=AGENT.uri,
        receiver=opinador.uri,
        msgcnt=_msgcnt(),
    )
    reply = MESSAGE_SENDER(message, opinador.address)
    return parse_resultat_consulta_compres_usuari(reply)


def _load_purchased_products_for_iface(user_id):
    return build_purchased_products_from_orders(_fetch_user_purchases_from_opinador(user_id), logger=logger)
```

- [ ] **Step 4: Re-run the return-policy tests and verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_return_policy -v
```

Expected: PASS for UI selection grouping, aggregate decisions, and snapshot-driven refund batching.

- [ ] **Step 5: Commit the Retornador boundary refactor**

```bash
git add agents/agent_retornador.py protocols/opinador.py services/retornador_service.py tests/test_return_policy.py
git commit -m "refactor: make retornador consume opinion snapshots"
```

### Task 6: Venedor Extern Delegates to Compra and Cobrador

**Files:**
- Modify: `agents/agent_venedor_extern.py:60-320`
- Modify: `agents/agent_compra.py:95-357`
- Modify: `agents/agent_cobrador.py:114-238`
- Modify: `protocols/compra.py`
- Modify: `protocols/pagament.py`
- Modify: `tests/test_venedor_extern_flow.py`

- [ ] **Step 1: Write failing tests for vendor delegation**

```python
def test_vendor_registration_writes_shipping_metadata_via_compra(self):
    from AgentUtil.Agent import Agent
    from AgentUtil.DSO import DSO
    from agents import agent_cercador, agent_cobrador, agent_compra, agent_directory, agent_venedor_extern
    from protocols.compra import parse_peticio_registre_producte_extern_compra

    agn = Namespace("http://www.agentes.org#")
    directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
    compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
    cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
    cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")
    venedor = Agent("VenedorExternAgent", agn.VenedorExtern, "http://venedor.test/comm", "http://venedor.test/Stop")
    router = LocalMessageRouter()
    compra_messages = []

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        bootstrap_phase2_data(data_dir, product_count=10, seed=21)
        agent_directory.configure_runtime({"agent": directory})
        router.register_app(directory.address, agent_directory.app)
        agent_cercador.configure_runtime({"agent": cercador, "directory_agent": directory, "data_dir": data_dir})
        router.register_app(cercador.address, agent_cercador.app)
        agent_cobrador.configure_runtime({"agent": cobrador, "directory_agent": directory, "data_dir": data_dir})
        router.register_app(cobrador.address, agent_cobrador.app)
        agent_compra.configure_runtime({"agent": compra, "directory_agent": directory, "data_dir": data_dir})
        router.register_app(compra.address, agent_compra.app)
        def venedor_sender(message, address):
            if address == compra.address:
                compra_messages.append(parse_peticio_registre_producte_extern_compra(message))
            return router.send_message(message, address)
        agent_venedor_extern.configure_runtime({"agent": venedor, "directory_agent": directory, "data_dir": data_dir}, message_sender=venedor_sender)
        router.register_app(venedor.address, agent_venedor_extern.app)
        self.assertEqual(compra_messages[0]["product_id"], "P1030")
        self.assertTrue(compra_messages[0]["requires_external_logistics"])


def test_vendor_iface_reads_profile_via_cobrador_query(self):
    from protocols.pagament import build_resultat_consulta_dades_venedor
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        agent_venedor_extern.configure_runtime({"agent": venedor, "directory_agent": directory, "data_dir": data_dir})

        def fake_sender(message, address):
            return build_resultat_consulta_dades_venedor(
                {"seller_id": "10.0.0.1", "bank_data": "ES12 2100 1234 5678 9012", "seller_name": "Vendor"},
                sender=cobrador.uri,
                receiver=venedor.uri,
                msgcnt=2,
            )

        agent_venedor_extern.MESSAGE_SENDER = fake_sender
        html = agent_venedor_extern.render_iface_page("10.0.0.1").get_data(as_text=True)
        self.assertIn("Vendor", html)
```

- [ ] **Step 2: Run the vendor-focused tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_venedor_extern_flow -v
```

Expected: FAIL because `agent_venedor_extern` still writes owner files locally and still reads seller-bank data directly.

- [ ] **Step 3: Implement vendor delegation through Compra and Cobrador**

```python
# protocols/compra.py
def build_peticio_registre_producte_extern_compra(payload, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-product-compra-{payload['product_id']}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreProducteExternCompra))
    graph.add((content, AZON.IdProducte, Literal(payload["product_id"])))
    graph.add((content, AZON.IdVenedorExtern, Literal(payload["seller_id"])))
    graph.add((content, AZON.RequereixLogisticaExterna, Literal(bool(payload["requires_external_logistics"]), datatype=XSD.boolean)))
    if payload.get("centre_id"):
        graph.add((content, AZON.IdCentreLogistic, Literal(payload["centre_id"])))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)
```

```python
# agents/agent_compra.py
from services.external_vendor_service import save_external_product_location, save_shipping_responsibility


def pla_registrar_producte_extern_compra(gm, content, sender):
    payload = parse_peticio_registre_producte_extern_compra(gm, content)
    save_shipping_responsibility(
        SHIPPING_RESPONSIBILITY_PATH,
        payload["product_id"],
        payload["seller_id"],
        payload["requires_external_logistics"],
    )
    if not payload["requires_external_logistics"] and payload.get("centre_id"):
        save_external_product_location(LOCATIONS_PATH, payload["product_id"], payload["centre_id"])
    return build_confirmacio_registre_producte_extern_compra(payload["product_id"], sender=AGENT.uri, receiver=sender, request_content=content, msgcnt=mss_cnt)
```

```python
# agents/agent_venedor_extern.py
def _register_product_metadata_with_compra(product):
    compra = resolve_agent_via_directory(AGENT, DirectoryAgent, MESSAGE_SENDER, _msgcnt, DSO.CompraAgent)
    message = build_peticio_registre_producte_extern_compra(
        {
            "product_id": product["product_id"],
            "seller_id": product["seller_id"],
            "requires_external_logistics": product["requires_external_logistics"],
            "centre_id": product.get("centre_id", ""),
        },
        sender=AGENT.uri,
        receiver=compra.uri,
        msgcnt=_msgcnt(),
    )
    return parse_confirmacio_registre_producte_extern_compra(MESSAGE_SENDER(message, compra.address))
```

```python
# protocols/pagament.py
def build_peticio_consulta_dades_venedor(seller_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"seller-profile-request-{seller_id}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaDadesBancariesVenedor))
    graph.add((content, AZON.IdVenedorExtern, Literal(seller_id)))
    return build_message(graph, ACL.request, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)

def build_resultat_consulta_dades_venedor(profile, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"seller-profile-response-{profile['seller_id']}"]
    graph.add((content, RDF.type, AZON.ResultatConsultaDadesBancariesVenedor))
    graph.add((content, AZON.IdVenedorExtern, Literal(profile["seller_id"])))
    graph.add((content, AZON.DadesBancariesVenedorExtern, Literal(profile["bank_data"])))
    graph.add((content, AZON.Nom, Literal(profile.get("seller_name", ""))))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(graph, ACL.inform, sender=sender, receiver=receiver, content=content, ontology=ONTOLOGY_URI, msgcnt=msgcnt)
```

- [ ] **Step 4: Re-run the vendor-focused tests and verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_venedor_extern_flow -v
```

Expected: PASS for registration, vendor-shipped purchase, and platform-shipped purchase flows with `Compra` and `Cobrador` as the only writers to their respective stores.

- [ ] **Step 5: Commit the vendor delegation refactor**

```bash
git add agents/agent_compra.py agents/agent_cobrador.py agents/agent_venedor_extern.py protocols/compra.py protocols/pagament.py tests/test_venedor_extern_flow.py
git commit -m "refactor: delegate vendor persistence to owner agents"
```

### Task 7: Cobrador Charges Without Reading the Catalog

**Files:**
- Modify: `protocols/centre_logistic.py:40-187`
- Modify: `services/logistics_service.py:96-143,404-418`
- Modify: `protocols/pagament.py:176-355`
- Modify: `agents/agent_cobrador.py:65-238`
- Modify: `tests/test_cobrador_flow.py`
- Modify: `tests/test_logistics_flow.py`

- [ ] **Step 1: Write failing tests for catalog-free internal charges**

```python
def test_internal_charge_uses_price_from_transport_message(self):
    from AgentUtil.Agent import Agent
    from agents import agent_cobrador
    from protocols.pagament import build_peticio_cobrament_intern, extract_confirmacio_pagament

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        agent_cobrador.configure_runtime(
            {
                "agent": Agent("CobradorAgent", AGN.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop"),
                "directory_agent": None,
                "data_dir": data_dir,
            }
        )
        client = agent_cobrador.app.test_client()
        message = build_peticio_cobrament_intern(
            {
                "localized_product_id": "ploc-1",
                "lot_id": "LOT-1",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "city": "Barcelona",
                "delivery_date": "2026-06-06",
                "transport_cost": 4.5,
                "product": {"product_id": "P1001", "name": "Teclat", "weight": 0.8, "price": 50.0},
            },
            sender=AGN.CentreLogistic,
            receiver=agent_cobrador.AGENT.uri,
            msgcnt=1,
        )
        response = client.get("/comm", query_string={"content": message.serialize(format="xml")})
        graph = Graph()
        graph.parse(data=response.get_data(as_text=True), format="xml")
        confirmation = extract_confirmacio_pagament(graph)
        self.assertEqual(confirmation["products_subtotal"], 50.0)
        self.assertEqual(confirmation["amount"], 54.5)
```

- [ ] **Step 2: Run the charging tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_cobrador_flow tests.test_logistics_flow -v
```

Expected: FAIL because `protocols.pagament.parse_peticio_cobrament_intern` drops product price and `agent_cobrador` still uses `CATALOG_PATH`.

- [ ] **Step 3: Carry invoice lines end-to-end and remove `CATALOG_PATH` from Cobrador**

```python
# protocols/centre_logistic.py
def _add_product_to_graph(graph, subject, product, centre_node=None):
    product_node = AZON[f"product-{product['product_id']}"]
    link_product(graph, subject, product_node, product_kind="intern")
    graph.add((product_node, RDF.type, AZON.ProducteIntern))
    graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if "name" in product:
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
    if "weight" in product:
        graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if "price" in product:
        graph.add((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
    return product_node


def parse_productes_localitzats(graph, content):
    product = None
    centre_id = None
    centre_city = None
    product = {
        "product_id": str(graph.value(product_node, AZON.IdProducte)),
        "name": str(graph.value(product_node, AZON.Nom) or ""),
        "weight": float(weight_value) if weight_value is not None else 0.0,
        "price": float(graph.value(product_node, AZON.Preu) or 0.0),
    }
```

```python
# services/logistics_service.py
def _add_product_reference(graph, subject, product, centre_node=None):
    product_node = AZON[f"product-{product['product_id']}"]
    link_product(graph, subject, product_node, product_kind="intern")
    graph.add((product_node, RDF.type, AZON.ProducteIntern))
    graph.set((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if "name" in product:
        graph.set((product_node, AZON.Nom, Literal(product["name"])))
    if "weight" in product:
        graph.set((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if "price" in product:
        graph.set((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))


def _read_item(graph, item_node):
    lot_node = graph.value(item_node, AZON.SobreLot)
    lot_id = graph.value(lot_node, AZON.IdLot) if lot_node is not None else None
    user_id = graph.value(item_node, AZON.IdUsuari)
    product = {
        "product_id": str(graph.value(product_node, AZON.IdProducte)),
        "name": str(graph.value(product_node, AZON.Nom) or ""),
        "weight": float(weight_value) if weight_value is not None else 0.0,
        "price": float(graph.value(product_node, AZON.Preu) or 0.0),
    }
```

```python
# agents/agent_cobrador.py
def pla_cobrament_intern(gm, content, sender):
    shipment = parse_peticio_cobrament_intern(gm, content)
    products = [shipment["product"]] if shipment.get("product") else []
    products_subtotal = round(sum(product.get("price", 0.0) for product in products), 2)
    amount = round(products_subtotal + shipment["transport_cost"], 2)
    payment = {
        "payment_id": f"PAY-{uuid4().hex[:8].upper()}",
        "order_id": shipment.get("order_id") or shipment.get("localized_product_id") or shipment["lot_id"],
        "amount": amount,
        "method": "targeta",
        "sentit": SENTIT_COBRAMENT,
        "user_id": shipment["user_id"],
        "products": products,
        "products_subtotal": products_subtotal,
        "transport_cost": shipment["transport_cost"],
        "status": OK_PAYMENT_STATUS,
        "date": _payment_date(),
    }
```

- [ ] **Step 4: Re-run the charging tests and verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_cobrador_flow tests.test_logistics_flow -v
```

Expected: PASS for internal-charge roundtrips, invoice extraction, and logistics-to-payment integration.

- [ ] **Step 5: Commit the catalog-free charging refactor**

```bash
git add agents/agent_cobrador.py protocols/centre_logistic.py protocols/pagament.py services/logistics_service.py tests/test_cobrador_flow.py tests/test_logistics_flow.py
git commit -m "refactor: remove catalog dependency from cobrador"
```

### Task 8: Documentation, Diagrams, and Full Verification

**Files:**
- Modify: `docs/AgentZon/Diagrames-Entrega-2.pd`
- Modify: `docs/Justificacions/JUSTIFICACIO_EINES.md`
- Modify: `docs/Justificacions/GUIA_NOU_INTEGRANT.md`
- Modify: `docs/AgentZon/desalineacions-codi-documentacio-diagrames.md`

- [ ] **Step 1: Update the editable Prometheus diagram with the new owner-query arrows**

```xml
<!-- docs/AgentZon/Diagrames-Entrega-2.pd -->
<message from="VenedorExtern" to="Compra" label="PeticioRegistreProducteExternCompra"/>
<message from="Retornador" to="Opinador" label="PeticioConsultaCompresUsuari"/>
<message from="Compra" to="Cercador" label="PeticioConsultaProductes"/>
<message from="Cercador" to="Opinador" label="PeticioRegistreCerca"/>
<message from="VenedorExtern" to="Cobrador" label="PeticioConsultaDadesBancariesVenedor"/>
```

- [ ] **Step 2: Update the justification and onboarding docs to describe the owner boundaries**

```md
## Propietat de dades

- `Cercador` és l'únic propietari de `productes.ttl`.
- `Compra` és l'únic propietari de `dades_enviament_usuari.ttl`, `responsable_enviament_productes.ttl`, `ubicacions_productes.ttl` i `seguiment_enviaments.ttl`.
- `Opinador` és l'únic propietari de `historial_cerques.ttl`, `historial_compres.ttl` i `feedback.ttl`.
- `Retornador` és l'únic propietari de `devolucions.ttl`.
- `Cobrador` és l'únic propietari de `dades_bancaries_usuari.ttl`, `dades_bancaries_venedors_externs.ttl` i `pagaments.ttl`.
- Qualsevol accés extern a aquestes dades es fa amb FIPA-ACL + RDF, no amb lectures directes de fitxer.
```

- [ ] **Step 3: Run focused ownership regressions and then the full suite**

Run:

```bash
.venv/bin/python -m unittest tests.test_agent_data_ownership tests.test_cercador_flow tests.test_purchase_flow tests.test_opinador_flow tests.test_return_policy tests.test_venedor_extern_flow tests.test_cobrador_flow tests.test_logistics_flow -v
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Expected: PASS for the focused boundary tests first, then PASS for the full suite.

- [ ] **Step 4: Run a syntax/lint sanity pass on the edited Python modules**

Run:

```bash
.venv/bin/python -m compileall agents protocols services tests
```

Expected: PASS with no syntax errors in the edited modules.

- [ ] **Step 5: Commit the documentation and verification updates**

```bash
git add docs/AgentZon/Diagrames-Entrega-2.pd docs/Justificacions/JUSTIFICACIO_EINES.md docs/Justificacions/GUIA_NOU_INTEGRANT.md docs/AgentZon/desalineacions-codi-documentacio-diagrames.md
git commit -m "docs: document database ownership protocols"
```

## Self-Review

### Spec coverage

- Single-owner database enforcement: covered by Task 1 runtime assertions and Tasks 2-7 code changes.
- `Compra` ownership (`dades_enviament_usuari.ttl`, `responsable_enviament_productes.ttl`, `ubicacions_productes.ttl`, `seguiment_enviaments.ttl`): covered by Tasks 2 and 6.
- `Cercador` ownership (`productes.ttl`): covered by Tasks 2 and 3.
- `Opinador` ownership (`historial_cerques.ttl`, `historial_compres.ttl`, `feedback.ttl`): covered by Tasks 3, 4, and 5.
- `Retornador` ownership (`devolucions.ttl`): covered by Task 5.
- `Centre Logístic` ownership (`lots-*.ttl`): covered by Task 7.
- `Cobrador` ownership (`dades_bancaries_usuari.ttl`, `dades_bancaries_venedors_externs.ttl`, `pagaments.ttl`): covered by Tasks 6 and 7.
- `Diagrames-Entrega-2.pd` update: covered by Task 8.
- Justification/onboarding docs update: covered by Task 8.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.
- Every code-changing step includes a concrete code block.
- Every verification step includes an exact command.

### Type consistency

- New protocol names are kept consistent across ontology, protocol modules, and agent dispatchers:
  - `PeticioConsultaProductes`
  - `PeticioRegistreCerca`
  - `PeticioConsultaCompresUsuari`
  - `PeticioRegistreProducteExternCompra`
  - `PeticioConsultaDadesBancariesVenedor`
- The plan assumes rich product snapshots consistently carry:
  - `product_id`
  - `name`
  - `category`
  - `brand`
  - `price`
  - `weight`
  - `seller_id`
  - `requires_external_logistics`
