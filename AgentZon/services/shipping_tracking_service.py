"""Persistencia del seguiment d'enviaments al costat de Compra."""

from rdflib import Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from protocols.pagament import embed_invoice_in_content, extract_invoice_from_content
from services.rdf_store import load_graph, save_graph


def _tracking_node(order_id, lot_id):
    return AZON[f"tracking-{order_id}-{lot_id}"]


def _add_product_reference(graph, subject, product, centre_node=None):
    product_node = AZON[f"product-{product['product_id']}"]
    graph.add((subject, AZON.TeProducte, product_node))
    graph.add((product_node, RDF.type, AZON.Producte))
    graph.set((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if product.get("name"):
        graph.set((product_node, AZON.Nom, Literal(product["name"])))
    if product.get("weight") is not None:
        graph.set((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if centre_node is not None:
        graph.add((product_node, AZON.UbicatACentre, centre_node))
    return product_node


def _ensure_centre_node(graph, centre_id=None, centre_city=None):
    if not centre_id:
        return None
    centre_node = AZON[f"centre-{centre_id}"]
    graph.add((centre_node, RDF.type, AZON.CentreLogistic))
    graph.set((centre_node, AZON.IdCentreLogistic, Literal(centre_id)))
    if centre_city:
        graph.set((centre_node, AZON.Ciutat, Literal(centre_city)))
    return centre_node


def save_localization_confirmations(tracking_path, reservations):
    graph = load_graph(tracking_path)
    bind_namespaces(graph)

    for reservation in reservations:
        node = _tracking_node(reservation["order_id"], reservation["lot_id"])
        order_node = AZON[f"order-{reservation['order_id']}"]
        lot_node = AZON[f"lot-{reservation['lot_id']}"]
        centre_node = _ensure_centre_node(
            graph,
            centre_id=reservation.get("centre_id"),
            centre_city=reservation.get("centre_city"),
        )

        graph.add((node, RDF.type, AZON.ConfirmacioLocalitzacio))
        graph.set((node, AZON.IdComanda, Literal(reservation["order_id"])))
        graph.set((node, AZON.IdLot, Literal(reservation["lot_id"])))
        graph.set((node, AZON.Estat, Literal(reservation.get("status", "OBERT"))))
        graph.set((node, AZON.Ciutat, Literal(reservation["city"])))
        graph.set((node, AZON.DataEntrega, Literal(reservation["delivery_date"])))
        graph.set((node, AZON.SobreComanda, order_node))
        graph.set((node, AZON.SobreLot, lot_node))

        for product in reservation.get("products", []):
            _add_product_reference(graph, node, product, centre_node=centre_node)

    save_graph(tracking_path, graph)


def apply_shipping_update(tracking_path, shipment, shipped=False, invoice=None):
    graph = load_graph(tracking_path)
    bind_namespaces(graph)

    node = _tracking_node(shipment["order_id"], shipment["lot_id"])
    order_node = AZON[f"order-{shipment['order_id']}"]
    lot_node = AZON[f"lot-{shipment['lot_id']}"]
    centre_node = _ensure_centre_node(
        graph,
        centre_id=shipment.get("centre_id"),
        centre_city=shipment.get("centre_city"),
    )

    graph.set((node, AZON.IdComanda, Literal(shipment["order_id"])))
    graph.set((node, AZON.IdLot, Literal(shipment["lot_id"])))
    graph.set((node, AZON.Ciutat, Literal(shipment["city"])))
    graph.set((node, AZON.SobreComanda, order_node))
    graph.set((node, AZON.SobreLot, lot_node))
    graph.set((node, AZON.IdTransportista, Literal(shipment["transport_id"])))
    graph.set((node, AZON.NomTransportista, Literal(shipment["transport_name"])))
    graph.set((node, AZON.DataEntregaDefinitiva, Literal(shipment["delivery_date"])))
    graph.set((node, AZON.CostTransport, Literal(shipment.get("price", 0.0), datatype=XSD.float)))
    graph.set((node, AZON.Estat, Literal("ENVIAT" if shipped else "ASSIGNAT")))

    graph.add((node, RDF.type, AZON.DadesEnviament))
    if shipped:
        graph.add((node, RDF.type, AZON.ConfirmacioEnviament))

    for product in shipment.get("products", []):
        _add_product_reference(graph, node, product, centre_node=centre_node)

    if invoice is not None:
        embed_invoice_in_content(graph, node, invoice)

    save_graph(tracking_path, graph)


def _load_tracking_entry(graph, node):
    product_nodes = list(graph.objects(node, AZON.TeProducte))
    centre_id = None
    centre_city = None
    products = []
    for product_node in product_nodes:
        centre_node = graph.value(product_node, AZON.UbicatACentre)
        if centre_node is not None and centre_id is None:
            centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
            centre_city_value = graph.value(centre_node, AZON.Ciutat)
            centre_id = str(centre_id_value) if centre_id_value is not None else None
            centre_city = str(centre_city_value) if centre_city_value is not None else None
        weight_value = graph.value(product_node, AZON.Pes)
        products.append(
            {
                "product_id": str(graph.value(product_node, AZON.IdProducte)),
                "name": str(graph.value(product_node, AZON.Nom) or ""),
                "weight": float(weight_value) if weight_value is not None else 0.0,
            }
        )

    explicit_status = graph.value(node, AZON.Estat)
    if (node, RDF.type, AZON.ConfirmacioEnviament) in graph:
        status = "ENVIAT"
    elif (node, RDF.type, AZON.DadesEnviament) in graph:
        status = "ASSIGNAT"
    else:
        status = str(explicit_status or "OBERT")

    official_delivery_date = graph.value(node, AZON.DataEntregaDefinitiva)
    transport_cost = graph.value(node, AZON.CostTransport)
    invoice = extract_invoice_from_content(graph, node)
    return {
        "order_id": str(graph.value(node, AZON.IdComanda)),
        "lot_id": str(graph.value(node, AZON.IdLot)),
        "status": status,
        "city": str(graph.value(node, AZON.Ciutat)),
        "delivery_date": str(official_delivery_date or graph.value(node, AZON.DataEntrega) or ""),
        "estimated_delivery_date": str(graph.value(node, AZON.DataEntrega) or ""),
        "official_delivery_date": str(official_delivery_date) if official_delivery_date is not None else None,
        "transport_id": str(graph.value(node, AZON.IdTransportista) or ""),
        "transport_name": str(graph.value(node, AZON.NomTransportista) or ""),
        "price": float(transport_cost) if transport_cost is not None else 0.0,
        "centre_id": centre_id,
        "centre_city": centre_city,
        "products": products,
        "product_id": products[0]["product_id"] if len(products) == 1 else None,
        "product_name": products[0]["name"] if len(products) == 1 else None,
        "invoice": invoice,
    }


def load_tracking_for_order(tracking_path, order_id):
    graph = load_graph(tracking_path)
    bind_namespaces(graph)
    entries = []
    for node in graph.subjects(AZON.IdComanda, Literal(order_id)):
        if graph.value(node, AZON.IdLot) is None:
            continue
        entries.append(_load_tracking_entry(graph, node))
    return sorted(entries, key=lambda entry: (entry["lot_id"], entry["order_id"]))


def _collect_shipped_product_ids(entries):
    shipped = set()
    for entry in entries:
        if entry.get("status") != "ENVIAT":
            continue
        for product in entry.get("products", []):
            product_id = product.get("product_id")
            if product_id:
                shipped.add(product_id)
    return shipped


def aggregate_order_status(entries, order_product_ids=None):
    if not entries:
        return "OBERT"

    expected = {product_id for product_id in (order_product_ids or []) if product_id}
    if expected:
        shipped = _collect_shipped_product_ids(entries)
        if shipped >= expected:
            return "ENVIAT"
        if shipped & expected:
            return "ASSIGNAT"

    statuses = {entry["status"] for entry in entries}
    if statuses == {"ENVIAT"}:
        return "ENVIAT"
    if statuses.issubset({"ASSIGNAT", "ENVIAT"}):
        return "ASSIGNAT"
    return "OBERT"


def aggregate_official_delivery_date(entries):
    official_dates = [entry["official_delivery_date"] for entry in entries if entry.get("official_delivery_date")]
    if len(official_dates) != len(entries):
        return None
    return max(official_dates) if official_dates else None
