"""Ontology regression tests for naming, structure, and RDF integration."""

import re
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS


class OntologyAlignmentTests(unittest.TestCase):
    def _load_ontology(self):
        ontology_path = Path(__file__).resolve().parents[1] / "ontologia" / "AgentZonOntology.rdf"
        graph = Graph()
        graph.parse(ontology_path)
        return graph

    def test_ontology_terms_are_upper_camel_case_and_internal_agents_are_not_modeled(self):
        from AgentZon.AgentUtil.OntoNamespaces import AZON

        graph = self._load_ontology()
        pattern = re.compile(r"^[A-Z][A-Za-z0-9]*$")
        local_terms = set()

        for rdf_type in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
            for subject in graph.subjects(RDF.type, rdf_type):
                subject_text = str(subject)
                if subject_text.startswith(str(AZON)):
                    local_terms.add(subject_text.split("#", 1)[1])

        self.assertIn("Actor", local_terms)
        self.assertIn("TeProducte", local_terms)
        self.assertIn("IdProducte", local_terms)
        self.assertIn("MostraProducte", local_terms)
        self.assertNotIn("AgentIntern", local_terms)
        self.assertNotIn("AgentCercador", local_terms)
        self.assertNotIn("teProducte", local_terms)
        self.assertNotIn("idProducte", local_terms)
        self.assertTrue(local_terms)
        self.assertTrue(all(pattern.match(term) for term in local_terms))

    def test_ontology_declares_key_domains_and_ranges(self):
        from AgentZon.AgentUtil.OntoNamespaces import AZON

        graph = self._load_ontology()

        expected_triples = [
            (AZON.MostraProducte, RDFS.domain, AZON.ResultatCerca),
            (AZON.MostraProducte, RDFS.range, AZON.Producte),
            (AZON.TeProducte, RDFS.range, AZON.Producte),
            (AZON.TeDadesEnviament, RDFS.domain, AZON.Comanda),
            (AZON.TeDadesEnviament, RDFS.range, AZON.DadesEnviamentUsuari),
            (AZON.SobreComanda, RDFS.range, AZON.Comanda),
            (AZON.SobreLot, RDFS.range, AZON.Lot),
            (AZON.UbicatACentre, RDFS.domain, AZON.UbicacioProducte),
            (AZON.UbicatACentre, RDFS.range, AZON.CentreLogistic),
        ]

        for triple in expected_triples:
            self.assertIn(triple, graph)

    def test_runtime_graphs_use_object_relations_between_domain_entities(self):
        from AgentZon.AgentUtil.ACLMessages import get_message_properties
        from AgentZon.AgentUtil.OntoNamespaces import AZON
        from AgentZon.protocols.compra import build_peticio_registre_compra
        from AgentZon.services.order_service import create_order, save_user_shipping_data
        from AgentZon.services.rdf_store import load_graph

        order = {
            "order_id": "ORDER-TEST",
            "user_id": "USER-1",
            "user_name": "Pol",
            "products": [{"product_id": "P1001"}],
            "shipping_data": {
                "user_id": "USER-1",
                "user_name": "Pol",
                "street_address": "Mallorca 1",
                "city": "Barcelona",
                "priority": "standard",
                "payment_method": "visa",
            },
        }

        message = build_peticio_registre_compra(order)
        content = get_message_properties(message)["content"]
        self.assertEqual(
            [str(node) for node in message.objects(content, AZON.TeProducte)],
            [str(AZON["Producte-P1001"])],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            orders_path = data_dir / "comandes.ttl"
            shipping_path = data_dir / "dades_enviament_usuari.ttl"

            save_user_shipping_data(shipping_path, order["shipping_data"])
            create_order(orders_path, order["shipping_data"], [{"product_id": "P1001"}])

            orders_graph = load_graph(orders_path)
            order_node = next(orders_graph.subjects(RDF.type, AZON.Comanda))
            self.assertTrue(list(orders_graph.objects(order_node, AZON.TeProducte)))
            self.assertTrue(list(orders_graph.objects(order_node, AZON.TeDadesEnviament)))


if __name__ == "__main__":
    unittest.main()
