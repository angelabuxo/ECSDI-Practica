"""Resums d'enviament, facturacio agregada i coordinacio amb centres logistics."""

from concurrent.futures import ThreadPoolExecutor

from rdflib import Graph, RDF

from AgentUtil.ACLMessages import get_message_properties
from AgentUtil.OntoNamespaces import AZON
from protocols.centre_logistic import (
    build_productes_localitzats,
    extract_shipping_details_list,
    parse_confirmacio_localitzacio,
)
from protocols.pagament import extract_invoice_from_content


def extract_centre_reservations_from_reply(reply):
    if isinstance(reply, Graph):
        reply_graph = reply
    else:
        reply_graph = Graph()
        reply_graph.parse(data=reply, format="xml")

    properties = get_message_properties(reply_graph)
    if not properties:
        return []
    content = properties["content"]
    if (content, RDF.type, AZON.ConfirmacioLocalitzacio) in reply_graph:
        return [parse_confirmacio_localitzacio(reply_graph)]
    return []


def extract_centre_shipments_from_reply(reply):
    if isinstance(reply, Graph):
        reply_graph = reply
    else:
        reply_graph = Graph()
        reply_graph.parse(data=reply, format="xml")
    properties = get_message_properties(reply_graph)
    shipments = extract_shipping_details_list(reply_graph)
    if properties:
        invoice = extract_invoice_from_content(reply_graph, properties["content"])
        if invoice is not None and shipments:
            shipments[0]["invoice"] = invoice
    return shipments


def _shipment_bundle_key(shipment):
    centre_id = shipment.get("centre_id") or ""
    lot_id = shipment.get("lot_id") or ""
    if centre_id or lot_id:
        return f"{centre_id}:{lot_id}"
    return shipment.get("product_id") or ""


def mark_shared_transport_costs(shipments):
    seen_bundles = set()
    normalized = []
    for shipment in shipments:
        bundle_key = _shipment_bundle_key(shipment)
        if bundle_key and bundle_key in seen_bundles:
            normalized.append({**shipment, "price": 0.0, "shared_transport": True})
            continue
        if bundle_key:
            seen_bundles.add(bundle_key)
        normalized.append(shipment)
    return normalized


def sum_unique_lot_transport_cost(shipments):
    seen_bundles = set()
    total = 0.0
    for shipment in shipments:
        bundle_key = _shipment_bundle_key(shipment)
        if bundle_key:
            if bundle_key in seen_bundles:
                continue
            seen_bundles.add(bundle_key)
        total += shipment.get("price", 0.0)
    return round(total, 2)


def build_invoice_summary(order, shipments):
    lines = sorted(
        [
            {"product_id": product["product_id"], "name": product["name"], "price": product["price"]}
            for product in order["products"]
        ],
        key=lambda line: line["product_id"],
    )
    shipment_invoices = [shipment["invoice"] for shipment in shipments if shipment.get("invoice")]
    fallback_products_subtotal = round(sum(line["price"] for line in lines), 2)
    fallback_transport_cost = sum_unique_lot_transport_cost(shipments)

    if not shipment_invoices:
        return {
            "payment_id": "PENDENT",
            "order_id": order["order_id"],
            "amount": round(fallback_products_subtotal + fallback_transport_cost, 2),
            "method": order["shipping_data"]["payment_method"],
            "payment_status": "PENDENT",
            "date": "",
            "lines": lines,
            "transport_cost": fallback_transport_cost,
            "products_subtotal": fallback_products_subtotal,
        }

    payment_ids = sorted({invoice["payment_id"] for invoice in shipment_invoices if invoice.get("payment_id")})
    statuses = sorted({invoice["status"] for invoice in shipment_invoices if invoice.get("status")})
    methods = sorted({invoice["method"] for invoice in shipment_invoices if invoice.get("method")})
    dates = sorted({invoice["date"] for invoice in shipment_invoices if invoice.get("date")})
    products_subtotal = round(sum(invoice.get("products_subtotal", 0.0) for invoice in shipment_invoices), 2)
    transport_cost = round(sum(invoice.get("transport_cost", 0.0) for invoice in shipment_invoices), 2)
    amount = round(sum(invoice.get("amount", 0.0) for invoice in shipment_invoices), 2)

    if not products_subtotal:
        products_subtotal = fallback_products_subtotal
    if not transport_cost:
        transport_cost = fallback_transport_cost
    if not amount:
        amount = round(products_subtotal + transport_cost, 2)

    return {
        "payment_id": ", ".join(payment_ids) if payment_ids else "PENDENT",
        "order_id": order["order_id"],
        "amount": amount,
        "method": methods[0] if len(methods) == 1 else order["shipping_data"]["payment_method"],
        "payment_status": ", ".join(statuses) if statuses else "PENDENT",
        "date": ", ".join(dates),
        "lines": lines,
        "transport_cost": transport_cost,
        "products_subtotal": products_subtotal,
    }


def _status_rank(status):
    return {
        "OBERT": 0,
        "PREPARAT": 1,
        "NEGOCIANT": 2,
        "ASSIGNAT": 3,
        "ENVIAT": 4,
    }.get(status or "OBERT", 0)


def group_shipments_for_display(shipments):
    groups = {}
    group_order = []
    for shipment in shipments:
        centre_id = shipment.get("centre_id") or ""
        lot_id = shipment.get("lot_id") or ""
        group_key = f"{centre_id}:{lot_id}" if centre_id or lot_id else shipment.get("order_id") or ""
        if group_key not in groups:
            groups[group_key] = {
                "lot_id": lot_id,
                "centre_id": shipment.get("centre_id"),
                "centre_city": shipment.get("centre_city"),
                "transport_id": shipment.get("transport_id"),
                "transport_name": shipment.get("transport_name"),
                "city": shipment.get("city"),
                "delivery_date": shipment.get("delivery_date"),
                "estimated_delivery_date": shipment.get("estimated_delivery_date") or shipment.get("delivery_date"),
                "official_delivery_date": shipment.get("official_delivery_date"),
                "delivery_is_official": bool(shipment.get("official_delivery_date")),
                "status": shipment.get("status", "OBERT"),
                "transport_cost": 0.0,
                "products": [],
            }
            group_order.append(group_key)
        group = groups[group_key]
        if _status_rank(shipment.get("status")) > _status_rank(group["status"]):
            group["status"] = shipment.get("status")
        if shipment.get("official_delivery_date"):
            group["delivery_date"] = shipment["official_delivery_date"]
            group["official_delivery_date"] = shipment["official_delivery_date"]
            group["delivery_is_official"] = True
        if shipment.get("transport_id"):
            group["transport_id"] = shipment.get("transport_id")
        if shipment.get("transport_name"):
            group["transport_name"] = shipment.get("transport_name")
        for product in shipment.get("products", []):
            group["products"].append(
                {
                    "product_id": product.get("product_id"),
                    "product_name": product.get("name") or product.get("product_id"),
                }
            )
        if not shipment.get("shared_transport"):
            group["transport_cost"] = max(group["transport_cost"], float(shipment.get("price", 0.0)))
    for index, group_key in enumerate(group_order, start=1):
        groups[group_key]["index"] = index
        groups[group_key]["shared_shipment"] = len(groups[group_key]["products"]) > 1
    return [groups[group_key] for group_key in group_order]


def aggregate_order_status(shipments):
    """Estat global de la comanda segons els enviaments mostrats al resum.

    ENVIAT només quan tots els grans d'enviament (centre + lot) estan ENVIAT.
    """
    shipment_groups = group_shipments_for_display(shipments)
    if not shipment_groups:
        return "OBERT"

    statuses = [group.get("status", "OBERT") for group in shipment_groups]
    if all(status == "ENVIAT" for status in statuses):
        return "ENVIAT"
    if any(status == "ENVIAT" for status in statuses):
        return "ASSIGNAT"
    if all(status == "ASSIGNAT" for status in statuses):
        return "ASSIGNAT"
    return "OBERT"


def fulfill_centre_group(order, group, sender_uri, message_sender, next_msgcnt):
    selected_centre = group["centre"]
    centre_products = group["products"]
    message, _ = build_productes_localitzats(
        order,
        products=centre_products,
        centre=selected_centre,
        sender=sender_uri,
        receiver=selected_centre["uri"],
        msgcnt=next_msgcnt(),
    )
    reply = message_sender(message, selected_centre["address"])
    reservations = []
    for reservation in extract_centre_reservations_from_reply(reply):
        reservations.append(
            {
                **reservation,
                "centre_id": reservation.get("centre_id") or selected_centre.get("centre_id"),
                "centre_city": reservation.get("centre_city") or selected_centre.get("centre_city"),
            }
        )
    return reservations


def collect_warehouse_reservations(order, centre_groups, sender_uri, message_sender, next_msgcnt):
    if not centre_groups:
        return []

    def dispatch_group(group):
        return fulfill_centre_group(order, group, sender_uri, message_sender, next_msgcnt)

    if len(centre_groups) == 1:
        reservations = dispatch_group(centre_groups[0])
    else:
        reservations = []
        with ThreadPoolExecutor(max_workers=len(centre_groups)) as executor:
            for group_reservations in executor.map(dispatch_group, centre_groups):
                reservations.extend(group_reservations)
    return reservations


