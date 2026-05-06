"""Structural assertions about order and purchase-history persistence."""

import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON
from AgentZon.protocols.centre_logistic import build_peticio_transport
from AgentZon.services.history_service import record_purchase
from AgentZon.services.order_service import build_order, save_order, save_user_shipping_data
from AgentZon.services.rdf_store import load_graph


class OrderGraphTests(unittest.TestCase):
    def test_transport_request_carries_max_delivery_date(self):
        lot = {
            "lot_id": "LOT-1",
            "order_id": "ORDER-1",
            "city": "Barcelona",
            "delivery_date": "2026-05-10",
            "total_weight": 3.5,
        }
        message, content = build_peticio_transport(lot)
        self.assertIn((content, AZON.DataEntrega, None), message)

    def test_order_graph_links_shipping_and_products(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            orders_path = base / "comandes.ttl"
            shipping_path = base / "dades_enviament_usuari.ttl"

            shipping = {
                "user_id": "USER-1",
                "user_name": "Pol",
                "street_address": "Carrer Major 1",
                "city": "Barcelona",
                "priority": "48h",
                "payment_method": "visa",
            }
            products = [{"product_id": "P1001", "name": "Wireless Headphones", "weight": 1.5}]
            order = build_order(shipping, products)

            save_user_shipping_data(shipping_path, order)
            save_order(orders_path, order)

            graph = load_graph(orders_path)
            order_node = AZON[f"order-{order['order_id']}"]

            self.assertIn((order_node, RDF.type, AZON.Comanda), graph)
            self.assertIn((order_node, AZON.MetodePagament, None), graph)
            self.assertIn((order_node, AZON.DataEntrega, None), graph)
            self.assertIn((order_node, AZON.DataEntregaDefinitiva, None), graph)
            self.assertIn((order_node, AZON.TeProducte, AZON["product-P1001"]), graph)

    def test_purchase_history_links_back_to_the_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "historial_compres.ttl"
            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "user_name": "Pol",
                "products": [{"product_id": "P1001"}],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "street_address": "Carrer Major 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            }

            record_purchase(history_path, order)
            graph = load_graph(history_path)
            history_node = AZON["purchase-ORDER-1"]

            self.assertIn((history_node, AZON.SobreComanda, AZON["order-ORDER-1"]), graph)
            self.assertIn((history_node, AZON.TeProducte, AZON["product-P1001"]), graph)


if __name__ == "__main__":
    unittest.main()
