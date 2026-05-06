"""Persistence helpers for shipping data and internal order creation."""

from uuid import uuid4

from rdflib import Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import load_graph, save_graph


# Order construction ---------------------------------------------------------------
def build_order(shipping_data, products):
    return {
        "order_id": f"ORDER-{uuid4().hex[:8].upper()}",
        "user_id": shipping_data["user_id"],
        "user_name": shipping_data["user_name"],
        "products": products,
        "shipping_data": shipping_data,
    }


# Shipping persistence -------------------------------------------------------------
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


# Order persistence ----------------------------------------------------------------
def save_order(orders_path, order):
    graph = load_graph(orders_path)
    bind_namespaces(graph)
    node = AZON[f"order-{order['order_id']}"]
    shipping_node = AZON[f"shipping-{order['order_id']}"]
    graph.add((node, RDF.type, AZON.Comanda))
    graph.add((node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((node, AZON.Nom, Literal(order["user_name"])))
    graph.add((node, AZON.Carrer, Literal(order["shipping_data"]["street_address"])))
    graph.add((node, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((node, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.add((node, AZON.TeDadesEnviament, shipping_node))
    for product in order["products"]:
        graph.add((node, AZON.TeProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(orders_path, graph)
