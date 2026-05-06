"""Helpers for lot creation and transport-offer evaluation."""

from datetime import date, timedelta
from uuid import uuid4

from rdflib import Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.services.rdf_store import load_graph, save_graph


# Lot persistence ------------------------------------------------------------------
def create_lot(lots_path, order_id, city, priority, products):
    graph = load_graph(lots_path)
    bind_namespaces(graph)
    node = None
    for lot in graph.subjects(RDF.type, AZON.Lot):
        lot_city = graph.value(lot, AZON.Ciutat)
        lot_priority = graph.value(lot, AZON.Prioritat)
        if str(lot_city) == city and str(lot_priority) == priority:
            node = lot
            break

    if node is None:
        lot_id = f"LOT-{uuid4().hex[:6].upper()}"
        node = AZON[f"lot-{lot_id}"]
        graph.add((node, RDF.type, AZON.Lot))
        graph.add((node, AZON.IdLot, Literal(lot_id)))
        graph.add((node, AZON.Ciutat, Literal(city)))
        graph.add((node, AZON.Prioritat, Literal(priority)))
        total_weight = 0.0
    else:
        lot_id = str(graph.value(node, AZON.IdLot))
        existing_weight = graph.value(node, AZON.PesTotal)
        total_weight = float(existing_weight) if existing_weight is not None else 0.0

    graph.add((node, AZON.SobreComanda, AZON[f"order-{order_id}"]))
    for product in products:
        total_weight += float(product["weight"])
        graph.add((node, AZON.TeProducte, AZON[f"product-{product['product_id']}"]))
    graph.set((node, AZON.PesTotal, Literal(total_weight)))
    save_graph(lots_path, graph)
    return {
        "lot_id": lot_id,
        "order_id": order_id,
        "city": city,
        "priority": priority,
        "total_weight": total_weight,
    }


# Offer evaluation -----------------------------------------------------------------
def choose_best_offer(offers):
    return min(offers, key=lambda offer: (offer["price"], offer["delivery_date"]))


def estimate_dispatch_date(priority):
    base_days = {"urgent": 1, "standard": 3, "relaxed": 5}.get(priority, 3)
    return (date.today() + timedelta(days=base_days)).isoformat()
