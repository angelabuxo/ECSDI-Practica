"""Helpers for lot creation and transport-offer evaluation."""

from threading import Lock
from uuid import uuid4

from rdflib import Literal, RDF

from AgentUtil.OntoNamespaces import AZON, bind_namespaces
from services.rdf_store import load_graph, save_graph


LOT_LOCK = Lock()


# Lot persistence ------------------------------------------------------------------
def create_lot(lots_path, order_id, city, delivery_date, products, centre_id=None, centre_city=None):
    with LOT_LOCK:
        graph = load_graph(lots_path)
        bind_namespaces(graph)
        node = None
        for lot in graph.subjects(RDF.type, AZON.Lot):
            lot_city = graph.value(lot, AZON.Ciutat)
            lot_delivery_date = graph.value(lot, AZON.DataEntrega)
            if str(lot_city) == city and str(lot_delivery_date) == delivery_date:
                node = lot
                break

        created_new_lot = node is None

        if created_new_lot:
            lot_id = f"LOT-{uuid4().hex[:6].upper()}"
            node = AZON[f"lot-{lot_id}"]
            graph.add((node, RDF.type, AZON.Lot))
            graph.add((node, AZON.IdLot, Literal(lot_id)))
            graph.add((node, AZON.Ciutat, Literal(city)))
            graph.add((node, AZON.DataEntrega, Literal(delivery_date)))
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
            "delivery_date": delivery_date,
            "total_weight": total_weight,
            "created_new_lot": created_new_lot,
            "products": [dict(product) for product in products],
            "centre_id": centre_id,
            "centre_city": centre_city,
        }


# Offer evaluation -----------------------------------------------------------------
def choose_best_offer(offers):
    return min(offers, key=lambda offer: (offer["price"], offer["delivery_date"]))
