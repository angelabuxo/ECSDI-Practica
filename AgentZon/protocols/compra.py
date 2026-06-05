"""Missatges de compra, resultat de compra i registre d'historial de compres."""

from rdflib import Graph, Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.ACL import ACL
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces
from protocols.rdf_refs import (
    _user_id_from_iri,
    ensure_lot_node,
    link_product,
    link_sobre_comanda,
    lot_id_from_node,
    order_id_from_node,
    product_nodes_from_content,
)


def _add_product_reference(graph, subject, product):
    product_node = AZON[f"product-{product['product_id']}"]
    product_kind = "extern" if product.get("seller_id") else "generic"
    product_type = AZON.ProducteExtern if product_kind == "extern" else AZON.Producte
    link_product(graph, subject, product_node, product_kind=product_kind)
    graph.add((product_node, RDF.type, product_type))
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
    if product.get("seller_id"):
        graph.add((product_node, AZON.IdVenedorExtern, Literal(product["seller_id"])))
    if "requires_external_logistics" in product:
        graph.add(
            (
                product_node,
                AZON.RequereixLogisticaExterna,
                Literal(bool(product["requires_external_logistics"]), datatype=XSD.boolean),
            )
        )
    return product_node


def _build_embedded_order(graph, order_node, order, include_order_id):
    shipping = order["shipping_data"]
    graph.add((order_node, RDF.type, AZON.Comanda))
    if include_order_id:
        graph.add((order_node, AZON.IdComanda, Literal(order["order_id"])))
    graph.add((order_node, AZON.PertanyAUsuari, AZON["usuari-" + str(order["user_id"])]))
    graph.add((order_node, AZON.Nom, Literal(shipping["user_name"])))
    graph.add((order_node, AZON.Carrer, Literal(shipping["street_address"])))
    graph.add((order_node, AZON.Ciutat, Literal(shipping["city"])))
    graph.add((order_node, AZON.Prioritat, Literal(shipping["priority"])))
    payment_method = shipping.get("payment_method")
    if payment_method:
        graph.add((order_node, AZON.MetodePagament, Literal(payment_method)))
    delivery_date = order.get("delivery_date")
    if delivery_date:
        graph.add((order_node, AZON.DataEntrega, Literal(delivery_date)))
    purchase_date = order.get("purchase_date")
    if purchase_date:
        graph.add((order_node, AZON.DataCompra, Literal(purchase_date)))
    final_delivery_date = order.get("final_delivery_date")
    if final_delivery_date:
        graph.add((order_node, AZON.DataEntregaDefinitiva, Literal(final_delivery_date)))
    status = order.get("status")
    if status:
        graph.add((order_node, AZON.Estat, Literal(status)))
    for product in order["products"]:
        _add_product_reference(graph, order_node, product)


def extract_order_snapshot(graph, order_node):
    products = []
    seen_product_ids = set()
    for _, product_node in product_nodes_from_content(graph, order_node):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_id = str(product_id)
        seen_product_ids.add(product_id)
        product = {"product_id": product_id}
        name = graph.value(product_node, AZON.Nom)
        description = graph.value(product_node, AZON.Descripcio)
        category = graph.value(product_node, AZON.Categoria)
        brand = graph.value(product_node, AZON.Marca)
        price = graph.value(product_node, AZON.Preu)
        weight = graph.value(product_node, AZON.Pes)
        if name is not None:
            product["name"] = str(name)
        if description is not None:
            product["description"] = str(description)
        if category is not None:
            product["category"] = str(category)
        if brand is not None:
            product["brand"] = str(brand)
        if price is not None:
            product["price"] = float(price)
        if weight is not None:
            product["weight"] = float(weight)
        seller_id = graph.value(product_node, AZON.IdVenedorExtern)
        if seller_id is not None:
            product["seller_id"] = str(seller_id)
        requires_external = graph.value(product_node, AZON.RequereixLogisticaExterna)
        if requires_external is not None:
            product["requires_external_logistics"] = bool(requires_external.toPython())
        products.append(product)

    for product_node in graph.objects(order_node, AZON.TeProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_id = str(product_id)
        if product_id in seen_product_ids:
            continue
        products.append({"product_id": product_id})
        seen_product_ids.add(product_id)

    final_delivery_date = graph.value(order_node, AZON.DataEntregaDefinitiva)
    purchase_date = graph.value(order_node, AZON.DataCompra)
    status = graph.value(order_node, AZON.Estat)
    return {
        "order_id": order_id_from_node(graph, order_node),
        "user_id": _user_id_from_iri(graph.value(order_node, AZON.PertanyAUsuari)),
        "user_name": str(graph.value(order_node, AZON.Nom)),
        "purchase_date": str(purchase_date) if purchase_date is not None else None,
        "delivery_date": str(graph.value(order_node, AZON.DataEntrega) or ""),
        "final_delivery_date": str(final_delivery_date) if final_delivery_date is not None else None,
        "status": str(status) if status is not None else "",
        "product_ids": sorted(product["product_id"] for product in products),
        "products": products,
        "shipping_data": {
            "user_name": str(graph.value(order_node, AZON.Nom)),
            "street_address": str(graph.value(order_node, AZON.Carrer) or ""),
            "city": str(graph.value(order_node, AZON.Ciutat) or ""),
            "priority": str(graph.value(order_node, AZON.Prioritat) or ""),
            "payment_method": str(graph.value(order_node, AZON.MetodePagament) or ""),
            "user_id": _user_id_from_iri(graph.value(order_node, AZON.PertanyAUsuari)),
        },
    }


def _extract_centre_metadata(graph, subject):
    centre_id = None
    centre_city = None
    for _, product_node in product_nodes_from_content(graph, subject):
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
    graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(user_id)]))
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
    graph.add((content, AZON.PertanyAUsuari, AZON["usuari-" + str(order["user_id"])]))
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
    for _, product_node in product_nodes_from_content(graph, order_node):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            product_id = Literal(str(product_node).rsplit("product-", 1)[-1])
        product_ids.append(str(product_id))

    return {
        "user_id": _user_id_from_iri(graph.value(content, AZON.PertanyAUsuari)),
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
    order_node = graph.value(content, AZON.SobreComanda)
    parsed = extract_order_snapshot(graph, order_node)
    if parsed["products"]:
        return parsed

    products = []
    for product_node in graph.objects(content, AZON.SobreProducte):
        product_id = graph.value(product_node, AZON.IdProducte)
        if product_id is None:
            local = str(product_node).rsplit("product-", 1)[-1]
            product_id = Literal(local)
        products.append({"product_id": str(product_id)})
    return {**parsed, "products": products, "product_ids": sorted(product["product_id"] for product in products)}


def build_peticio_registre_producte_extern_compra(payload, sender=None, receiver=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-product-compra-{payload['product_id']}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.PeticioRegistreProducteExternCompra))
    graph.add((content, AZON.IdProducte, Literal(payload["product_id"])))
    graph.add((content, AZON.IdVenedorExtern, Literal(payload["seller_id"])))
    graph.add(
        (
            content,
            AZON.RequereixLogisticaExterna,
            Literal(bool(payload["requires_external_logistics"]), datatype=XSD.boolean),
        )
    )
    if payload.get("centre_id"):
        graph.add((content, AZON.IdCentreLogistic, Literal(payload["centre_id"])))
    return build_message(
        graph,
        perf=ACL.request,
        sender=sender,
        receiver=receiver,
        content=content,
        ontology=ONTOLOGY_URI,
        msgcnt=msgcnt,
    )


def parse_peticio_registre_producte_extern_compra(graph, content=None):
    if content is None:
        props = get_message_properties(graph)
        content = props["content"]
    requires_external = graph.value(content, AZON.RequereixLogisticaExterna)
    centre_id = graph.value(content, AZON.IdCentreLogistic)
    return {
        "product_id": str(graph.value(content, AZON.IdProducte)),
        "seller_id": str(graph.value(content, AZON.IdVenedorExtern)),
        "requires_external_logistics": bool(requires_external.toPython()) if requires_external is not None else False,
        "centre_id": str(centre_id) if centre_id is not None else "",
    }


def build_confirmacio_registre_producte_extern_compra(
    product_id,
    sender=None,
    receiver=None,
    request_content=None,
    msgcnt=0,
):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"external-product-compra-confirmation-{product_id}-{msgcnt}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreProducteExternCompra))
    graph.add((content, AZON.IdProducte, Literal(product_id)))
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


def parse_confirmacio_registre_producte_extern_compra(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return {"product_id": str(graph.value(content, AZON.IdProducte))}


def build_confirmacio_registre_compra(order_id, sender=None, receiver=None, request_content=None, msgcnt=0):
    graph = Graph()
    bind_namespaces(graph)
    content = AZON[f"history-confirmation-{order_id}"]
    graph.add((content, RDF.type, AZON.ConfirmacioRegistreCompra))
    link_sobre_comanda(graph, content, order_id)
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
    graph.add((content, AZON.DataEntrega, Literal(order["delivery_date"])))
    graph.add((content, AZON.SobreComanda, order_node))
    if request_content is not None:
        graph.add((content, AZON.EsRespostaA, request_content))

    _build_embedded_order(graph, order_node, order, include_order_id=True)
    graph.add((order_node, AZON.MetodePagament, Literal(order["shipping_data"]["payment_method"])))
    graph.add((order_node, AZON.DataEntrega, Literal(order["delivery_date"])))

    for reservation in reservations:
        shipment_node = AZON[f"tracking-{reservation['localized_product_id']}"]
        centre_node = None
        if reservation.get("centre_id"):
            centre_node = AZON[f"centre-{reservation['centre_id']}"]
            graph.add((centre_node, RDF.type, AZON.CentreLogistic))
            graph.add((centre_node, AZON.IdCentreLogistic, Literal(reservation["centre_id"])))
            if reservation.get("centre_city"):
                graph.add((centre_node, AZON.Ciutat, Literal(reservation["centre_city"])))

        lot_node = ensure_lot_node(
            graph,
            reservation["lot_id"],
            city=reservation["city"],
            delivery_date=reservation["delivery_date"],
            status=reservation.get("status", "OBERT"),
            centre_id=reservation.get("centre_id"),
        )

        graph.add((shipment_node, RDF.type, AZON.ConfirmacioLocalitzacio))
        graph.add((shipment_node, AZON.Estat, Literal(reservation.get("status", "OBERT"))))
        graph.add((shipment_node, AZON.Ciutat, Literal(reservation["city"])))
        graph.add((shipment_node, AZON.DataEntrega, Literal(reservation["delivery_date"])))
        graph.add((shipment_node, AZON.SobreComanda, order_node))
        graph.add((shipment_node, AZON.SobreLot, lot_node))

        product = reservation.get("product")
        if product:
            product_node = _add_product_reference(graph, shipment_node, product)
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
        product = None
        for _, product_node in product_nodes_from_content(graph, reservation_node):
            weight_value = graph.value(product_node, AZON.Pes)
            product = {
                "product_id": str(graph.value(product_node, AZON.IdProducte)),
                "name": str(graph.value(product_node, AZON.Nom) or ""),
                "weight": float(weight_value) if weight_value is not None else 0.0,
            }
            break
        centre_id, centre_city = _extract_centre_metadata(graph, reservation_node)
        lots.append(
            {
                "lot_id": lot_id_from_node(graph, reservation_node),
                "status": str(graph.value(reservation_node, AZON.Estat)),
                "city": str(graph.value(reservation_node, AZON.Ciutat)),
                "delivery_date": str(graph.value(reservation_node, AZON.DataEntrega)),
                "centre_id": centre_id,
                "centre_city": centre_city,
                "product": product,
                "lot_node": str(lot_node) if lot_node is not None else None,
            }
        )

    official_delivery_date = graph.value(content, AZON.DataEntregaDefinitiva)
    return {
        "order_id": order_id_from_node(graph, content),
        "estimated_delivery_date": str(graph.value(content, AZON.DataEntrega)),
        "official_delivery_date": str(official_delivery_date) if official_delivery_date is not None else None,
        "lots": lots,
    }


def extract_registration_confirmation(graph):
    props = get_message_properties(graph)
    content = props["content"]
    return order_id_from_node(graph, content)
