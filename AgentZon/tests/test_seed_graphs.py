"""Structural assertions about the bootstrapped seed graphs."""

import tempfile
import unittest
from pathlib import Path

from rdflib import RDF

from AgentUtil.OntoNamespaces import AZON
from services.bootstrap import bootstrap_phase2_data
from services.rdf_store import load_graph


class SeedGraphTests(unittest.TestCase):
    def test_bootstrap_generates_reproducible_random_catalog_and_locations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=12, seed=7)

            products = load_graph(data_dir / "productes.ttl")
            locations = load_graph(data_dir / "ubicacions_productes.ttl")

            product_nodes = sorted(products.subjects(RDF.type, AZON.Producte))
            self.assertEqual(len(product_nodes), 12)
            centres = sorted(locations.subjects(RDF.type, AZON.CentreLogistic))
            self.assertEqual(centres, [AZON["centre-BCN"]])

            for product_node in product_nodes:
                self.assertIsNotNone(products.value(product_node, AZON.IdProducte))
                self.assertIsNotNone(products.value(product_node, AZON.Nom))
                self.assertIsNotNone(products.value(product_node, AZON.Descripcio))
                self.assertIsNotNone(products.value(product_node, AZON.Categoria))
                self.assertIsNotNone(products.value(product_node, AZON.Marca))
                self.assertGreater(float(products.value(product_node, AZON.Preu)), 0.0)
                self.assertGreater(float(products.value(product_node, AZON.Pes)), 0.0)
                self.assertEqual(list(locations.objects(product_node, AZON.UbicatACentre)), [AZON["centre-BCN"]])

    def test_bootstrap_with_same_seed_generates_same_catalog(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=99)
            first_snapshot = set(load_graph(data_dir / "productes.ttl"))

            bootstrap_phase2_data(data_dir, product_count=8, seed=99)
            second_snapshot = set(load_graph(data_dir / "productes.ttl"))

            self.assertEqual(first_snapshot, second_snapshot)


if __name__ == "__main__":
    unittest.main()
