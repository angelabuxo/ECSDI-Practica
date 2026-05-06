"""Ontology-backed messages used during logistics and transport negotiation."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.OntoNamespaces import AGN, AZON, bind_namespaces


# Product localization -------------------------------------------------------------
def build_productes_localitzats(
    order_id,
    user_id,
    city,
    priority,
    products,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"localized-{order_id}"]
    graph.add((content, RDF.type, AZON.ProducteLocalitzat))
    graph.add((content, AZON.idComanda, Literal(order_id)))
    graph.add((content, AZON.idUsuari, Literal(user_id)))
    graph.add((content, AZON.ciutat, Literal(city)))
    graph.add((content, AZON.prioritat, Literal(priority)))
    for product in products:
        product_node = AZON[f"localized-product-{order_id}-{product['product_id']}"]
        graph.add((content, AZON.teProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.idProducte, Literal(product["product_id"])))
        graph.add((product_node, AZON.nom, Literal(product["name"])))
        graph.add((product_node, AZON.pes, Literal(product["weight"], datatype=XSD.float)))
    message = build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.Compra,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        msgcnt=msgcnt,
    )
    return message, content


def parse_productes_localitzats(graph, content):
    products = []
    for node in graph.objects(content, AZON.teProducte):
        products.append(
            {
                "product_id": str(graph.value(node, AZON.idProducte)),
                "name": str(graph.value(node, AZON.nom)),
                "weight": float(graph.value(node, AZON.pes)),
            }
        )
    return {
        "order_id": str(graph.value(content, AZON.idComanda)),
        "user_id": str(graph.value(content, AZON.idUsuari)),
        "city": str(graph.value(content, AZON.ciutat)),
        "priority": str(graph.value(content, AZON.prioritat)),
        "products": products,
    }


# Transport negotiation ------------------------------------------------------------
def build_peticio_transport(
    lot_id,
    order_id,
    city,
    priority,
    total_weight,
    sender=None,
    receiver=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-request-{lot_id}"]
    graph.add((content, RDF.type, AZON.PeticioTransport))
    graph.add((content, AZON.idLot, Literal(lot_id)))
    graph.add((content, AZON.idComanda, Literal(order_id)))
    graph.add((content, AZON.ciutat, Literal(city)))
    graph.add((content, AZON.prioritat, Literal(priority)))
    graph.add((content, AZON.pes, Literal(total_weight, datatype=XSD.float)))
    message = build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        msgcnt=msgcnt,
    )
    return message, content


def parse_peticio_transport(graph, content):
    return {
        "lot_id": str(graph.value(content, AZON.idLot)),
        "order_id": str(graph.value(content, AZON.idComanda)),
        "city": str(graph.value(content, AZON.ciutat)),
        "priority": str(graph.value(content, AZON.prioritat)),
        "weight": float(graph.value(content, AZON.pes)),
    }


# Transport responses --------------------------------------------------------------
def build_resposta_oferta_transport(offer, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-offer-{offer['transport_id']}-{offer['lot_id']}"]
    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.idLot, Literal(offer["lot_id"])))
    graph.add((content, AZON.idComanda, Literal(offer.get("order_id", offer["lot_id"].replace("LOT-", "ORDER-")))))
    graph.add((content, AZON.idTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.nomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.ciutat, Literal(offer["city"])))
    graph.add((content, AZON.dataEntrega, Literal(offer["delivery_date"])))
    graph.add((content, AZON.costTransport, Literal(offer["price"], datatype=XSD.float)))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.Transportista,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        msgcnt=msgcnt,
    )


def extract_transport_offer(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "lot_id": str(graph.value(content, AZON.idLot)),
        "order_id": str(graph.value(content, AZON.idComanda)),
        "transport_id": str(graph.value(content, AZON.idTransportista)),
        "transport_name": str(graph.value(content, AZON.nomTransportista)),
        "city": str(graph.value(content, AZON.ciutat)),
        "delivery_date": str(graph.value(content, AZON.dataEntrega)),
        "price": float(graph.value(content, AZON.costTransport)),
    }


def build_shipping_details_response(order_id, city, offer, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"shipping-details-{order_id}"]
    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.idComanda, Literal(order_id)))
    graph.add((content, AZON.idLot, Literal(offer["lot_id"])))
    graph.add((content, AZON.idTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.nomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.ciutat, Literal(city)))
    graph.add((content, AZON.dataEntrega, Literal(offer["delivery_date"])))
    graph.add((content, AZON.costTransport, Literal(offer["price"], datatype=XSD.float)))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Compra,
        content=content,
        msgcnt=msgcnt,
    )


def extract_shipping_details(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "order_id": str(graph.value(content, AZON.idComanda)),
        "lot_id": str(graph.value(content, AZON.idLot)),
        "transport_id": str(graph.value(content, AZON.idTransportista)),
        "transport_name": str(graph.value(content, AZON.nomTransportista)),
        "city": str(graph.value(content, AZON.ciutat)),
        "delivery_date": str(graph.value(content, AZON.dataEntrega)),
        "price": float(graph.value(content, AZON.costTransport)),
    }
