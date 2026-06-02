"""Persistencia del seguiment d'enviaments al costat de Compra."""

from rdflib import Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from protocols.pagament import embed_invoice_in_content, extract_invoice_from_content
from services.rdf_store import load_graph, save_graph


def _tracking_node(localized_product_id):
    return AZON[f"tracking-{localized_product_id}"]


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


def save_localization_confirmations(tracking_path, items):
    graph = load_graph(tracking_path)
    bind_namespaces(graph)

    for item in items:
        localized_product_id = item["localized_product_id"]
        node = _tracking_node(localized_product_id)
        order_node = AZON[f"order-{item['order_id']}"]
        lot_node = AZON[f"lot-{item['lot_id']}"]
        centre_node = _ensure_centre_node(
            graph,
            centre_id=item.get("centre_id"),
            centre_city=item.get("centre_city"),
        )
        product = item["product"]

        graph.add((node, RDF.type, AZON.ConfirmacioLocalitzacio))
        graph.set((node, AZON.IdComanda, Literal(item["order_id"])))
        graph.set((node, AZON.IdLot, Literal(item["lot_id"])))
        graph.set((node, AZON.Estat, Literal(item.get("status", "OBERT"))))
        graph.set((node, AZON.Ciutat, Literal(item["city"])))
        graph.set((node, AZON.DataEntrega, Literal(item["delivery_date"])))
        graph.set((node, AZON.SobreComanda, order_node))
        graph.set((node, AZON.SobreLot, lot_node))
        if product.get("product_id"):
            _add_product_reference(graph, node, product, centre_node=centre_node)

    save_graph(tracking_path, graph)


def lookup_order_for_localized_product(tracking_path, localized_product_id):
    graph = load_graph(tracking_path)
    bind_namespaces(graph)
    node = _tracking_node(localized_product_id)
    order_id = graph.value(node, AZON.IdComanda)
    return str(order_id) if order_id is not None else None


def apply_shipping_update(tracking_path, shipment, shipped=False, invoice=None):
    graph = load_graph(tracking_path)
    bind_namespaces(graph)

    localized_product_id = shipment["localized_product_id"]
    node = _tracking_node(localized_product_id)
    order_id = shipment.get("order_id") or graph.value(node, AZON.IdComanda)
    if order_id is None:
        raise KeyError(f"No order mapping for localized product {localized_product_id}")
    order_node = AZON[f"order-{order_id}"]
    lot_node = AZON[f"lot-{shipment['lot_id']}"]
    centre_node = _ensure_centre_node(
        graph,
        centre_id=shipment.get("centre_id"),
        centre_city=shipment.get("centre_city"),
    )

    graph.set((node, AZON.IdComanda, Literal(str(order_id))))
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

    product = shipment.get("product")
    if product and product.get("product_id"):
        _add_product_reference(graph, node, product, centre_node=centre_node)

    if invoice is not None:
        embed_invoice_in_content(graph, node, invoice)

    save_graph(tracking_path, graph)


def _load_tracking_entry(graph, node):
    product_nodes = list(graph.objects(node, AZON.TeProducte))
    centre_id = None
    centre_city = None
    product = None
    for product_node in product_nodes:
        centre_node = graph.value(product_node, AZON.UbicatACentre)
        if centre_node is not None and centre_id is None:
            centre_id_value = graph.value(centre_node, AZON.IdCentreLogistic)
            centre_city_value = graph.value(centre_node, AZON.Ciutat)
            centre_id = str(centre_id_value) if centre_id_value is not None else None
            centre_city = str(centre_city_value) if centre_city_value is not None else None
        weight_value = graph.value(product_node, AZON.Pes)
        product = {
            "product_id": str(graph.value(product_node, AZON.IdProducte)),
            "name": str(graph.value(product_node, AZON.Nom) or ""),
            "weight": float(weight_value) if weight_value is not None else 0.0,
        }
        break

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
    localized_product_id = str(node).rsplit("tracking-", 1)[-1]
    return {
        "localized_product_id": localized_product_id,
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
        "product": product,
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
    return sorted(entries, key=lambda entry: (entry["lot_id"], entry["localized_product_id"]))


def aggregate_official_delivery_date(entries):
    official_dates = [entry["official_delivery_date"] for entry in entries if entry.get("official_delivery_date")]
    if len(official_dates) != len(entries):
        return None
    return max(official_dates) if official_dates else None
