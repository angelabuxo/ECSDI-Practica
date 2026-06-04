"""Extracció d'identificadors i enllaços de producte via relacions RDF."""

from rdflib import Literal, RDF

from AgentUtil.OntoNamespaces import AZON


def order_id_from_node(graph, content):
    order_node = graph.value(content, AZON.SobreComanda)
    if order_node is not None:
        order_id = graph.value(order_node, AZON.IdComanda)
        if order_id is not None:
            return str(order_id)
        node_name = str(order_node).rsplit("order-", 1)[-1]
        if node_name and node_name != str(order_node):
            return node_name
    legacy = graph.value(content, AZON.IdComanda)
    return str(legacy) if legacy is not None else ""


def lot_id_from_node(graph, content):
    lot_node = graph.value(content, AZON.SobreLot)
    if lot_node is not None:
        lot_id = graph.value(lot_node, AZON.IdLot)
        if lot_id is not None:
            return str(lot_id)
        node_name = str(lot_node).rsplit("lot-", 1)[-1]
        if node_name and node_name != str(lot_node):
            return node_name
    legacy = graph.value(content, AZON.IdLot)
    return str(legacy) if legacy is not None else ""


def transport_id_from_node(graph, content):
    transport_node = graph.value(content, AZON.AssignatATransportista)
    if transport_node is not None:
        transport_id = graph.value(transport_node, AZON.IdTransportista)
        if transport_id is not None:
            return str(transport_id)
        node_name = str(transport_node).rsplit("transport-", 1)[-1]
        if node_name and node_name != str(transport_node):
            return node_name
    legacy = graph.value(content, AZON.IdTransportista)
    return str(legacy) if legacy is not None else ""


def product_nodes_from_content(graph, content):
    for prop in (AZON.TeProducteExtern, AZON.TeProducteIntern, AZON.TeProducte):
        for product_node in graph.objects(content, prop):
            yield prop, product_node


def first_product_node(graph, content):
    for _, product_node in product_nodes_from_content(graph, content):
        return product_node
    return None


def link_product(graph, subject, product_node, product_kind="generic"):
    if product_kind == "extern":
        graph.add((subject, AZON.TeProducteExtern, product_node))
    elif product_kind == "intern":
        graph.add((subject, AZON.TeProducteIntern, product_node))
    else:
        graph.add((subject, AZON.TeProducte, product_node))


def ensure_transportista_node(graph, transport_id, transport_name=None):
    transport_node = AZON[f"transport-{transport_id}"]
    graph.add((transport_node, RDF.type, AZON.Transportista))
    graph.add((transport_node, AZON.IdTransportista, Literal(str(transport_id))))
    if transport_name:
        graph.add((transport_node, AZON.NomTransportista, Literal(transport_name)))
    return transport_node


def ensure_lot_node(graph, lot_id, city=None, delivery_date=None, status=None, centre_id=None):
    lot_node = AZON[f"lot-{lot_id}"]
    graph.add((lot_node, RDF.type, AZON.Lot))
    graph.add((lot_node, AZON.IdLot, Literal(lot_id)))
    if city is not None:
        graph.add((lot_node, AZON.Ciutat, Literal(city)))
    if delivery_date is not None:
        graph.add((lot_node, AZON.DataEntrega, Literal(delivery_date)))
    if status is not None:
        graph.add((lot_node, AZON.Estat, Literal(status)))
    if centre_id is not None:
        graph.add((lot_node, AZON.IdCentreLogistic, Literal(centre_id)))
    return lot_node


def ensure_order_node(graph, order_id):
    order_node = AZON[f"order-{order_id}"]
    graph.add((order_node, RDF.type, AZON.Comanda))
    graph.add((order_node, AZON.IdComanda, Literal(order_id)))
    return order_node


def link_sobre_comanda(graph, subject, order_id):
    order_node = ensure_order_node(graph, order_id)
    graph.add((subject, AZON.SobreComanda, order_node))
    return order_node


def link_sobre_lot(graph, subject, lot_id, **lot_fields):
    lot_node = ensure_lot_node(graph, lot_id, **lot_fields)
    graph.add((subject, AZON.SobreLot, lot_node))
    return lot_node


def link_assignat_transportista(graph, subject, transport_id, transport_name=None):
    transport_node = ensure_transportista_node(graph, transport_id, transport_name)
    graph.add((subject, AZON.AssignatATransportista, transport_node))
    return transport_node
