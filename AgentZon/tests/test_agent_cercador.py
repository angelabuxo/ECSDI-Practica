import sys
import unittest
from pathlib import Path

from rdflib import RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_cercador import AgentCercador, create_app
from AgentZon.config import AGENTZON
from AgentZon.protocols.cerca import build_peticio_cerca, get_resultat_cerca_subject, read_resultat_cerca


class AgentCercadorTest(unittest.TestCase):
    def test_processar_cerca_returns_resultat_cerca_rdf_graph(self):
        agent = AgentCercador()
        peticio = build_peticio_cerca(text="portatil", categ="informatica")

        resultat_graph = agent.processar_cerca(peticio)
        resultat_subject = get_resultat_cerca_subject(resultat_graph)
        resultat = read_resultat_cerca(agent.graph + resultat_graph, resultat_subject)

        self.assertIn((resultat_subject, RDF.type, AGENTZON.ResultatCerca), resultat_graph)
        self.assertGreaterEqual(resultat["total"], 1)
        self.assertIn("p001", [producte["id"] for producte in resultat["llista_productes"]])

    def test_info_endpoint_returns_turtle_state(self):
        app = create_app()

        response = app.test_client().get("/Info")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"@prefix az:", response.data)
        self.assertIn(b"Portatil Lenovo IdeaPad", response.data)


if __name__ == "__main__":
    unittest.main()
