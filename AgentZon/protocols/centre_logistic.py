"""Ontology-backed messages used during logistics and transport negotiation."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentZon.AgentUtil.ACL import ACL
from AgentZon.AgentUtil.ACLMessages import build_message, get_message_properties
from AgentZon.AgentUtil.OntoNamespaces import AGN, AZON, AZON_ONTOLOGY, bind_namespaces


def _product_node(product_id):
    return AZON[f"Producte-{product_id}"]


def _order_node(order_id):
    return AZON[f"Comanda-{order_id}"]


def _shipping_node(user_id):
    return AZON[f"DadesEnviament-{user_id}"]


def _lot_node(lot_id):
    return AZON[f"Lot-{lot_id}"]


def _transport_node(transport_id):
    return AZON[f"Transportista-{transport_id}"]


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
    content = AZON[f"ProducteLocalitzat-{order_id}"]
    order_node = _order_node(order_id)
    shipping_node = _shipping_node(user_id)
    graph.add((content, RDF.type, AZON.ProducteLocalitzat))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order_id)))
    graph.add((order_node, AZON.IdUsuari, Literal(user_id)))
    graph.add((order_node, AZON.TeDadesEnviament, shipping_node))
    graph.add((shipping_node, RDF.type, AZON.DadesEnviamentUsuari))
    graph.add((shipping_node, AZON.IdUsuari, Literal(user_id)))
    graph.add((shipping_node, AZON.Ciutat, Literal(city)))
    graph.add((shipping_node, AZON.Prioritat, Literal(priority)))
    for product in products:
        product_node = _product_node(product["product_id"])
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
        msgcnt=msgcnt,
        ontology=AZON_ONTOLOGY,
    )
    return message, content


def parse_productes_localitzats(graph, content):
    products = []
    order_node = graph.value(content, AZON.SobreComanda)
    shipping_node = graph.value(order_node, AZON.TeDadesEnviament)
    for node in graph.objects(content, AZON.TeProducte):
        products.append(
            {
                "product_id": str(graph.value(node, AZON.IdProducte)),
                "name": str(graph.value(node, AZON.Nom)),
                "weight": float(graph.value(node, AZON.Pes)),
            }
        )
    return {
        "order_id": str(graph.value(order_node, AZON.IdComanda)),
        "user_id": str(graph.value(order_node, AZON.IdUsuari)),
        "city": str(graph.value(shipping_node, AZON.Ciutat)),
        "priority": str(graph.value(shipping_node, AZON.Prioritat)),
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
    content = AZON[f"PeticioTransport-{lot_id}"]
    lot_node = _lot_node(lot_id)
    order_node = _order_node(order_id)
    graph.add((content, RDF.type, AZON.PeticioTransport))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((lot_node, RDF.type, AZON.Lot))
    graph.add((lot_node, AZON.IdLot, Literal(lot_id)))
    graph.add((lot_node, AZON.SobreComanda, order_node))
    graph.add((lot_node, AZON.Ciutat, Literal(city)))
    graph.add((lot_node, AZON.Prioritat, Literal(priority)))
    graph.add((lot_node, AZON.Pes, Literal(total_weight, datatype=XSD.float)))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order_id)))
    message = build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        msgcnt=msgcnt,
        ontology=AZON_ONTOLOGY,
    )
    return message, content


def parse_peticio_transport(graph, content):
    lot_node = graph.value(content, AZON.SobreLot)
    order_node = graph.value(lot_node, AZON.SobreComanda)
    return {
        "lot_id": str(graph.value(lot_node, AZON.IdLot)),
        "order_id": str(graph.value(order_node, AZON.IdComanda)),
        "city": str(graph.value(lot_node, AZON.Ciutat)),
        "priority": str(graph.value(lot_node, AZON.Prioritat)),
        "weight": float(graph.value(lot_node, AZON.Pes)),
    }


# Transport responses --------------------------------------------------------------
def build_resposta_oferta_transport(offer, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"RespostaOfertaTransport-{offer['transport_id']}-{offer['lot_id']}"]
    lot_node = _lot_node(offer["lot_id"])
    order_node = _order_node(offer.get("order_id", offer["lot_id"].replace("LOT-", "ORDER-")))
    transport_node = _transport_node(offer["transport_id"])
    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((content, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(offer["city"])))
    graph.add((content, AZON.DataEntrega, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((lot_node, RDF.type, AZON.Lot))
    graph.add((lot_node, AZON.IdLot, Literal(offer["lot_id"])))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(offer.get("order_id", offer["lot_id"].replace("LOT-", "ORDER-")))))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    graph.add((transport_node, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((transport_node, AZON.Nom, Literal(offer["transport_name"])))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.Transportista,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        msgcnt=msgcnt,
        ontology=AZON_ONTOLOGY,
    )


def extract_transport_offer(graph):
    props = get_message_properties(graph)
    content = props["content"]
    lot_node = graph.value(content, AZON.SobreLot)
    order_node = graph.value(content, AZON.SobreComanda)
    transport_node = graph.value(content, AZON.AssignatATransportista)
    return {
        "lot_id": str(graph.value(lot_node, AZON.IdLot)),
        "order_id": str(graph.value(order_node, AZON.IdComanda)),
        "transport_id": str(graph.value(transport_node, AZON.IdTransportista, default=graph.value(content, AZON.IdTransportista))),
        "transport_name": str(graph.value(transport_node, AZON.Nom, default=graph.value(content, AZON.NomTransportista))),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "price": float(graph.value(content, AZON.CostTransport)),
    }


def build_shipping_details_response(order_id, city, offer, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"RespostaOfertaTransport-Enviament-{order_id}"]
    lot_node = _lot_node(offer["lot_id"])
    order_node = _order_node(order_id)
    transport_node = _transport_node(offer["transport_id"])
    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((content, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(city)))
    graph.add((content, AZON.DataEntrega, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((lot_node, RDF.type, AZON.Lot))
    graph.add((lot_node, AZON.IdLot, Literal(offer["lot_id"])))
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order_id)))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    graph.add((transport_node, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((transport_node, AZON.Nom, Literal(offer["transport_name"])))
    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Compra,
        content=content,
        msgcnt=msgcnt,
        ontology=AZON_ONTOLOGY,
    )


def extract_shipping_details(graph):
    props = get_message_properties(graph)
    content = props["content"]
    order_node = graph.value(content, AZON.SobreComanda)
    lot_node = graph.value(content, AZON.SobreLot)
    transport_node = graph.value(content, AZON.AssignatATransportista)
    return {
        "order_id": str(graph.value(order_node, AZON.IdComanda)),
        "lot_id": str(graph.value(lot_node, AZON.IdLot)),
        "transport_id": str(graph.value(transport_node, AZON.IdTransportista, default=graph.value(content, AZON.IdTransportista))),
        "transport_name": str(graph.value(transport_node, AZON.Nom, default=graph.value(content, AZON.NomTransportista))),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "price": float(graph.value(content, AZON.CostTransport)),
    }
