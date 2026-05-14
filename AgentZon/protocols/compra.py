"""Ontology-backed messages for purchase-history registration requests."""

from rdflib import Graph, Literal, RDF

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces


# RDF builders --------------------------------------------------------------------
def build_peticio_registre_compra(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-request-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]

    graph.add((content, RDF.type, AZON.PeticioRegistreCompra))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((content, AZON.SobreComanda, order_node))

    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.IdUsuari, Literal(order["user_id"])))

    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.SobreProducte, product_node))
        graph.add((order_node, AZON.SobreProducte, product_node))

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


# RDF parsers ---------------------------------------------------------------------
def parse_peticio_registre_compra(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            local = str(product_node).rsplit("product-", 1)[-1]
            product_id = Literal(local)
        products.append({"product_id": str(product_id)})

    return {
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "products": products,
    }


def build_confirmacio_registre_compra(order_id, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-confirmation-{order_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreCompra))
    graph.add((content, AZON.IdComanda, Literal(order_id)))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{order_id}"]))
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


def build_peticio_enviament_extern(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-shipping-request-{order['order_id']}"]
    graph.add((content, RDF.type, AZON.PeticioEnviamentExtern))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((content, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{order['order_id']}"]))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_registration_confirmation(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return str(graph.value(content, AZON.IdComanda))
