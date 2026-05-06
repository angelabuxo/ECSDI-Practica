"""Structural assertions about the refined AgentZon ontology vocabulary."""

import unittest

from rdflib import Graph, OWL, RDF

from AgentZon.AgentUtil.OntoNamespaces import AZON


class OntologyAlignmentTests(unittest.TestCase):
    def test_refined_ontology_removes_internal_agent_branch_and_legacy_terms(self):
        graph = Graph()
        graph.parse("AgentZon/ontologia/AgentZonOntology.rdf", format="xml")

        self.assertIn((AZON.TeProducte, RDF.type, OWL.ObjectProperty), graph)
        self.assertIn((AZON.PesTotal, RDF.type, OWL.DatatypeProperty), graph)
        self.assertNotIn((AZON.AgentIntern, None, None), graph)
        self.assertNotIn((AZON.AgentCercador, None, None), graph)
        self.assertNotIn((AZON.AgentCompra, None, None), graph)
        self.assertNotIn((AZON.emissor, None, None), graph)
        self.assertNotIn((AZON.receptor, None, None), graph)
        self.assertNotIn((AZON.teProducte, None, None), graph)


if __name__ == "__main__":
    unittest.main()
