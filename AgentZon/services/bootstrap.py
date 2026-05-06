"""Seed data generators for the AgentZon Phase 2 prototype."""

from pathlib import Path

from rdflib import Graph, Literal, RDF, XSD

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import save_graph


# Seed graph builders --------------------------------------------------------------
def _build_products_graph():
    graph = Graph()
    bind_namespaces(graph)

    products = [
        {
            "id": "P1001",
            "name": "Wireless Headphones",
            "description": "Wireless over-ear headphones with noise isolation",
            "category": "audio",
            "brand": "AuralMax",
            "price": 89.99,
            "weight": 1.5,
        },
        {
            "id": "P1002",
            "name": "Portable Speaker",
            "description": "Compact bluetooth speaker for travel",
            "category": "audio",
            "brand": "AuralMax",
            "price": 59.99,
            "weight": 1.1,
        },
        {
            "id": "P2001",
            "name": "Mechanical Keyboard",
            "description": "Mechanical keyboard with tactile switches",
            "category": "peripherals",
            "brand": "KeyForge",
            "price": 129.00,
            "weight": 2.4,
        },
        {
            "id": "P3001",
            "name": "Ceramic Coffee Mug",
            "description": "Ceramic mug for hot drinks",
            "category": "home",
            "brand": "CasaNova",
            "price": 15.50,
            "weight": 0.6,
        },
    ]

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
        graph.add((product, AZON.UbicatACentre, centre))
    return graph


def _build_empty_graph():
    graph = Graph()
    bind_namespaces(graph)
    return graph


# Bootstrap orchestration ----------------------------------------------------------
def bootstrap_phase2_data(data_dir):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "productes.ttl": _build_products_graph(),
        "ubicacions_productes.ttl": _build_locations_graph(),
        "historial_cerques.ttl": _build_empty_graph(),
        "historial_compres.ttl": _build_empty_graph(),
        "comandes.ttl": _build_empty_graph(),
        "dades_enviament_usuari.ttl": _build_empty_graph(),
        "lots.ttl": _build_empty_graph(),
    }

    for filename, graph in files.items():
        save_graph(data_dir / filename, graph)
