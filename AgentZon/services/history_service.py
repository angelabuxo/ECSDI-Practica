"""Persistence helpers for search and purchase history graphs."""

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import load_graph, save_graph


# Search history -------------------------------------------------------------------
def record_search(path, criteria, products):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"HistorialCerca-{len(graph)}"]
    graph.add((record, RDF.type, AZON.HistorialCerca))
    graph.add((record, AZON.TeText, Literal(criteria.get("text", ""))))
    graph.add((record, AZON.TeCategoria, Literal(criteria.get("category", ""))))
    graph.add((record, AZON.TeMarca, Literal(criteria.get("brand", ""))))
    graph.add((record, AZON.TotalResultats, Literal(len(products))))
    for product in products:
        product_node = AZON[f"Producte-{product['product_id']}"]
        graph.add((record, AZON.MostraProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    save_graph(path, graph)


# Purchase history -----------------------------------------------------------------
def record_purchase(path, order):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"HistorialCompra-{order['order_id']}"]
    order_node = AZON[f"Comanda-{order['order_id']}"]
    graph.add((record, RDF.type, AZON.HistorialCompra))
    graph.add((record, AZON.SobreComanda, order_node))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.IdUsuari, Literal(order["user_id"])))
    for product in order["products"]:
        product_node = AZON[f"Producte-{product['product_id']}"]
        graph.add((record, AZON.TeProducte, product_node))
        graph.add((order_node, AZON.TeProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    save_graph(path, graph)
