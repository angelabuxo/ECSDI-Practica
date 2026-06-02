"""Construccio i persistencia de comandes i dades d'enviament de l'usuari."""

from datetime import date, timedelta
from uuid import uuid4

from rdflib import Literal, RDF

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from services.rdf_store import load_graph, save_graph


# Order construction ---------------------------------------------------------------
def _priority_to_delivery_date(priority):
    offsets = {
        "5 dies": 5,
        "7 dies": 7,
        "24h": 1,
        "48h": 2,
        "72h": 3,
    }
    return (date.today() + timedelta(days=offsets.get(priority, 7))).isoformat()


def build_order(shipping_data, products):
    return {
        "order_id": f"ORDER-{uuid4().hex[:8].upper()}",
        "user_id": shipping_data["user_id"],
        "user_name": shipping_data["user_name"],
        "products": products,
        "shipping_data": shipping_data,
        "delivery_date": _priority_to_delivery_date(shipping_data["priority"]),
        "final_delivery_date": None,
    }


# Shipping persistence -------------------------------------------------------------
def save_user_shipping_data(shipping_path, order):
    graph = load_graph(shipping_path)
    bind_namespaces(graph)
    shipping = order["shipping_data"]
    node = AZON[f"shipping-{order['order_id']}"]
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
    graph.add((node, RDF.type, AZON.Comanda))
    graph.set((node, AZON.IdComanda, Literal(order["order_id"])))
    graph.set((node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.set((node, AZON.Nom, Literal(order["user_name"])))
    graph.set((node, AZON.Carrer, Literal(order["shipping_data"]["street_address"])))
    graph.set((node, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.set((node, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.set((node, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.set((node, AZON.MetodePagament, Literal(order["shipping_data"]["payment_method"])))
    for product in order["products"]:
        graph.add((node, AZON.TeProducte, AZON[f"product-{product['product_id']}"]))
    if order.get("final_delivery_date"):
        graph.set((node, AZON.DataEntregaDefinitiva, Literal(order["final_delivery_date"])))
    save_graph(orders_path, graph)


def load_order(orders_path, order_id):
    graph = load_graph(orders_path)
    bind_namespaces(graph)
    node = AZON[f"order-{order_id}"]
    if (node, RDF.type, AZON.Comanda) not in graph:
        return None

    product_ids = []
    for product_node in graph.objects(node, AZON.TeProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))

    final_delivery_date = graph.value(node, AZON.DataEntregaDefinitiva)
    return {
        "order_id": order_id,
        "user_id": str(graph.value(node, AZON.IdUsuari)),
        "user_name": str(graph.value(node, AZON.Nom)),
        "product_ids": sorted(product_ids),
        "delivery_date": str(graph.value(node, AZON.DataEntrega)),
        "final_delivery_date": str(final_delivery_date) if final_delivery_date is not None else None,
        "shipping_data": {
            "user_name": str(graph.value(node, AZON.Nom)),
            "street_address": str(graph.value(node, AZON.Carrer)),
            "city": str(graph.value(node, AZON.Ciutat)),
            "priority": str(graph.value(node, AZON.Prioritat)),
            "payment_method": str(graph.value(node, AZON.MetodePagament)),
            "user_id": str(graph.value(node, AZON.IdUsuari)),
        },
    }


def update_order_final_delivery_date(orders_path, order_id, final_delivery_date):
    graph = load_graph(orders_path)
    bind_namespaces(graph)
    node = AZON[f"order-{order_id}"]
    graph.set((node, AZON.DataEntregaDefinitiva, Literal(final_delivery_date)))
    save_graph(orders_path, graph)
