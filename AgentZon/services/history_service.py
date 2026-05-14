"""Persistence helpers for search and purchase history graphs."""

from datetime import date

from rdflib import Graph, Literal

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from services.rdf_store import load_graph, save_graph


# Search history -------------------------------------------------------------------
def record_search(path, criteria, products):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"search-{len(graph)}"]
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


# Purchase history -----------------------------------------------------------------
def record_purchase(path, order):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"purchase-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]
    graph.add((record, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((record, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((record, AZON.SobreComanda, order_node))
    graph.add((record, AZON.DataCompra, Literal(order.get("purchase_date", date.today().isoformat()))))
    if order.get("delivery_date") is not None:
        graph.add((record, AZON.DataEntregaDefinitiva, Literal(order["delivery_date"])))
    for product in order["products"]:
        graph.add((record, AZON.SobreProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(path, graph)
