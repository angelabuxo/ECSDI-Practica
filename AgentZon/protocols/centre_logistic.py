"""Missatges de localització de productes, transport, lots i confirmació d'enviament."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AGN, AZON, ONTOLOGY_URI, bind_namespaces
from protocols.pagament import embed_invoice_in_content, extract_invoice_from_content


def _build_centre_node(graph, centre):
    if not centre or not centre.get("centre_id"):
        return None
    centre_node = AZON[f"centre-{centre['centre_id']}"]
    graph.add((centre_node, RDF.type, AZON.CentreLogistic))
    graph.add((centre_node, AZON.IdCentreLogistic, Literal(centre["centre_id"])))
    if centre.get("centre_city"):
        graph.add((centre_node, AZON.Ciutat, Literal(centre["centre_city"])))
    return centre_node


def _add_product_to_graph(graph, subject, product, centre_node=None):
    product_node = AZON[f"product-{product['product_id']}"]
    graph.add((subject, AZON.TeProducte, product_node))
    graph.add((product_node, RDF.type, AZON.Producte))
    graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if "name" in product:
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
    if "weight" in product:
        graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if centre_node is not None:
        graph.add((product_node, AZON.UbicatACentre, centre_node))
    return product_node


# Product localization -------------------------------------------------------------
def build_productes_localitzats(order, products=None, centre=None, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    products = list(products or order["products"])
    content_suffix = (
        f"{order['order_id']}-{products[0]['product_id']}"
        if len(products) == 1
        else order["order_id"]
    )
    content = AZON[f"localized-{content_suffix}"]
    order_node = AZON[f"order-{order['order_id']}"]
    centre_node = _build_centre_node(graph, centre)

    graph.add((content, RDF.type, AZON.ProducteLocalitzat))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.IdUsuari, Literal(order["user_id"])))
    graph.add((content, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
    graph.add((content, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.add((content, AZON.SobreComanda, order_node))

    graph.add((order_node, RDF.type, AZON.Comanda))

    for product in products:
        product_node = _add_product_to_graph(graph, content, product, centre_node=centre_node)
        graph.add((order_node, AZON.TeProducte, product_node))

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
    centre_id = None
    centre_city = None
    for product_node in graph.objects(content, AZON.TeProducte):
        weight_value = graph.value(product_node, AZON.Pes)
        centre_node = graph.value(product_node, AZON.UbicatACentre)
        if centre_node is not None and centre_id is None:
            centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
            centre_city_value = graph.value(centre_node, AZON.Ciutat)
            centre_id = str(centre_id_value) if centre_id_value is not None else None
            centre_city = str(centre_city_value) if centre_city_value is not None else None
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
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "products": products,
        "centre_id": centre_id,
        "centre_city": centre_city,
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
    graph.add((content, AZON.DataEntrega, Literal(lot["delivery_date"])))
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
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
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
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
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
        "delivery_date": str(graph.value(content, AZON.DataEntregaDefinitiva)),
        "price": float(graph.value(content, AZON.CostTransport)),
    }


def build_eleccio_transportista(lot, offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-selection-{lot['lot_id']}"]
    lot_node = AZON[f"lot-{lot['lot_id']}"]
    transport_node = AZON[f"transport-{offer['transport_id']}"]

    graph.add((content, RDF.type, AZON.EleccioTransportista))
    graph.add((content, AZON.IdLot, Literal(lot["lot_id"])))
    graph.add((content, AZON.IdComanda, Literal(lot["order_id"])))
    graph.add((content, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(lot["city"])))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{lot['order_id']}"]))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    return build_message(
        graph,
        perf=ACL.request,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def build_shipping_details_response(
    request_data_or_order_id,
    city_or_offer,
    offer=None,
    sender=None,
    receiver=None,
    request_content=None,
    invoice=None,
    msgcnt=0,
):
    if isinstance(request_data_or_order_id, dict):
        request_data = request_data_or_order_id
        offer = city_or_offer
    else:
        request_data = {
            "order_id": request_data_or_order_id,
            "city": city_or_offer,
            "delivery_date": offer["delivery_date"],
            "products": [],
        }
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"shipping-confirmation-{request_data['order_id']}-{offer['lot_id']}"]
    lot_node = AZON[f"lot-{offer['lot_id']}"]
    transport_node = AZON[f"transport-{offer['transport_id']}"]
    centre_node = _build_centre_node(graph, request_data)

    graph.add((content, RDF.type, AZON.ConfirmacioEnviament))
    graph.add((content, AZON.IdComanda, Literal(request_data["order_id"])))
    graph.add((content, AZON.IdLot, Literal(offer["lot_id"])))
    graph.add((content, AZON.IdTransportista, Literal(offer["transport_id"])))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(request_data["city"])))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, AZON[f"order-{request_data['order_id']}"]))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((transport_node, RDF.type, AZON.Transportista))
    graph.add((lot_node, RDF.type, AZON.Lot))
    graph.add((lot_node, AZON.IdLot, Literal(offer["lot_id"])))
    graph.add((lot_node, AZON.Ciutat, Literal(request_data["city"])))
    graph.add((lot_node, AZON.DataEntrega, Literal(request_data["delivery_date"])))
    graph.add((lot_node, AZON.PesTotal, Literal(sum(product["weight"] for product in request_data["products"]), datatype=XSD.float)))
    graph.add((lot_node, AZON.SobreComanda, AZON[f"order-{request_data['order_id']}"]))
    for product in request_data["products"]:
        _add_product_to_graph(graph, lot_node, product, centre_node=centre_node)
    if invoice is not None:
        embed_invoice_in_content(graph, content, invoice)
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Compra,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_shipping_details_list(graph):
    shipments = []
    for content in set(graph.subjects(RDF.type, AZON.ConfirmacioEnviament)):
        lot_id = graph.value(content, AZON.IdLot)
        if lot_id is None:
            continue

        lot_node = graph.value(content, AZON.SobreLot)
        product_nodes = list(graph.objects(lot_node, AZON.TeProducte)) if lot_node is not None else []
        if not product_nodes:
            product_nodes = [None]

        for product_node in product_nodes:
            product_id = None
            centre_id = None
            centre_city = None
            if product_node is not None:
                product_id_value = graph.value(product_node, AZON.IdProducte)
                product_id = str(product_id_value) if product_id_value is not None else None
                centre_node = graph.value(product_node, AZON.UbicatACentre)
                if centre_node is not None:
                    centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
                    centre_city_value = graph.value(centre_node, AZON.Ciutat)
                    centre_id = str(centre_id_value) if centre_id_value is not None else None
                    centre_city = str(centre_city_value) if centre_city_value is not None else None

            shipments.append(
                {
                    "order_id": str(graph.value(content, AZON.IdComanda)),
                    "lot_id": str(lot_id),
                    "transport_id": str(graph.value(content, AZON.IdTransportista)),
                    "transport_name": str(graph.value(content, AZON.NomTransportista)),
                    "city": str(graph.value(content, AZON.Ciutat)),
                    "delivery_date": str(graph.value(content, AZON.DataEntregaDefinitiva)),
                    "price": float(graph.value(content, AZON.CostTransport)),
                    "product_id": product_id,
                    "centre_id": centre_id,
                    "centre_city": centre_city,
                }
            )

    return sorted(
        shipments,
        key=lambda shipment: (
            shipment["product_id"] or "",
            shipment["centre_id"] or "",
            shipment["lot_id"],
        ),
    )


def extract_shipping_details(graph):
    shipments = extract_shipping_details_list(graph)
    if not shipments:
        raise ValueError("Shipping confirmation does not contain shipment details")
    details = shipments[0]
    props = get_message_properties(graph)
    content = props["content"]
    invoice = extract_invoice_from_content(graph, content)
    if invoice is not None:
        details["invoice"] = invoice
    return details
