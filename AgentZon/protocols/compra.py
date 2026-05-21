"""Ontology-backed purchase and purchase-history registration messages."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces


def _add_product_reference(graph, subject, product):
    product_node = AZON[f"product-{product['product_id']}"]
    graph.add((subject, AZON.TeProducte, product_node))
    graph.add((product_node, RDF.type, AZON.Producte))
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


def _build_embedded_order(graph, order_node, order, include_order_id):
    shipping = order["shipping_data"]
    graph.add((order_node, RDF.type, AZON.Comanda))
    if include_order_id:
        graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((order_node, AZON.Nom, Literal(shipping["user_name"])))
    graph.add((order_node, AZON.Carrer, Literal(shipping["street_address"])))
    graph.add((order_node, AZON.Ciutat, Literal(shipping["city"])))
    graph.add((order_node, AZON.Prioritat, Literal(shipping["priority"])))
    for product in order["products"]:
        _add_product_reference(graph, order_node, product)


def build_peticio_compra(
    request_id,
    user_id,
    payment_method,
    shipping_data,
    product_ids,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[request_id]
    order_node = AZON[f"{request_id}-order"]

    graph.add((content, RDF.type, AZON.PeticioCompra))
    graph.add((content, AZON.IdUsuari, Literal(user_id)))
    graph.add((content, AZON.MetodePagament, Literal(payment_method)))
    graph.add((content, AZON.SobreComanda, order_node))

    _build_embedded_order(
        graph,
        order_node,
        {
            "user_id": user_id,
            "shipping_data": shipping_data,
            "products": [{"product_id": product_id} for product_id in product_ids],
        },
        include_order_id=False,
    )

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


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

    _build_embedded_order(graph, order_node, order, include_order_id=True)

    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.SobreProducte, product_node))

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
def parse_peticio_compra(graph, content):
    order_node = graph.value(content, AZON.SobreComanda)
    product_ids = []
    for product_node in graph.objects(order_node, AZON.TeProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))

    return {
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "payment_method": str(graph.value(content, AZON.MetodePagament)),
        "shipping_data": {
            "user_name": str(graph.value(order_node, AZON.Nom)),
            "street_address": str(graph.value(order_node, AZON.Carrer)),
            "city": str(graph.value(order_node, AZON.Ciutat)),
            "priority": str(graph.value(order_node, AZON.Prioritat)),
        },
        "product_ids": sorted(product_ids),
    }


def parse_peticio_registre_compra(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            local = str(product_node).rsplit("product-", 1)[-1]
            product_id = Literal(local)
        products.append({"product_id": str(product_id)})
    if not products:
        order_node = graph.value(content, AZON.SobreComanda)
        for product_node in graph.objects(order_node, AZON.TeProducte):
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


def build_confirmacio_enviament(order, shipping_details, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"shipping-confirmation-{order['order_id']}"]
    lot_node = AZON[f"lot-{shipping_details['lot_id']}"]
    transport_node = AZON[f"transport-{shipping_details['transport_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]

    graph.add((content, RDF.type, AZON.ConfirmacioEnviament))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.IdLot, Literal(shipping_details["lot_id"])))
    graph.add((content, AZON.IdTransportista, Literal(shipping_details["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(shipping_details["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(shipping_details["city"])))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(shipping_details["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(shipping_details["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    _build_embedded_order(graph, order_node, order, include_order_id=True)
    graph.add((order_node, AZON.MetodePagament, Literal(order["shipping_data"]["payment_method"])))
    graph.add((order_node, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.add((order_node, AZON.DataEntregaDefinitiva, Literal(shipping_details["delivery_date"])))
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
