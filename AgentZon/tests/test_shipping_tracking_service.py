import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rdflib import Graph

from services.shipping_tracking_service import apply_shipping_update, save_localization_confirmations


class ShippingTrackingServiceTests(unittest.TestCase):
    def test_concurrent_tracking_updates_do_not_corrupt_turtle(self):
        reservation = {
            "localized_product_id": "ploc-1",
            "order_id": "ORDER-1",
            "lot_id": "LOT-1",
            "user_id": "USER-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-10",
            "product": {"product_id": "P1", "name": "X", "weight": 1.0},
            "centre_id": "CL-BCN",
            "centre_city": "Barcelona",
        }
        shipment = {
            "localized_product_id": "ploc-1",
            "lot_id": "LOT-1",
            "city": "Barcelona",
            "delivery_date": "2026-06-08",
            "transport_id": "economy",
            "transport_name": "Transportista-economy",
            "price": 6.0,
            "product": {"product_id": "P1", "name": "X", "weight": 1.0},
            "centre_id": "CL-BCN",
            "centre_city": "Barcelona",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_path = Path(tmpdir) / "seguiment_enviaments.ttl"
            failures = []

            def update_tracking(i):
                try:
                    if i % 2:
                        save_localization_confirmations(tracking_path, [reservation])
                    else:
                        apply_shipping_update(tracking_path, shipment, shipped=False, invoice=None)
                except Exception as exc:
                    failures.append(exc)

            for _ in range(10):
                with ThreadPoolExecutor(max_workers=8) as executor:
                    list(executor.map(update_tracking, range(20)))

            self.assertEqual([], failures)
            graph = Graph()
            graph.parse(tracking_path, format="turtle")


if __name__ == "__main__":
    unittest.main()
