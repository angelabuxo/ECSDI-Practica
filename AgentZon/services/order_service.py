"""Persistence helpers for shipping data and internal order creation."""

from uuid import uuid4

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import load_graph, save_graph


# Shipping persistence -------------------------------------------------------------
def save_user_shipping_data(shipping_path, shipping_data):
    graph = load_graph(shipping_path)
    bind_namespaces(graph)
    node = AZON[f"shipping-{shipping_data['user_id']}"]
    graph.add((node, RDF.type, AZON.DadesEnviamentUsuari))
    graph.add((node, AZON.idUsuari, Literal(shipping_data["user_id"])))
    graph.add((node, AZON.nom, Literal(shipping_data["user_name"])))
    graph.add((node, AZON.carrer, Literal(shipping_data["street_address"])))
    graph.add((node, AZON.ciutat, Literal(shipping_data["city"])))
    graph.add((node, AZON.prioritat, Literal(shipping_data["priority"])))
    graph.add((node, AZON.metodePagament, Literal(shipping_data["payment_method"])))
    save_graph(shipping_path, graph)


# Order persistence ----------------------------------------------------------------
def create_order(orders_path, shipping_data, products):
    order = {
        "order_id": f"ORDER-{uuid4().hex[:8].upper()}",
        "user_id": shipping_data["user_id"],
        "user_name": shipping_data["user_name"],
        "products": products,
        "shipping_data": shipping_data,
    }
    graph = load_graph(orders_path)
    bind_namespaces(graph)
    node = AZON[f"order-{order['order_id']}"]
    graph.add((node, RDF.type, AZON.Comanda))
    graph.add((node, AZON.idComanda, Literal(order["order_id"])))
    graph.add((node, AZON.idUsuari, Literal(order["user_id"])))
    graph.add((node, AZON.nom, Literal(order["user_name"])))
    graph.add((node, AZON.carrer, Literal(order["shipping_data"]["street_address"])))
    graph.add((node, AZON.ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((node, AZON.prioritat, Literal(order["shipping_data"]["priority"])))
    for product in order["products"]:
        graph.add((node, AZON.teProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(orders_path, graph)
    return order
