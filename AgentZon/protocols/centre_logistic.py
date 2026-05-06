"""Ontology-backed messages used during logistics and transport negotiation."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.OntoNamespaces import AGN, AZON, ONTOLOGY_URI, bind_namespaces


# Product localization -------------------------------------------------------------
def build_productes_localitzats(order, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"localized-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]

    graph.add((content, RDF.type, AZON.ProducteLocalitzat))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((content, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((content, AZON.Prioritat, Literal(order["shipping_data"]["priority"])))
    graph.add((content, AZON.SobreComanda, order_node))

    graph.add((order_node, RDF.type, AZON.Comanda))

    for product in order["products"]:
        product_node = AZON[f"product-{product['product_id']}"]
        graph.add((content, AZON.TeProducte, product_node))
        graph.add((order_node, AZON.TeProducte, product_node))
        graph.add((product_node, RDF.type, AZON.Producte))
        graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
        graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))

    message = build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.Compra,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )
    return message, content


def parse_productes_localitzats(graph, content):
    products = []
    for product_node in graph.objects(content, AZON.TeProducte):
        weight_value = graph.value(product_node, AZON.Pes)
        products.append(
            {
                "product_id": str(graph.value(product_node, AZON.IdProducte)),
                "name": str(graph.value(product_node, AZON.Nom)),
                "weight": float(weight_value) if weight_value is not None else 0.0,
            }
        )
    return {
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "priority": str(graph.value(content, AZON.Prioritat)),
        "products": products,
    }


# Transport negotiation ------------------------------------------------------------
def build_peticio_transport(lot, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-request-{lot['lot_id']}"]
    lot_node = AZON[f"lot-{lot['lot_id']}"]

    graph.add((content, RDF.type, AZON.PeticioTransport))
    graph.add((content, AZON.IdLot, Literal(lot["lot_id"])))
    graph.add((content, AZON.IdComanda, Literal(lot["order_id"])))
    graph.add((content, AZON.Ciutat, Literal(lot["city"])))
    graph.add((content, AZON.Prioritat, Literal(lot["priority"])))
    graph.add((content, AZON.PesTotal, Literal(lot["total_weight"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{lot['order_id']}"]))

    message = build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )
    return message, content


def parse_peticio_transport(graph, content):
    return {
        "lot_id": str(graph.value(content, AZON.IdLot)),
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "priority": str(graph.value(content, AZON.Prioritat)),
        "total_weight": float(graph.value(content, AZON.PesTotal)),
    }


# Transport responses --------------------------------------------------------------
def build_resposta_oferta_transport(offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-offer-{offer['transport_id']}-{offer['lot_id']}"]
    lot_node = AZON[f"lot-{offer['lot_id']}"]
    transport_node = AZON[f"transport-{offer['transport_id']}"]
    order_id = offer.get("order_id", offer["lot_id"].replace("LOT-", "ORDER-"))

    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.IdLot, Literal(offer["lot_id"])))
    graph.add((content, AZON.IdComanda, Literal(order_id)))
    graph.add((content, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(offer["city"])))
    graph.add((content, AZON.DataEntrega, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{order_id}"]))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.Transportista,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_transport_offer(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "lot_id": str(graph.value(content, AZON.IdLot)),
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "transport_id": str(graph.value(content, AZON.IdTransportista)),
        "transport_name": str(graph.value(content, AZON.NomTransportista)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "price": float(graph.value(content, AZON.CostTransport)),
    }


def build_shipping_details_response(order_id, city, offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    return build_resposta_oferta_transport(
        {
            "lot_id": offer["lot_id"],
            "order_id": order_id,
            "transport_id": offer["transport_id"],
            "transport_name": offer["transport_name"],
            "city": city,
            "delivery_date": offer["delivery_date"],
            "price": offer["price"],
        },
        sender=sender,
        receiver=receiver,
        request_content=request_content,
        msgcnt=msgcnt,
    )


def extract_shipping_details(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "lot_id": str(graph.value(content, AZON.IdLot)),
        "transport_id": str(graph.value(content, AZON.IdTransportista)),
        "transport_name": str(graph.value(content, AZON.NomTransportista)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "price": float(graph.value(content, AZON.CostTransport)),
    }
