"""Creacio de lots, negociacio amb transportistes i cicle de vida del centre logistic."""

from datetime import date, timedelta
import random
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4

from rdflib import Literal, RDF
from rdflib.namespace import XSD

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from config import MAX_LOT_WEIGHT_KG, READY_DELIVERY_WINDOW_DAYS
from services.rdf_store import load_graph, save_graph


LOT_LOCK = Lock()


def _parse_date(value):
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    return date.fromisoformat(text)


def _localized_product_node(localized_product_id):
    return AZON[localized_product_id]


def _find_lot_node_by_id(graph, lot_id):
    for lot_node in graph.subjects(RDF.type, AZON.Lot):
        if str(graph.value(lot_node, AZON.IdLot)) == lot_id:
            return lot_node
    raise KeyError(f"Lot {lot_id} does not exist")


def _get_lot_status(graph, lot_node):
    status = graph.value(lot_node, AZON.Estat)
    return str(status) if status is not None else "OBERT"


def _set_lot_status(graph, lot_node, status):
    graph.set((lot_node, AZON.Estat, Literal(status)))


def _item_nodes_for_lot(graph, lot_node):
    return sorted(
        {
            item_node
            for item_node in graph.subjects(AZON.SobreLot, lot_node)
            if (item_node, RDF.type, AZON.ProducteLocalitzat) in graph
        },
        key=str,
    )


def _ensure_centre_node(graph, centre_id=None, centre_city=None):
    if not centre_id:
        return None
    centre_node = AZON[f"centre-{centre_id}"]
    graph.add((centre_node, RDF.type, AZON.CentreLogistic))
    graph.set((centre_node, AZON.IdCentreLogistic, Literal(centre_id)))
    if centre_city:
        graph.set((centre_node, AZON.Ciutat, Literal(centre_city)))
    return centre_node


def _lookup_centre_city(graph, centre_id):
    if not centre_id:
        return None
    centre_node = AZON[f"centre-{centre_id}"]
    centre_city = graph.value(centre_node, AZON.Ciutat)
    return str(centre_city) if centre_city is not None else None


def _find_open_lot_node(graph, city, delivery_date, centre_id=None):
    for lot_node in graph.subjects(RDF.type, AZON.Lot):
        if _get_lot_status(graph, lot_node) != "OBERT":
            continue
        if str(graph.value(lot_node, AZON.Ciutat)) != city:
            continue
        if str(graph.value(lot_node, AZON.DataEntrega)) != delivery_date:
            continue
        if centre_id:
            lot_centre_id = graph.value(lot_node, AZON.IdCentreLogistic)
            if lot_centre_id is not None and str(lot_centre_id) != centre_id:
                continue
        return lot_node
    return None


def _add_product_reference(graph, subject, product, centre_node=None):
    product_node = AZON[f"product-{product['product_id']}"]
    graph.add((subject, AZON.TeProducte, product_node))
    graph.add((product_node, RDF.type, AZON.Producte))
    graph.set((product_node, AZON.IdProducte, Literal(product["product_id"])))
    if "name" in product:
        graph.set((product_node, AZON.Nom, Literal(product["name"])))
    if "weight" in product:
        graph.set((product_node, AZON.Pes, Literal(product["weight"], datatype=XSD.float)))
    if centre_node is not None:
        graph.add((product_node, AZON.UbicatACentre, centre_node))
    return product_node


def _localized_product_id_from_node(item_node):
    return str(item_node).rsplit("#", 1)[-1]


def _read_item(graph, item_node):
    lot_node = graph.value(item_node, AZON.SobreLot)
    lot_id = graph.value(lot_node, AZON.IdLot) if lot_node is not None else None
    user_id = graph.value(item_node, AZON.IdUsuari)
    centre_id_value = graph.value(lot_node, AZON.IdCentreLogistic) if lot_node is not None else None
    centre_id = str(centre_id_value) if centre_id_value is not None else None
    centre_city = _lookup_centre_city(graph, centre_id)

    product = None
    for product_node in graph.objects(item_node, AZON.TeProducte):
        weight_value = graph.value(product_node, AZON.Pes)
        product = {
            "product_id": str(graph.value(product_node, AZON.IdProducte)),
            "name": str(graph.value(product_node, AZON.Nom) or ""),
            "weight": float(weight_value) if weight_value is not None else 0.0,
        }
        break

    return {
        "localized_product_id": _localized_product_id_from_node(item_node),
        "user_id": str(user_id) if user_id is not None else None,
        "lot_id": str(lot_id) if lot_id is not None else None,
        "city": str(graph.value(item_node, AZON.Ciutat) or graph.value(lot_node, AZON.Ciutat) or ""),
        "delivery_date": str(
            graph.value(item_node, AZON.DataEntrega) or graph.value(lot_node, AZON.DataEntrega) or ""
        ),
        "centre_id": centre_id,
        "centre_city": centre_city,
        "product": product or {"product_id": "", "name": "", "weight": 0.0},
    }


def _extract_lot(graph, lot_node):
    lot_id = str(graph.value(lot_node, AZON.IdLot))
    centre_id_value = graph.value(lot_node, AZON.IdCentreLogistic)
    centre_id = str(centre_id_value) if centre_id_value is not None else None
    items = [_read_item(graph, item_node) for item_node in _item_nodes_for_lot(graph, lot_node)]
    official_delivery_date = graph.value(lot_node, AZON.DataEntregaDefinitiva)
    price_value = graph.value(lot_node, AZON.CostTransport)

    return {
        "lot_id": lot_id,
        "city": str(graph.value(lot_node, AZON.Ciutat)),
        "delivery_date": str(graph.value(lot_node, AZON.DataEntrega)),
        "official_delivery_date": str(official_delivery_date) if official_delivery_date is not None else None,
        "total_weight": float(graph.value(lot_node, AZON.PesTotal) or 0.0),
        "status": _get_lot_status(graph, lot_node),
        "transport_id": str(graph.value(lot_node, AZON.IdTransportista) or ""),
        "transport_name": str(graph.value(lot_node, AZON.NomTransportista) or ""),
        "price": float(price_value) if price_value is not None else 0.0,
        "centre_id": centre_id,
        "centre_city": _lookup_centre_city(graph, centre_id),
        "products": [item["product"] for item in items],
        "items": items,
    }


# Lot persistence ------------------------------------------------------------------
def create_lot(lots_path, item):
    """Persist one localized product item into an open or new lot."""
    product = item["product"]
    incoming_weight = round(float(product["weight"]), 2)
    city = item["city"]
    delivery_date = item["delivery_date"]
    centre_id = item.get("centre_id")
    centre_city = item.get("centre_city")

    with LOT_LOCK:
        graph = load_graph(lots_path)
        bind_namespaces(graph)
        centre_node = _ensure_centre_node(graph, centre_id=centre_id, centre_city=centre_city)

        lot_node = _find_open_lot_node(graph, city, delivery_date, centre_id=centre_id)
        created_new_lot = lot_node is None
        if created_new_lot:
            lot_id = f"LOT-{uuid4().hex[:6].upper()}"
            lot_node = AZON[f"lot-{lot_id}"]
            graph.add((lot_node, RDF.type, AZON.Lot))
            graph.add((lot_node, AZON.IdLot, Literal(lot_id)))
            graph.add((lot_node, AZON.Ciutat, Literal(city)))
            graph.add((lot_node, AZON.DataEntrega, Literal(delivery_date)))
            if centre_id:
                graph.set((lot_node, AZON.IdCentreLogistic, Literal(centre_id)))
            total_weight = 0.0
        else:
            lot_id = str(graph.value(lot_node, AZON.IdLot))
            total_weight = float(graph.value(lot_node, AZON.PesTotal) or 0.0)

        item_node = _localized_product_node(item["localized_product_id"])
        graph.add((item_node, RDF.type, AZON.ProducteLocalitzat))
        graph.set((item_node, AZON.SobreLot, lot_node))
        if item.get("user_id"):
            graph.set((item_node, AZON.IdUsuari, Literal(item["user_id"])))
        graph.set((item_node, AZON.Ciutat, Literal(city)))
        graph.set((item_node, AZON.DataEntrega, Literal(delivery_date)))
        _add_product_reference(graph, item_node, product, centre_node=centre_node)
        total_weight = round(total_weight + incoming_weight, 2)
        graph.set((lot_node, AZON.PesTotal, Literal(total_weight, datatype=XSD.float)))
        status = "PREPARAT" if total_weight >= MAX_LOT_WEIGHT_KG else "OBERT"
        _set_lot_status(graph, lot_node, status)
        save_graph(lots_path, graph)

        lot = _extract_lot(graph, lot_node)
        lot["localized_product_id"] = item["localized_product_id"]
        lot["user_id"] = item.get("user_id")
        lot["product"] = dict(product)
        lot["created_new_lot"] = created_new_lot
        lot["ready_for_negotiation"] = status == "PREPARAT"
        return lot


def load_lot_by_id(lots_path, lot_id):
    graph = load_graph(lots_path)
    bind_namespaces(graph)
    return _extract_lot(graph, _find_lot_node_by_id(graph, lot_id))


def list_ready_lots_for_negotiation(
    lots_path,
    today=None,
    delivery_window_days=READY_DELIVERY_WINDOW_DAYS,
):
    today = today or date.today()
    cutoff = today + timedelta(days=delivery_window_days)

    with LOT_LOCK:
        graph = load_graph(lots_path)
        bind_namespaces(graph)
        changed = False
        ready_lots = []

        for lot_node in graph.subjects(RDF.type, AZON.Lot):
            status = _get_lot_status(graph, lot_node)
            if status == "OBERT":
                delivery_value = _parse_date(graph.value(lot_node, AZON.DataEntrega))
                if delivery_value is not None and delivery_value <= cutoff:
                    _set_lot_status(graph, lot_node, "PREPARAT")
                    status = "PREPARAT"
                    changed = True
            if status == "PREPARAT":
                ready_lots.append(_extract_lot(graph, lot_node))

        if changed:
            save_graph(lots_path, graph)

    return sorted(ready_lots, key=lambda lot: (lot["delivery_date"], lot["lot_id"]))


def mark_lot_negotiating(lots_path, lot_id):
    with LOT_LOCK:
        graph = load_graph(lots_path)
        bind_namespaces(graph)
        lot_node = _find_lot_node_by_id(graph, lot_id)
        if _get_lot_status(graph, lot_node) != "PREPARAT":
            return None
        _set_lot_status(graph, lot_node, "NEGOCIANT")
        save_graph(lots_path, graph)
        return _extract_lot(graph, lot_node)


def assign_transport_to_lot(lots_path, lot_id, offer):
    with LOT_LOCK:
        graph = load_graph(lots_path)
        bind_namespaces(graph)
        lot_node = _find_lot_node_by_id(graph, lot_id)
        transport_node = AZON[f"transport-{offer['transport_id']}"]
        graph.add((transport_node, RDF.type, AZON.Transportista))
        graph.set((lot_node, AZON.AssignatATransportista, transport_node))
        graph.set((lot_node, AZON.IdTransportista, Literal(offer["transport_id"])))
        graph.set((lot_node, AZON.NomTransportista, Literal(offer["transport_name"])))
        graph.set((lot_node, AZON.DataEntregaDefinitiva, Literal(offer["delivery_date"])))
        graph.set((lot_node, AZON.CostTransport, Literal(offer["price"], datatype=XSD.float)))
        _set_lot_status(graph, lot_node, "ASSIGNAT")
        save_graph(lots_path, graph)
        return _extract_lot(graph, lot_node)


def mark_lot_shipped(lots_path, lot_id):
    with LOT_LOCK:
        graph = load_graph(lots_path)
        bind_namespaces(graph)
        lot_node = _find_lot_node_by_id(graph, lot_id)
        _set_lot_status(graph, lot_node, "ENVIAT")
        save_graph(lots_path, graph)
        return _extract_lot(graph, lot_node)


# Offer evaluation -----------------------------------------------------------------
PREMIUM_COUNTER_FACTOR = 1.10
PREMIUM_PRICE_CAP_FACTOR = 1.15


def _offer_rank_key(offer):
    return (offer["price"], offer["delivery_date"], offer["transport_id"])


def split_low_and_high_offers(offers):
    """Classifica ofertes inicials en oferta baixa (mínim preu) i alta (màxim preu)."""
    if not offers:
        return None, None
    if len(offers) == 1:
        return offers[0], None
    low_offer = min(offers, key=_offer_rank_key)
    high_offer = max(offers, key=_offer_rank_key)
    return low_offer, high_offer


def build_premium_counter_price(low_offer):
    return round(low_offer["price"] * PREMIUM_COUNTER_FACTOR, 2)


def build_premium_price_cap(low_offer):
    return round(low_offer["price"] * PREMIUM_PRICE_CAP_FACTOR, 2)


def build_counter_offer_price(offers, decrement=0.01):
    """Mantingut per compatibilitat de tests antics; no s'usa en la negociació premium."""
    return round(min(offer["price"] for offer in offers) - decrement, 2)


def _acl_performative_name(performative):
    if performative is None:
        return None
    return str(performative).rsplit("#", 1)[-1]


def select_offer_after_premium_negotiation(
    low_offer,
    high_offer,
    *,
    counter_price=None,
    cap_price=None,
    premium_performative=None,
    premium_negotiated_offer=None,
):
    """Aplica la política 110 % / 115 % sobre l'oferta baixa."""
    if low_offer is None:
        return dict(high_offer) if high_offer is not None else None
    if high_offer is None:
        return dict(low_offer)

    performative_name = _acl_performative_name(premium_performative)
    if performative_name == "agree" and counter_price is not None and counter_price <= cap_price:
        return {**high_offer, "price": counter_price}
    if (
        performative_name == "propose"
        and premium_negotiated_offer is not None
        and premium_negotiated_offer["price"] <= cap_price
    ):
        return dict(premium_negotiated_offer)
    return dict(low_offer)


def choose_winning_offer(initial_offers, negotiated_offers, chooser=random.choice):
    candidate_pool = negotiated_offers or initial_offers
    cheapest_price = min(offer["price"] for offer in candidate_pool)
    cheapest_offers = [offer for offer in candidate_pool if offer["price"] == cheapest_price]
    ordered_offers = sorted(
        cheapest_offers,
        key=lambda offer: (offer["delivery_date"], offer["transport_id"]),
    )
    return chooser(ordered_offers)


def choose_best_offer(offers):
    return choose_winning_offer(offers, [], chooser=lambda candidates: candidates[0])


def format_centre_uri_name(centre_id):
    return f"CentreLogistic{''.join(ch for ch in centre_id if ch.isalnum())}"


def query_transport_offers(lot, transport_agents, request_offer):
    """Query transport agents in parallel. request_offer(agent) returns an offer or None."""

    with ThreadPoolExecutor(max_workers=len(transport_agents)) as executor:
        futures = [executor.submit(request_offer, agent) for agent in transport_agents]
        return [offer for future in futures if (offer := future.result()) is not None]


def match_transport_agent(transport_agents, transport_id):
    return next(
        agent
        for agent in transport_agents
        if agent.name.endswith(transport_id) or transport_id in agent.name.lower()
    )


def build_internal_shipment(item, selected_offer, total_lot_weight=None):
    item_weight = float(item["product"].get("weight", 0.0))
    if total_lot_weight and item_weight:
        transport_cost = round(selected_offer["price"] * item_weight / total_lot_weight, 2)
    else:
        transport_cost = round(selected_offer["price"], 2)
    return {
        "localized_product_id": item["localized_product_id"],
        "lot_id": item["lot_id"],
        "user_id": item["user_id"],
        "city": item["city"],
        "delivery_date": selected_offer["delivery_date"],
        "transport_cost": transport_cost,
        "product": item["product"],
    }
