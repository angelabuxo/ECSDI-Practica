"""Persistence helpers for search and purchase history graphs."""

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import load_graph, save_graph


# Search history -------------------------------------------------------------------
def record_search(path, criteria, products):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"search-{len(graph)}"]
    graph.add((record, RDF.type, AZON.PeticioCerca))
    graph.add((record, AZON.teText, Literal(criteria.get("text", ""))))
    graph.add((record, AZON.teCategoria, Literal(criteria.get("category", ""))))
    graph.add((record, AZON.teMarca, Literal(criteria.get("brand", ""))))
    graph.add((record, AZON.totalResultats, Literal(len(products))))
    for product in products:
        graph.add((record, AZON.mostraProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(path, graph)


# Purchase history -----------------------------------------------------------------
def record_purchase(path, order):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"purchase-{order['order_id']}"]
    graph.add((record, RDF.type, AZON.HistorialCompra))
    graph.add((record, AZON.idComanda, Literal(order["order_id"])))
    graph.add((record, AZON.idUsuari, Literal(order["user_id"])))
    for product in order["products"]:
        graph.add((record, AZON.idProducte, Literal(product["product_id"])))
    save_graph(path, graph)
