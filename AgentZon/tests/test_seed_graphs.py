"""Structural assertions about the bootstrapped seed graphs."""

import tempfile
import unittest
from pathlib import Path

from AgentUtil.OntoNamespaces import AZON
from services.bootstrap import bootstrap_phase2_data
from services.rdf_store import load_graph


class SeedGraphTests(unittest.TestCase):
    def test_bootstrap_uses_refined_vocabulary_and_explicit_location_relations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)

            locations = load_graph(data_dir / "ubicacions_productes.ttl")

            self.assertIn((AZON["product-P1001"], AZON.UbicatACentre, AZON["centre-BCN"]), locations)


if __name__ == "__main__":
    unittest.main()
