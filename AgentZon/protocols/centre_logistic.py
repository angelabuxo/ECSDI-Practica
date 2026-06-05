"""Missatges de localitzacio de productes, transport, lots i seguiment d'enviament."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AGN, AZON, ONTOLOGY_URI, bind_namespaces
from protocols.pagament import embed_invoice_in_content, extract_invoice_from_content
from protocols.rdf_refs import (
    ensure_lot_node,
    ensure_order_node,
    ensure_transportista_node,
    link_product,
    lot_id_from_node,
    order_id_from_node,
    product_nodes_from_content,
    transport_id_from_node,
)


def _build_centre_node(graph, centre):
    if not centre or not centre.get("centre_id"):
        return None
    centre_node = AZON[f"centre-{centre['centre_id']}"]
    graph.add((centre_node, RDF.type, AZON.CentreLogistic))
    graph.add((centre_node, AZON.IdCentreLogistic, Literal(centre["centre_id"])))
    if centre.get("centre_city"):
        graph.add((centre_node, AZON.Ciutat, Literal(centre["centre_city"])))
    return centre_node


def _lot_order_id(lot):
    order_id = lot.get("order_id")
    if order_id is not None:
        return order_id
    return lot["lot_id"].replace("LOT-", "ORDER-")


def _add_product_to_graph(graph, subject, product, centre_node=None):
    product_node = AZON[f"product-{product['product_id']}"]
    link_product(graph, subject, product_node, product_kind="intern")
    graph.add((product_node, RDF.type, AZON.ProducteIntern))
    graph.add((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if "name" in product:
        graph.add((product_node, AZON.Nom, Literal(product["name"])))
    if "weight" in product:
        graph.add((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if "price" in product:
        graph.add((product_node, AZON.Preu, Literal(product["price"], datatype=XSD.float)))
    if centre_node is not None:
        graph.add((product_node, AZON.UbicatACentre, centre_node))
    return product_node


# Product localization -------------------------------------------------------------
def build_productes_localitzats(localized_item, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[localized_item["localized_product_id"]]
    centre = {
        "centre_id": localized_item.get("centre_id"),
        "centre_city": localized_item.get("centre_city"),
    }
    centre_node = _build_centre_node(graph, centre)
    product = localized_item["product"]

    graph.add((content, RDF.type, AZON.ProducteLocalitzat))
    graph.add((content, AZON.IdUsuari, Literal(localized_item["user_id"])))
    graph.add((content, AZON.Ciutat, Literal(localized_item["city"])))
    graph.add((content, AZON.DataEntrega, Literal(localized_item["delivery_date"])))
    _add_product_to_graph(graph, content, product, centre_node=centre_node)

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
    product = None
    centre_id = None
    centre_city = None
    for _, product_node in product_nodes_from_content(graph, content):
        weight_value = graph.value(product_node, AZON.Pes)
        price_value = graph.value(product_node, AZON.Preu)
        centre_node = graph.value(product_node, AZON.UbicatACentre)
        if centre_node is not None and centre_id is None:
            centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
            centre_city_value = graph.value(centre_node, AZON.Ciutat)
            centre_id = str(centre_id_value) if centre_id_value is not None else None
            centre_city = str(centre_city_value) if centre_city_value is not None else None
        product = {
            "product_id": str(graph.value(product_node, AZON.IdProducte)),
            "name": str(graph.value(product_node, AZON.Nom) or ""),
            "weight": float(weight_value) if weight_value is not None else 0.0,
            "price": float(price_value) if price_value is not None else 0.0,
        }
        break
    return {
        "localized_product_id": str(content).rsplit("#", 1)[-1],
        "user_id": str(graph.value(content, AZON.IdUsuari)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "product": product or {"product_id": "", "name": "", "weight": 0.0, "price": 0.0},
        "centre_id": centre_id,
        "centre_city": centre_city,
    }


def build_confirmacio_localitzacio(request_data, lot, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    localized_product_id = request_data["localized_product_id"]
    content = AZON[f"localization-confirmation-{localized_product_id}"]
    lot_node = ensure_lot_node(
        graph,
        lot["lot_id"],
        city=lot["city"],
        delivery_date=lot["delivery_date"],
        status=lot["status"],
        centre_id=lot.get("centre_id"),
    )
    ploc_node = AZON[localized_product_id]
    centre_node = _build_centre_node(graph, lot)

    graph.add((content, RDF.type, AZON.ConfirmacioLocalitzacio))
    graph.add((content, AZON.Estat, Literal(lot["status"])))
    graph.add((content, AZON.Ciutat, Literal(request_data["city"])))
    graph.add((content, AZON.DataEntrega, Literal(request_data["delivery_date"])))
    graph.add((content, AZON.SobreLot, lot_node))
    if request_data.get("user_id"):
        graph.add((content, AZON.IdUsuari, Literal(request_data["user_id"])))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    graph.add((ploc_node, RDF.type, AZON.ProducteLocalitzat))
    graph.add((ploc_node, AZON.SobreLot, lot_node))
    _add_product_to_graph(graph, ploc_node, request_data["product"], centre_node=centre_node)

    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Compra,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_confirmacio_localitzacio(graph):
    props = get_message_properties(graph)
    content = props["content"]
    request_content = graph.value(content, AZON.EsRespostaA)
    localized_product_id = str(request_content).rsplit("#", 1)[-1] if request_content is not None else None
    product = None
    centre_id = None
    centre_city = None
    product_source = request_content if request_content is not None else content
    for _, product_node in product_nodes_from_content(graph, product_source):
        weight_value = graph.value(product_node, AZON.Pes)
        price_value = graph.value(product_node, AZON.Preu)
        centre_node = graph.value(product_node, AZON.UbicatACentre)
        if centre_node is not None and centre_id is None:
            centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
            centre_city_value = graph.value(centre_node, AZON.Ciutat)
            centre_id = str(centre_id_value) if centre_id_value is not None else None
            centre_city = str(centre_city_value) if centre_city_value is not None else None
        product = {
            "product_id": str(graph.value(product_node, AZON.IdProducte)),
            "name": str(graph.value(product_node, AZON.Nom) or ""),
            "weight": float(weight_value) if weight_value is not None else 0.0,
            "price": float(price_value) if price_value is not None else 0.0,
        }
        break
    return {
        "localized_product_id": localized_product_id,
        "user_id": str(graph.value(content, AZON.IdUsuari) or ""),
        "lot_id": lot_id_from_node(graph, content),
        "status": str(graph.value(content, AZON.Estat)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "centre_id": centre_id,
        "centre_city": centre_city,
        "product": product or {"product_id": "", "name": "", "weight": 0.0, "price": 0.0},
    }


# Transport negotiation ------------------------------------------------------------
def build_peticio_transport(lot, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-request-{lot['lot_id']}"]
    order_id = _lot_order_id(lot)
    lot_node = ensure_lot_node(
        graph,
        lot["lot_id"],
        city=lot["city"],
        delivery_date=lot["delivery_date"],
    )
    order_node = ensure_order_node(graph, order_id)

    graph.add((content, RDF.type, AZON.PeticioTransport))
    graph.add((content, AZON.Ciutat, Literal(lot["city"])))
    graph.add((content, AZON.DataEntrega, Literal(lot["delivery_date"])))
    graph.add((content, AZON.PesTotal, Literal(lot["total_weight"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, order_node))

    message = build_message(
        graph,
        perf=ACL.cfp,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )
    return message, content


def parse_peticio_transport(graph, content):
    return {
        "lot_id": lot_id_from_node(graph, content),
        "order_id": order_id_from_node(graph, content),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "total_weight": float(graph.value(content, AZON.PesTotal)),
    }


# Transport responses --------------------------------------------------------------
def _build_transport_offer_content(graph, content, offer, city=None, price=None, request_content=None):
    order_id = offer.get("order_id", offer["lot_id"].replace("LOT-", "ORDER-"))
    lot_node = ensure_lot_node(graph, offer["lot_id"], city=city or offer.get("city"))
    order_node = ensure_order_node(graph, order_id)
    transport_node = ensure_transportista_node(
        graph,
        offer["transport_id"],
        offer["transport_name"],
    )

    graph.add((content, RDF.type, AZON.RespostaOfertaTransport))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(city or offer["city"])))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(price if price is not None else offer["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))
    return content


def build_resposta_oferta_transport(offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-offer-{offer['transport_id']}-{offer['lot_id']}"]
    _build_transport_offer_content(graph, content, offer, request_content=request_content)

    return build_message(
        graph,
        perf=ACL.propose,
        sender=sender or AGN.Transportista,
        receiver=receiver or AGN.CentreLogistic,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def build_contraoferta_transport(lot, offer, new_price, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-counter-{offer['transport_id']}-{lot['lot_id']}"]
    counter_offer = {
        **offer,
        "lot_id": lot["lot_id"],
        "order_id": _lot_order_id(lot),
        "city": lot["city"],
        "price": new_price,
    }
    _build_transport_offer_content(
        graph,
        content,
        counter_offer,
        city=lot["city"],
        price=new_price,
        request_content=request_content,
    )
    return build_message(
        graph,
        perf=ACL.propose,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_transport_offer(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {
        "lot_id": lot_id_from_node(graph, content),
        "order_id": order_id_from_node(graph, content),
        "transport_id": transport_id_from_node(graph, content),
        "transport_name": str(graph.value(content, AZON.NomTransportista)),
        "city": str(graph.value(content, AZON.Ciutat)),
        "delivery_date": str(graph.value(content, AZON.DataEntregaDefinitiva)),
        "price": float(graph.value(content, AZON.CostTransport)),
    }


def _build_transport_selection_message(
    lot,
    offer,
    perf,
    sender=None,
    receiver=None,
    request_content=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"transport-selection-{lot['lot_id']}"]
    order_id = _lot_order_id(lot)
    lot_node = ensure_lot_node(graph, lot["lot_id"], city=lot["city"])
    order_node = ensure_order_node(graph, order_id)
    transport_node = ensure_transportista_node(
        graph,
        offer["transport_id"],
        offer["transport_name"],
    )

    graph.add((content, RDF.type, AZON.EleccioTransportista))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(lot["city"])))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    return build_message(
        graph,
        perf=perf,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Transportista,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def build_eleccio_transportista(lot, offer, sender=None, receiver=None, request_content=None, msgcnt=0):
    return _build_transport_selection_message(
        lot,
        offer,
        ACL.request,
        sender=sender,
        receiver=receiver,
        request_content=request_content,
        msgcnt=msgcnt,
    )


def build_accept_transport_offer(lot, offer, sender=None, receiver=None, msgcnt=0):
    return _build_transport_selection_message(
        lot,
        offer,
        ACL["accept-proposal"],
        sender=sender,
        receiver=receiver,
        msgcnt=msgcnt,
    )


def build_reject_transport_offer(lot, offer, sender=None, receiver=None, msgcnt=0):
    return _build_transport_selection_message(
        lot,
        offer,
        ACL["reject-proposal"],
        sender=sender,
        receiver=receiver,
        msgcnt=msgcnt,
    )


def _build_shipping_update_response(
    response_type,
    item,
    offer,
    sender=None,
    receiver=None,
    request_content=None,
    invoice=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    localized_product_id = item["localized_product_id"]
    content = AZON[f"shipping-{localized_product_id}-{offer['lot_id']}"]
    lot_node = ensure_lot_node(
        graph,
        offer["lot_id"],
        city=item["city"],
        delivery_date=item["delivery_date"],
    )
    ploc_node = AZON[localized_product_id]
    transport_node = ensure_transportista_node(
        graph,
        offer["transport_id"],
        offer["transport_name"],
    )
    if item.get("order_id"):
        graph.add((content, AZON.SobreComanda, ensure_order_node(graph, item["order_id"])))
    centre_node = _build_centre_node(graph, item)
    product = item["product"]
    item_price = offer.get("price", 0.0)
    if isinstance(item_price, (int, float)) and offer.get("lot_transport_price") is not None:
        total_weight = float(offer.get("total_lot_weight") or product.get("weight") or 1.0)
        item_weight = float(product.get("weight") or 0.0)
        if total_weight and item_weight:
            item_price = round(float(offer["lot_transport_price"]) * item_weight / total_weight, 2)

    graph.add((content, RDF.type, response_type))
    graph.add((content, AZON.NomTransportista, Literal(offer["transport_name"])))
    graph.add((content, AZON.Ciutat, Literal(item["city"])))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
    graph.add((content, AZON.CostTransport, Literal(item_price, datatype=XSD.float)))
    graph.add((content, AZON.SobreLot, lot_node))
    graph.add((content, AZON.EsRespostaA, ploc_node))
    graph.add((content, AZON.AssignatATransportista, transport_node))
    graph.add((ploc_node, RDF.type, AZON.ProducteLocalitzat))
    graph.add((ploc_node, AZON.SobreLot, lot_node))
    _add_product_to_graph(graph, ploc_node, product, centre_node=centre_node)
    if invoice is not None:
        embed_invoice_in_content(graph, content, invoice)

    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender or AGN.CentreLogistic,
        receiver=receiver or AGN.Compra,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def build_dades_enviament(
    item,
    offer,
    sender=None,
    receiver=None,
    request_content=None,
    msgcnt=0,
):
    return _build_shipping_update_response(
        AZON.DadesEnviament,
        item,
        offer,
        sender=sender,
        receiver=receiver,
        request_content=request_content,
        msgcnt=msgcnt,
    )


def build_confirmacio_enviament(
    item,
    offer,
    sender=None,
    receiver=None,
    request_content=None,
    invoice=None,
    msgcnt=0,
):
    return _build_shipping_update_response(
        AZON.ConfirmacioEnviament,
        item,
        offer,
        sender=sender,
        receiver=receiver,
        request_content=request_content,
        invoice=invoice,
        msgcnt=msgcnt,
    )


def extract_shipping_details_list(graph):
    shipments = []
    contents = set(graph.subjects(RDF.type, AZON.DadesEnviament)) | set(
        graph.subjects(RDF.type, AZON.ConfirmacioEnviament)
    )
    for content in contents:
        lot_id = lot_id_from_node(graph, content)
        if not lot_id:
            continue

        ploc_node = graph.value(content, AZON.EsRespostaA)
        localized_product_id = str(ploc_node).rsplit("#", 1)[-1] if ploc_node is not None else None
        product = None
        centre_id = None
        centre_city = None
        product_source = ploc_node if ploc_node is not None else graph.value(content, AZON.SobreLot)
        if product_source is not None:
            for _, product_node in product_nodes_from_content(graph, product_source):
                product_id_value = graph.value(product_node, AZON.IdProducte)
                weight_value = graph.value(product_node, AZON.Pes)
                centre_node = graph.value(product_node, AZON.UbicatACentre)
                if centre_node is not None:
                    centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
                    centre_city_value = graph.value(centre_node, AZON.Ciutat)
                    centre_id = str(centre_id_value) if centre_id_value is not None else None
                    centre_city = str(centre_city_value) if centre_city_value is not None else None
                product = {
                    "product_id": str(product_id_value) if product_id_value is not None else None,
                    "name": str(graph.value(product_node, AZON.Nom) or product_id_value or ""),
                    "weight": float(weight_value) if weight_value is not None else 0.0,
                }
                break

        shipments.append(
            {
                "localized_product_id": localized_product_id,
                "lot_id": lot_id,
                "status": "ENVIAT" if (content, RDF.type, AZON.ConfirmacioEnviament) in graph else "ASSIGNAT",
                "transport_id": transport_id_from_node(graph, content),
                "transport_name": str(graph.value(content, AZON.NomTransportista)),
                "city": str(graph.value(content, AZON.Ciutat)),
                "delivery_date": str(graph.value(content, AZON.DataEntregaDefinitiva)),
                "price": float(graph.value(content, AZON.CostTransport)),
                "product": product,
                "centre_id": centre_id,
                "centre_city": centre_city,
            }
        )

    return sorted(
        shipments,
        key=lambda shipment: (
            shipment["localized_product_id"] or "",
            (shipment.get("product") or {}).get("product_id") or "",
            shipment["centre_id"] or "",
            shipment["lot_id"],
        ),
    )
