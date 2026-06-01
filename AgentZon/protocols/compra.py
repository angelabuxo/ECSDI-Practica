"""Missatges de compra, resultat de compra i registre d'historial de compres."""

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


def _extract_centre_metadata(graph, subject):
    centre_id = None
    centre_city = None
    for product_node in graph.objects(subject, AZON.TeProducte):
        centre_node = graph.value(product_node, AZON.UbicatACentre)
        if centre_node is None:
            continue
        centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
        centre_city_value = graph.value(centre_node, AZON.Ciutat)
        centre_id = str(centre_id_value) if centre_id_value is not None else None
        centre_city = str(centre_city_value) if centre_city_value is not None else None
        break
    return centre_id, centre_city


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


def build_resultat_compra(order, reservations, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"purchase-result-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]

    graph.add((content, RDF.type, AZON.ResultatCompra))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.Estat, Literal(order.get("status", "OBERT"))))
    graph.add((content, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.add((content, AZON.SobreComanda, order_node))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    _build_embedded_order(graph, order_node, order, include_order_id=True)
    graph.add((order_node, AZON.MetodePagament, Literal(order["shipping_data"]["payment_method"])))
    graph.add((order_node, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.add((order_node, AZON.Estat, Literal(order.get("status", "OBERT"))))

    for reservation in reservations:
        shipment_node = AZON[f"reservation-{reservation['order_id']}-{reservation['lot_id']}"]
        lot_node = AZON[f"lot-{reservation['lot_id']}"]
        centre_node = None
        if reservation.get("centre_id"):
            centre_node = AZON[f"centre-{reservation['centre_id']}"]
            graph.add((centre_node, RDF.type, AZON.CentreLogistic))
            graph.add((centre_node, AZON.IdCentreLogistic, Literal(reservation["centre_id"])))
            if reservation.get("centre_city"):
                graph.add((centre_node, AZON.Ciutat, Literal(reservation["centre_city"])))

        graph.add((shipment_node, RDF.type, AZON.ConfirmacioLocalitzacio))
        graph.add((shipment_node, AZON.IdComanda, Literal(reservation["order_id"])))
        graph.add((shipment_node, AZON.IdLot, Literal(reservation["lot_id"])))
        graph.add((shipment_node, AZON.Estat, Literal(reservation.get("status", "OBERT"))))
        graph.add((shipment_node, AZON.Ciutat, Literal(reservation["city"])))
        graph.add((shipment_node, AZON.DataEntrega, Literal(reservation["delivery_date"])))
        graph.add((shipment_node, AZON.SobreComanda, order_node))
        graph.add((shipment_node, AZON.SobreLot, lot_node))

        graph.add((lot_node, RDF.type, AZON.Lot))
        graph.add((lot_node, AZON.IdLot, Literal(reservation["lot_id"])))
        graph.add((lot_node, AZON.Ciutat, Literal(reservation["city"])))
        graph.add((lot_node, AZON.DataEntrega, Literal(reservation["delivery_date"])))
        graph.add((lot_node, AZON.Estat, Literal(reservation.get("status", "OBERT"))))
        if reservation.get("centre_id"):
            graph.add((lot_node, AZON.IdCentreLogistic, Literal(reservation["centre_id"])))

        for product in reservation.get("products", []):
            product_node = _add_product_reference(graph, shipment_node, product)
            graph.add((lot_node, AZON.TeProducte, product_node))
            if centre_node is not None:
                graph.add((product_node, AZON.UbicatACentre, centre_node))

    return build_message(
        graph,
        perf=ACL.inform,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def extract_resultat_compra(graph):
    props = get_message_properties(graph)
    content = props["content"]
    lots = []

    for reservation_node in sorted(set(graph.subjects(RDF.type, AZON.ConfirmacioLocalitzacio)), key=str):
        lot_node = graph.value(reservation_node, AZON.SobreLot)
        products = []
        for product_node in graph.objects(reservation_node, AZON.TeProducte):
            weight_value = graph.value(product_node, AZON.Pes)
            products.append(
                {
                    "product_id": str(graph.value(product_node, AZON.IdProducte)),
                    "name": str(graph.value(product_node, AZON.Nom) or ""),
                    "weight": float(weight_value) if weight_value is not None else 0.0,
                }
            )
        centre_id, centre_city = _extract_centre_metadata(graph, reservation_node)
        lots.append(
            {
                "lot_id": str(graph.value(reservation_node, AZON.IdLot)),
                "status": str(graph.value(reservation_node, AZON.Estat)),
                "city": str(graph.value(reservation_node, AZON.Ciutat)),
                "delivery_date": str(graph.value(reservation_node, AZON.DataEntrega)),
                "centre_id": centre_id,
                "centre_city": centre_city,
                "products": products,
                "lot_node": str(lot_node) if lot_node is not None else None,
            }
        )

    official_delivery_date = graph.value(content, AZON.DataEntregaDefinitiva)
    return {
        "order_id": str(graph.value(content, AZON.IdComanda)),
        "status": str(graph.value(content, AZON.Estat)),
        "estimated_delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "official_delivery_date": str(official_delivery_date) if official_delivery_date is not None else None,
        "lots": lots,
    }


def _build_centre_node(graph, shipment):
    centre_id = shipment.get("centre_id")
    if not centre_id:
        return None
    centre_node = AZON[f"centre-{centre_id}"]
    graph.add((centre_node, RDF.type, AZON.CentreLogistic))
    graph.add((centre_node, AZON.IdCentreLogistic, Literal(centre_id)))
    if shipment.get("centre_city"):
        graph.add((centre_node, AZON.Ciutat, Literal(shipment["centre_city"])))
    return centre_node


def _group_shipments_by_lot(shipments):
    grouped = {}
    lot_order = []
    for shipment in shipments:
        lot_id = shipment.get("lot_id")
        centre_id = shipment.get("centre_id") or ""
        if lot_id and centre_id:
            group_key = f"{centre_id}:{lot_id}"
        else:
            group_key = lot_id or shipment.get("product_id") or f"shipment-{len(lot_order)}"
        if group_key not in grouped:
            grouped[group_key] = []
            lot_order.append(group_key)
        grouped[group_key].append(shipment)
    return [grouped[lot_key] for lot_key in lot_order]


def build_confirmacio_enviament(order, shipping_details, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"shipping-confirmation-{order['order_id']}"]
    order_node = AZON[f"order-{order['order_id']}"]
    shipments = shipping_details if isinstance(shipping_details, list) else [shipping_details]
    final_delivery_date = max(shipment["delivery_date"] for shipment in shipments)
    products_by_id = {product["product_id"]: product for product in order["products"]}

    graph.add((content, RDF.type, AZON.ConfirmacioEnviament))
    graph.add((content, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((content, AZON.SobreComanda, order_node))
    graph.add((content, AZON.DataEntregaDefinitiva, Literal(final_delivery_date)))
    _build_embedded_order(graph, order_node, order, include_order_id=True)
    graph.add((order_node, AZON.MetodePagament, Literal(order["shipping_data"]["payment_method"])))
    graph.add((order_node, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.add((order_node, AZON.DataEntregaDefinitiva, Literal(final_delivery_date)))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    for index, lot_shipments in enumerate(_group_shipments_by_lot(shipments), start=1):
        shipment = lot_shipments[0]
        shipment_key = shipment.get("lot_id") or shipment.get("product_id") or f"shipment-{index}"
        shipment_node = AZON[f"shipping-confirmation-{order['order_id']}-{shipment_key}"]
        lot_node = AZON[f"lot-{shipment['lot_id']}"]
        transport_node = AZON[f"transport-{shipment['transport_id']}"]
        centre_node = _build_centre_node(graph, shipment)
        transport_price = max(item.get("price", 0.0) for item in lot_shipments)

        graph.add((shipment_node, RDF.type, AZON.ConfirmacioEnviament))
        graph.add((shipment_node, AZON.IdComanda, Literal(order["order_id"])))
        graph.add((shipment_node, AZON.IdLot, Literal(shipment["lot_id"])))
        graph.add((shipment_node, AZON.IdTransportista, Literal(shipment["transport_id"])))
        graph.add((shipment_node, AZON.NomTransportista, Literal(shipment["transport_name"])))
        graph.add((shipment_node, AZON.Ciutat, Literal(shipment["city"])))
        graph.add((shipment_node, AZON.DataEntregaDefinitiva, Literal(shipment["delivery_date"])))
        graph.add((shipment_node, AZON.CostTransport, Literal(transport_price, datatype=XSD.float)))
        graph.add((shipment_node, AZON.SobreLot, lot_node))
        graph.add((shipment_node, AZON.SobreComanda, order_node))
        graph.add((shipment_node, AZON.AssignatATransportista, transport_node))
        graph.add((transport_node, RDF.type, AZON.Transportista))
        graph.add((lot_node, RDF.type, AZON.Lot))
        graph.add((lot_node, AZON.IdLot, Literal(shipment["lot_id"])))
        graph.add((lot_node, AZON.Ciutat, Literal(order["shipping_data"]["city"])))
        graph.add((lot_node, AZON.SobreComanda, order_node))
        if request_content is not None:
            graph.add((shipment_node, AZON.EsRespostaA, request_content))

        for lot_shipment in lot_shipments:
            product_id = lot_shipment.get("product_id")
            if not product_id:
                continue
            product = products_by_id.get(product_id, {"product_id": product_id})
            product_node = _add_product_reference(graph, lot_node, product)
            if centre_node is not None:
                graph.add((product_node, AZON.UbicatACentre, centre_node))

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
