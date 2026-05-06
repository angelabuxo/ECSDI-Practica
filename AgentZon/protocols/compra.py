"""Ontology-backed messages for purchase-history registration requests."""

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces


# RDF builders --------------------------------------------------------------------
def build_peticio_registre_compra(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-request-{order['order_id']}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreCompra))
    graph.add((content, AZON.idComanda, Literal(order["order_id"])))
    graph.add((content, AZON.idUsuari, Literal(order["user_id"])))
    for product in order["products"]:
        graph.add((content, AZON.idProducte, Literal(product["product_id"])))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        msgcnt=msgcnt,
    )


# RDF parsers ---------------------------------------------------------------------
def parse_peticio_registre_compra(graph, content):
    return {
        "order_id": str(graph.value(content, AZON.idComanda)),
        "user_id": str(graph.value(content, AZON.idUsuari)),
        "product_ids": [str(value) for value in graph.objects(content, AZON.idProducte)],
    }


def build_confirmacio_registre_compra(order_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-confirmation-{order_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreCompra))
    graph.add((content, AZON.idComanda, Literal(order_id)))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        msgcnt=msgcnt,
    )


def extract_registration_confirmation(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return str(graph.value(content, AZON.idComanda))
