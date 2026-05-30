"""Catalog search tests for the AgentZon RDF product store."""

import tempfile
import unittest
from pathlib import Path

from tests.support import load_catalog_products


class CatalogServiceTests(unittest.TestCase):
    def test_search_products_filters_against_generated_catalog(self):
        from services.bootstrap import bootstrap_phase2_data
        from services.catalog_service import search_products

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=12)
            catalog_path = data_dir / "productes.ttl"
            sample = load_catalog_products(catalog_path)[0]
            search_token = sample["name"].split()[0]
            results = search_products(
                catalog_path,
                {
                    "text": search_token,
                    "category": sample["category"],
                    "brand": sample["brand"],
                    "min_price": sample["price"] - 0.01,
                    "max_price": sample["price"] + 0.01,
                },
            )

            self.assertIn(sample["product_id"], {result["product_id"] for result in results})
            self.assertIn(sample["name"], {result["name"] for result in results})


if __name__ == "__main__":
    unittest.main()
