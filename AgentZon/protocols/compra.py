"""Ontology-backed messages for purchase-history registration requests."""

from rdflib import Graph, Literal, RDF

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.OntoNamespaces import AZON, AZON_ONTOLOGY, bind_namespaces


def _product_node(product_id):
    return AZON[f"Producte-{product_id}"]


def _order_node(order_id):
    return AZON[f"Comanda-{order_id}"]


# RDF builders --------------------------------------------------------------------
def build_peticio_registre_compra(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"PeticioRegistreCompra-{order['order_id']}"]
    order_node = _order_node(order["order_id"])
    graph.add((content, RDF.type, AZON.PeticioRegistreCompra))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.IdUsuari, Literal(order["user_id"])))
    for product in order["products"]:
        product_node = _product_node(product["product_id"])
        graph.add((content, AZON.TeProducte, product_node))
        graph.add((order_node, AZON.TeProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        msgcnt=msgcnt,
        ontology=AZON_ONTOLOGY,
    )


# RDF parsers ---------------------------------------------------------------------
def parse_peticio_registre_compra(graph, content):
    order_node = graph.value(content, AZON.SobreComanda)
    return {
        "order_id": str(graph.value(order_node, AZON.IdComanda)),
        "user_id": str(graph.value(order_node, AZON.IdUsuari)),
        "product_ids": [str(graph.value(node, AZON.IdProducte)) for node in graph.objects(content, AZON.TeProducte)],
    }


def build_confirmacio_registre_compra(order_id, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"ConfirmacioRegistreCompra-{order_id}"]
    order_node = _order_node(order_id)
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreCompra))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order_id)))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        msgcnt=msgcnt,
        ontology=AZON_ONTOLOGY,
    )


def extract_registration_confirmation(graph):
    props = get_message_properties(graph)
    content = props["content"]
    order_node = graph.value(content, AZON.SobreComanda)
    return str(graph.value(order_node, AZON.IdComanda))
