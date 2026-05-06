"""Persistence helpers for shipping data and internal order creation."""

from uuid import uuid4

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import load_graph, save_graph


# Shipping persistence -------------------------------------------------------------
def save_user_shipping_data(shipping_path, shipping_data):
    graph = load_graph(shipping_path)
    bind_namespaces(graph)
    node = AZON[f"DadesEnviament-{shipping_data['user_id']}"]
    graph.add((node, RDF.type, AZON.DadesEnviamentUsuari))
    graph.add((node, AZON.IdUsuari, Literal(shipping_data["user_id"])))
    graph.add((node, AZON.Nom, Literal(shipping_data["user_name"])))
    graph.add((node, AZON.Carrer, Literal(shipping_data["street_address"])))
    graph.add((node, AZON.Ciutat, Literal(shipping_data["city"])))
    graph.add((node, AZON.Prioritat, Literal(shipping_data["priority"])))
    graph.add((node, AZON.MetodePagament, Literal(shipping_data["payment_method"])))
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
    node = AZON[f"Comanda-{order['order_id']}"]
    shipping_node = AZON[f"DadesEnviament-{order['user_id']}"]
    graph.add((node, RDF.type, AZON.Comanda))
    graph.add((node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((node, AZON.Nom, Literal(order["user_name"])))
    graph.add((node, AZON.TeDadesEnviament, shipping_node))
    for product in order["products"]:
        product_node = AZON[f"Producte-{product['product_id']}"]
        graph.add((node, AZON.TeProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    save_graph(orders_path, graph)
    return order
