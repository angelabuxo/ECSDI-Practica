from datetime import date, timedelta
from uuid import uuid4

from rdflib import Literal, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON, bind_namespaces
from AgentZon.domain import TransportOffer
from AgentZon.services.rdf_store import RDFFileStore


class LogisticsService:
    def __init__(self, lots_path):
        self.store = RDFFileStore(lots_path)

    def create_lot(self, order_id, city, priority, products):
        graph = self.store.load_graph()
        bind_namespaces(graph)
        lot_id = f"LOT-{uuid4().hex[:6].upper()}"
        node = AZON[f"lot-{lot_id}"]
        graph.add((node, RDF.type, AZON.Lot))
        graph.add((node, AZON.idLot, Literal(lot_id)))
        graph.add((node, AZON.idComanda, Literal(order_id)))
        graph.add((node, AZON.ciutat, Literal(city)))
        graph.add((node, AZON.prioritat, Literal(priority)))
        total_weight = 0.0
        for product in products:
            total_weight += float(product["weight"])
            graph.add((node, AZON.idProducte, Literal(product["product_id"])))
        graph.add((node, AZON.pes, Literal(total_weight)))
        self.store.save_graph(graph)
        return {"lot_id": lot_id, "order_id": order_id, "city": city, "priority": priority, "total_weight": total_weight}

    @staticmethod
    def choose_best_offer(offers):
        return min(offers, key=lambda offer: (offer.price, offer.delivery_date))

    @staticmethod
    def estimate_dispatch_date(priority):
        base_days = {"urgent": 1, "standard": 3, "relaxed": 5}.get(priority, 3)
        return (date.today() + timedelta(days=base_days)).isoformat()
