"""Registre d'historial de cerques, compres i feedback."""

from datetime import date, datetime

from rdflib import Graph, Literal, RDF

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from protocols.rdf_refs import ensure_order_node, link_sobre_comanda, order_id_from_node
from services.rdf_store import load_graph, save_graph


# Search history -------------------------------------------------------------------
def record_search(path, criteria, products, user_id=None):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"search-{len(graph)}"]
    graph.add((record, AZON.TextConsulta, Literal(criteria.get("text", ""))))
    graph.add((record, AZON.CategoriaConsulta, Literal(criteria.get("category", ""))))
    graph.add((record, AZON.MarcaConsulta, Literal(criteria.get("brand", ""))))
    if user_id:
        graph.add((record, AZON.IdUsuari, Literal(user_id)))
    if criteria.get("min_price") is not None:
        graph.add((record, AZON.PreuMinim, Literal(criteria["min_price"])))
    if criteria.get("max_price") is not None:
        graph.add((record, AZON.PreuMaxim, Literal(criteria["max_price"])))
    graph.add((record, AZON.TotalResultats, Literal(len(products))))
    for product in products:
        graph.add((record, AZON.MostraProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(path, graph)


def load_search_records(path, user_id=None):
    graph = load_graph(path)
    records = []
    for record in set(graph.subjects(AZON.TextConsulta, None)) | set(graph.subjects(AZON.TotalResultats, None)):
        record_user_id = str(graph.value(record, AZON.IdUsuari) or "")
        if user_id is not None and record_user_id != user_id:
            continue
        product_ids = []
        for product_node in graph.objects(record, AZON.MostraProducte):
            product_id = graph.value(product_node, AZON.IdProducte)
            if product_id is None:
                product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
            product_ids.append(str(product_id))
        records.append(
            {
                "search_id": str(record).rsplit("search-", 1)[-1],
                "user_id": record_user_id,
                "criteria": {
                    "text": str(graph.value(record, AZON.TextConsulta) or ""),
                    "category": str(graph.value(record, AZON.CategoriaConsulta) or ""),
                    "brand": str(graph.value(record, AZON.MarcaConsulta) or ""),
                    "min_price": _optional_float(graph.value(record, AZON.PreuMinim)),
                    "max_price": _optional_float(graph.value(record, AZON.PreuMaxim)),
                },
                "total_results": int(graph.value(record, AZON.TotalResultats) or 0),
                "product_ids": sorted(product_ids),
            }
        )
    return records


# Purchase history -----------------------------------------------------------------
def record_purchase(path, order):
    graph = load_graph(path)
    bind_namespaces(graph)
    record = AZON[f"purchase-{order['order_id']}"]
    purchase_date = order.get("purchase_date") or date.today().isoformat()
    ensure_order_node(graph, order["order_id"])
    graph.add((record, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((record, AZON.DataCompra, Literal(purchase_date)))
    link_sobre_comanda(graph, record, order["order_id"])
    for product in order["products"]:
        graph.add((record, AZON.SobreProducte, AZON[f"product-{product['product_id']}"]))
    save_graph(path, graph)


def load_purchase_records(path, user_id=None):
    graph = load_graph(path)
    records = []
    for record in set(graph.subjects(AZON.DataCompra, None)):
        record_user_id = str(graph.value(record, AZON.IdUsuari) or "")
        if user_id is not None and record_user_id != user_id:
            continue
        products = []
        for product_node in graph.objects(record, AZON.SobreProducte):
            product_id = graph.value(product_node, AZON.IdProducte)
            if product_id is None:
                product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
            products.append({"product_id": str(product_id)})
        records.append(
            {
                "order_id": order_id_from_node(graph, record),
                "user_id": record_user_id,
                "purchase_date": str(graph.value(record, AZON.DataCompra) or ""),
                "product_ids": sorted(product["product_id"] for product in products),
                "products": products,
            }
        )
    return records


def get_latest_purchase_for_user(path, user_id):
    records = load_purchase_records(path, user_id=user_id)
    if not records:
        return None
    return records[-1]


def record_feedback(path, feedback):
    graph = load_graph(path)
    bind_namespaces(graph)
    node = AZON[f"feedback-{feedback['feedback_id']}"]
    graph.add((node, RDF.type, AZON.Feedback))
    graph.add((node, AZON.IdFeedback, Literal(feedback["feedback_id"])))
    graph.add((node, AZON.IdUsuari, Literal(feedback["user_id"])))
    graph.add((node, AZON.IdComanda, Literal(feedback["order_id"])))
    graph.add((node, AZON.Puntuacio, Literal(feedback["rating"])))
    graph.add((node, AZON.Comentari, Literal(feedback.get("comment", ""))))
    graph.add((node, AZON.DataCompra, Literal(feedback.get("date", date.today().isoformat()))))
    for product_id in feedback.get("product_ids", []):
        graph.add((node, AZON.SobreProducte, AZON[f"product-{product_id}"]))
    save_graph(path, graph)


def load_feedback_records(path, user_id=None):
    graph = load_graph(path)
    records = []
    for node in set(graph.subjects(RDF.type, AZON.Feedback)):
        record_user_id = str(graph.value(node, AZON.IdUsuari) or "")
        if user_id is not None and record_user_id != user_id:
            continue
        product_ids = []
        for product_node in graph.objects(node, AZON.SobreProducte):
            product_id = graph.value(product_node, AZON.IdProducte)
            if product_id is None:
                product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
            product_ids.append(str(product_id))
        records.append(
            {
                "feedback_id": str(graph.value(node, AZON.IdFeedback) or ""),
                "user_id": record_user_id,
                "order_id": str(graph.value(node, AZON.IdComanda) or ""),
                "rating": int(graph.value(node, AZON.Puntuacio) or 0),
                "comment": str(graph.value(node, AZON.Comentari) or ""),
                "date": str(graph.value(node, AZON.DataCompra) or ""),
                "product_ids": sorted(product_ids),
            }
        )
    return records


def _optional_float(value):
    return None if value is None else float(value)
