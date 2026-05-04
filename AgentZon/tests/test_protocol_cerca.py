import sys
import unittest
from pathlib import Path

from rdflib import Graph, RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.config import AGENTZON, PRODUCTES_PATH
from AgentZon.protocols.cerca import (
    build_peticio_cerca,
    build_resultat_cerca,
    cercar_productes,
    get_peticio_cerca_subject,
    get_resultat_cerca_subject,
    read_peticio_cerca,
    read_resultat_cerca,
)


class ProtocolCercaTest(unittest.TestCase):
    def setUp(self):
        self.catalog_graph = Graph()
        self.catalog_graph.parse(PRODUCTES_PATH, format="turtle")

    def test_builds_and_reads_peticio_cerca_as_rdf(self):
        graph = build_peticio_cerca(
            text="sony",
            categ="audio",
            marca="Sony",
            preu_min=10.0,
            preu_max=60.0,
        )

        subject = get_peticio_cerca_subject(graph)
        peticio = read_peticio_cerca(graph, subject)

        self.assertIn((subject, RDF.type, AGENTZON.PeticioCerca), graph)
        self.assertEqual(peticio["text"], "sony")
        self.assertEqual(peticio["categ"], "audio")
        self.assertEqual(peticio["marca"], "sony")
        self.assertEqual(peticio["preu_min"], 10.0)
        self.assertEqual(peticio["preu_max"], 60.0)

    def test_queries_catalog_and_builds_resultat_cerca_graph(self):
        peticio_graph = build_peticio_cerca(text="sony", categ="audio", marca="Sony", preu_max=60.0)
        peticio_subject = get_peticio_cerca_subject(peticio_graph)

        productes = cercar_productes(self.catalog_graph, peticio_graph, peticio_subject)
        resultat_graph = build_resultat_cerca(self.catalog_graph, productes, peticio_subject=peticio_subject)
        resultat_subject = get_resultat_cerca_subject(resultat_graph)
        resultat = read_resultat_cerca(self.catalog_graph + resultat_graph, resultat_subject)

        self.assertEqual(resultat["total"], 1)
        self.assertEqual([producte["id"] for producte in resultat["llista_productes"]], ["p002"])
        self.assertIn((resultat_subject, RDF.type, AGENTZON.ResultatCerca), resultat_graph)
        self.assertIn((resultat_subject, AGENTZON.Mostra, AGENTZON["p002"]), resultat_graph)


if __name__ == "__main__":
    unittest.main()
