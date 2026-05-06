"""Catalog search tests for the AgentZon RDF product store."""

import tempfile
import unittest
from pathlib import Path


class CatalogServiceTests(unittest.TestCase):
    def test_search_products_filters_by_text_category_brand_and_price(self):
        from AgentZon.services.bootstrap import bootstrap_phase2_data
        from AgentZon.services.catalog_service import search_products

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)
            results = search_products(
                data_dir / "productes.ttl",
                {
                    "text": "wireless",
                    "category": "audio",
                    "brand": "AuralMax",
                    "min_price": 50.0,
                    "max_price": 120.0,
                },
            )

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["product_id"], "P1001")
            self.assertEqual(results[0]["name"], "Wireless Headphones")


if __name__ == "__main__":
    unittest.main()
