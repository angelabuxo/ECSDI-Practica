"""Missatges de feedback, suggeriments i devolucions per a l'Agent Opinador."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces
from protocols.compra import extract_order_snapshot
from protocols.rdf_refs import link_sobre_comanda, order_id_from_node


def _add_product_reference(graph, subject, product):
    product_node = AZON[f"product-{product['product_id']}"]
    graph.add((subject, AZON.SobreProducte, product_node))
    product_type = AZON.ProducteExtern if product.get("seller_id") else AZON.Producte
    graph.add((product_node, RDF.type, product_type))
    graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if "name" in product:
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
    if "description" in product:
        graph.add((product_node, AZON.Descripcio, Literal(product["description"])))
    if "category" in product:
        graph.add((product_node, AZON.Categoria, Literal(product["category"])))
    if "brand" in product:
        graph.add((product_node, AZON.Marca, Literal(product["brand"])))
    if "price" in product:
        graph.add((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
    if "weight" in product:
        graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    return product_node


def build_peticio_feedback(feedback_request, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"feedback-request-{feedback_request['feedback_id']}"]
    graph.add((content, RDF.type, AZON.PeticioFeedback))
    graph.add((content, AZON.IdFeedback, Literal(feedback_request["feedback_id"])))
    graph.add((content, AZON.IdUsuari, Literal(feedback_request["user_id"])))
    link_sobre_comanda(graph, content, feedback_request["order_id"])
    if feedback_request.get("prompt"):
        graph.add((content, AZON.Comentari, Literal(feedback_request["prompt"])))
    for product in feedback_request.get("products", []):
        _add_product_reference(graph, content, product)
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def build_peticio_consulta_comanda(order_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"order-query-{order_id}"]
    graph.add((content, RDF.type, AZON.PeticioConsultaComanda))
    link_sobre_comanda(graph, content, order_id)
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_consulta_comanda(graph, content):
    return order_id_from_node(graph, content)


def build_resultat_consulta_comanda(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    order_node = AZON[f"order-{order['order_id']}"]
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((order_node, AZON.Nom, Literal(order["user_name"])))
    graph.add((order_node, AZON.Carrer, Literal(order["shipping_data"]["street_address"])))
    graph.add((order_node, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((order_node, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.add((order_node, AZON.MetodePagament, Literal(order["shipping_data"]["payment_method"])))
    if order.get("purchase_date"):
        graph.add((order_node, AZON.DataCompra, Literal(order["purchase_date"])))
    if order.get("delivery_date"):
        graph.add((order_node, AZON.DataEntrega, Literal(order["delivery_date"])))
    if order.get("final_delivery_date"):
        graph.add((order_node, AZON.DataEntregaDefinitiva, Literal(order["final_delivery_date"])))
    if order.get("status"):
        graph.add((order_node, AZON.Estat, Literal(order["status"])))
    for product in order.get("products", []):
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((order_node, AZON.TeProducte, product_node))
        product_type = AZON.ProducteExtern if product.get("seller_id") else AZON.Producte
        graph.add((product_node, RDF.type, product_type))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
        if "name" in product:
            graph.add((product_node, AZON.Nom, Literal(product["name"])))
        if "description" in product:
            graph.add((product_node, AZON.Descripcio, Literal(product["description"])))
        if "category" in product:
            graph.add((product_node, AZON.Categoria, Literal(product["category"])))
        if "brand" in product:
            graph.add((product_node, AZON.Marca, Literal(product["brand"])))
        if "price" in product:
            graph.add((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
        if "weight" in product:
            graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=order_node,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_resultat_consulta_comanda(graph):
    props = get_message_properties(graph)
    return extract_order_snapshot(graph, props["content"])


def parse_peticio_feedback(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        products.append({"product_id": str(product_id)})
    return {
        "feedback_id": str(graph.value(content, AZON.IdFeedback)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "order_id": order_id_from_node(graph, content),
        "prompt": str(graph.value(content, AZON.Comentari) or ""),
        "product_ids": sorted(product["product_id"] for product in products),
        "products": products,
    }


def build_resposta_feedback(feedback, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"feedback-response-{feedback['feedback_id']}"]
    graph.add((content, RDF.type, AZON.RespostaFeedback))
    graph.add((content, AZON.IdFeedback, Literal(feedback["feedback_id"])))
    graph.add((content, AZON.IdUsuari, Literal(feedback["user_id"])))
    link_sobre_comanda(graph, content, feedback["order_id"])
    graph.add((content, AZON.Puntuacio, Literal(feedback["rating"])))
    graph.add((content, AZON.Comentari, Literal(feedback.get("comment", ""))))
    for product_id in feedback.get("product_ids", []):
        product_node = AZON[f"product-{product_id}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_resposta_feedback(graph, content):
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))
    return {
        "feedback_id": str(graph.value(content, AZON.IdFeedback)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "order_id": order_id_from_node(graph, content),
        "rating": int(graph.value(content, AZON.Puntuacio)),
        "comment": str(graph.value(content, AZON.Comentari) or ""),
        "product_ids": sorted(product_ids),
    }


def build_resposta_recomanacio(recommendation, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"recommendation-response-{recommendation['recommendation_id']}"]
    recommendation_node = AZON[f"recommendation-{recommendation['recommendation_id']}"]
    graph.add((content, RDF.type, AZON.RespostaRecomanacio))
    graph.add((content, AZON.GeneraRecomanacio, recommendation_node))
    graph.add((recommendation_node, RDF.type, AZON.Recomanacio))
    for product in recommendation.get("products", []):
        _add_product_reference(graph, recommendation_node, product)
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_recomanacio_products(graph, content=None):
    if content is None:
        content = graph.value(predicate=RDF.type, object=AZON.RespostaRecomanacio)
    recommendation_node = graph.value(content, AZON.GeneraRecomanacio)
    products = []
    for product_node in graph.objects(recommendation_node, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        products.append({"product_id": str(product_id)})
    return products


def build_peticio_devolucio(return_request, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"return-request-{return_request['return_id']}"]
    graph.add((content, RDF.type, AZON.PeticioDevolucio))
    graph.add((content, AZON.IdDevolucio, Literal(return_request["return_id"])))
    link_sobre_comanda(graph, content, return_request["order_id"])
    graph.add((content, AZON.IdUsuari, Literal(return_request["user_id"])))
    if return_request.get("amount") is not None:
        graph.add((content, AZON.ImportPagament, Literal(return_request["amount"], datatype=XSD.float)))
    graph.add((content, AZON.MotiuDevolucio, Literal(return_request.get("reason", ""))))
    if return_request.get("seller_id"):
        graph.add((content, AZON.IdVenedorExtern, Literal(return_request["seller_id"])))
    for product in return_request.get("products", []):
        _add_product_reference(graph, content, product)
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_devolucio(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        products.append({"product_id": str(product_id)})
    seller_id = graph.value(content, AZON.IdVenedorExtern)
    amount_value = graph.value(content, AZON.ImportPagament)
    return {
        "return_id": str(graph.value(content, AZON.IdDevolucio)),
        "order_id": order_id_from_node(graph, content),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "amount": float(amount_value) if amount_value is not None else None,
        "reason": str(graph.value(content, AZON.MotiuDevolucio) or ""),
        "seller_id": str(seller_id) if seller_id is not None else None,
        "product_ids": sorted(product["product_id"] for product in products),
        "products": products,
    }


def _amount_as_float(amount):
    """Normalitza imports opcionals (None) a float per literals XSD."""
    if amount is None:
        return 0.0
    try:
        return float(amount)
    except (TypeError, ValueError):
        return 0.0


def build_resolucio_devolucio(decision, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"return-response-{decision['return_id']}"]
    graph.add((content, RDF.type, AZON.ResolucioDevolucio))
    graph.add((content, AZON.IdDevolucio, Literal(decision["return_id"])))
    link_sobre_comanda(graph, content, decision["order_id"])
    graph.add((content, AZON.IdUsuari, Literal(decision["user_id"])))
    graph.add((content, AZON.ImportPagament, Literal(_amount_as_float(decision.get("amount")), datatype=XSD.float)))
    graph.add((content, AZON.Acceptada, Literal(bool(decision["accepted"]), datatype=XSD.boolean)))
    graph.add((content, AZON.MotiuDevolucio, Literal(decision.get("reason", ""))))
    for product_id in decision.get("product_ids", []):
        product_node = AZON[f"product-{product_id}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product_id)))
    if decision.get("seller_id"):
        graph.add((content, AZON.IdVenedorExtern, Literal(decision["seller_id"])))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_resolucio_devolucio(graph, content=None):
    if content is None:
        content = graph.value(predicate=RDF.type, object=AZON.ResolucioDevolucio)
    product_ids = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))
    amount_value = graph.value(content, AZON.ImportPagament)
    return {
        "return_id": str(graph.value(content, AZON.IdDevolucio)),
        "order_id": order_id_from_node(graph, content),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "amount": _amount_as_float(amount_value),
        "accepted": bool(graph.value(content, AZON.Acceptada).toPython()),
        "reason": str(graph.value(content, AZON.MotiuDevolucio) or ""),
        "product_ids": sorted(product_ids),
    }


def parse_feedback_confirmation(graph, content=None):
    if content is None:
        content = graph.value(predicate=RDF.type, object=AZON.RespostaFeedback)
    return {
        "feedback_id": str(graph.value(content, AZON.IdFeedback)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "order_id": order_id_from_node(graph, content),
        "rating": int(graph.value(content, AZON.Puntuacio)),
        "comment": str(graph.value(content, AZON.Comentari) or ""),
    }
