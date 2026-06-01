"""Structural assertions about deferred purchase graphs and order persistence."""

import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentUtil.OntoNamespaces import AZON
from protocols.compra import (
    build_peticio_compra,
    build_resultat_compra,
    extract_resultat_compra,
    parse_peticio_compra,
)
from protocols.centre_logistic import (
    build_confirmacio_localitzacio,
    build_peticio_transport,
    parse_confirmacio_localitzacio,
)
from services.history_service import record_purchase
from services.order_service import build_order, save_order, save_user_shipping_data
from services.rdf_store import load_graph


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

    def test_order_graph_links_shipping_and_products_without_official_delivery_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            orders_path = base / "comandes.ttl"
            shipping_path = base / "dades_enviament_usuari.ttl"

            shipping = {
                "user_id": "USER-1",
                "user_name": "Pol",
                "street_address": "Carrer Major 1",
                "city": "Barcelona",
                "priority": "7 dies",
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
            self.assertIn((order_node, AZON.Estat, None), graph)
            self.assertNotIn((order_node, AZON.DataEntregaDefinitiva, None), graph)
            self.assertIn((order_node, AZON.TeProducte, AZON["product-P1001"]), graph)

    def test_peticio_compra_round_trip_keeps_embedded_order_and_products(self):
        request_graph = build_peticio_compra(
            "purchase-request-1",
            user_id="USER-1",
            payment_method="visa",
            shipping_data={
                "user_name": "Pol",
                "street_address": "Carrer Major 1",
                "city": "Barcelona",
                "priority": "7 dies",
            },
            product_ids=["P1001", "P1002"],
        )
        content = request_graph.value(predicate=RDF.type, object=AZON.PeticioCompra)

        parsed = parse_peticio_compra(request_graph, content)

        self.assertEqual(parsed["user_id"], "USER-1")
        self.assertEqual(parsed["payment_method"], "visa")
        self.assertEqual(parsed["shipping_data"]["user_name"], "Pol")
        self.assertEqual(parsed["shipping_data"]["street_address"], "Carrer Major 1")
        self.assertEqual(parsed["shipping_data"]["city"], "Barcelona")
        self.assertEqual(parsed["shipping_data"]["priority"], "7 dies")
        self.assertEqual(parsed["product_ids"], ["P1001", "P1002"])

    def test_resultat_compra_round_trip_keeps_open_lot_status_and_lot_assignments(self):
        order = {
            "order_id": "ORDER-1",
            "user_id": "USER-1",
            "user_name": "Pol",
            "status": "OBERT",
            "delivery_date": "2026-06-02",
            "shipping_data": {
                "user_name": "Pol",
                "street_address": "Gran Via 100",
                "city": "Barcelona",
                "priority": "48h",
                "payment_method": "visa",
            },
            "products": [
                {"product_id": "P1001", "name": "Wireless Headphones", "price": 49.0, "weight": 1.5},
            ],
        }
        reservations = [
            {
                "order_id": "ORDER-1",
                "lot_id": "LOT-1",
                "centre_id": "CL-BCN",
                "centre_city": "Barcelona",
                "city": "Barcelona",
                "delivery_date": "2026-06-02",
                "status": "OBERT",
                "products": [
                    {"product_id": "P1001", "name": "Wireless Headphones", "weight": 1.5},
                ],
            }
        ]

        message = build_resultat_compra(order, reservations, sender=AZON.Compra, receiver=AZON.Usuari, msgcnt=7)
        parsed = extract_resultat_compra(message)

        self.assertEqual(parsed["order_id"], "ORDER-1")
        self.assertEqual(parsed["status"], "OBERT")
        self.assertEqual(parsed["estimated_delivery_date"], "2026-06-02")
        self.assertIsNone(parsed["official_delivery_date"])
        self.assertEqual(parsed["lots"][0]["lot_id"], "LOT-1")
        self.assertEqual(parsed["lots"][0]["centre_id"], "CL-BCN")

    def test_confirmacio_localitzacio_round_trip_keeps_open_lot_without_transport(self):
        request_data = {
            "order_id": "ORDER-1",
            "user_id": "USER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-02",
            "products": [
                {"product_id": "P1001", "name": "Wireless Headphones", "weight": 1.5},
            ],
            "centre_id": "CL-BCN",
            "centre_city": "Barcelona",
        }
        lot = {
            "lot_id": "LOT-1",
            "order_id": "ORDER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-02",
            "status": "OBERT",
            "products": [
                {"product_id": "P1001", "name": "Wireless Headphones", "weight": 1.5},
            ],
            "centre_id": "CL-BCN",
            "centre_city": "Barcelona",
        }

        message = build_confirmacio_localitzacio(
            request_data,
            lot,
            sender=AZON.CentreLogistic,
            receiver=AZON.Compra,
            msgcnt=8,
        )
        parsed = parse_confirmacio_localitzacio(message)

        self.assertEqual(parsed["lot_id"], "LOT-1")
        self.assertEqual(parsed["status"], "OBERT")
        self.assertEqual(parsed["centre_id"], "CL-BCN")
        self.assertEqual(parsed["products"][0]["product_id"], "P1001")

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
                    "priority": "7 dies",
                    "payment_method": "visa",
                },
            }

            record_purchase(history_path, order)
            graph = load_graph(history_path)
            history_node = AZON["purchase-ORDER-1"]

            self.assertIn((history_node, AZON.SobreComanda, AZON["order-ORDER-1"]), graph)
            self.assertIn((history_node, AZON.SobreProducte, AZON["product-P1001"]), graph)


if __name__ == "__main__":
    unittest.main()
