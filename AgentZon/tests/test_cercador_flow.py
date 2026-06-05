import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AGN
from protocols.cerca import build_peticio_consulta_productes, extract_product_snapshots
from protocols.opinador import build_confirmacio_registre_cerca, parse_peticio_registre_cerca
from services.bootstrap import bootstrap_phase2_data


class CercadorFlowTests(unittest.TestCase):
    def test_product_lookup_returns_only_requested_products(self):
        from agents import agent_cercador

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=6, seed=21)
            agent = Agent("CercadorAgent", AGN.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
            agent_cercador.configure_runtime({"agent": agent, "directory_agent": None, "data_dir": data_dir})
            client = agent_cercador.app.test_client()

            message = build_peticio_consulta_productes(["P1001", "P1003"], sender=AGN.Compra, receiver=agent.uri, msgcnt=1)
            response = client.get("/comm", query_string={"content": message.serialize(format="xml")})
            graph = Graph()
            graph.parse(data=response.get_data(as_text=True), format="xml")
            products = extract_product_snapshots(graph)

            self.assertEqual({product["product_id"] for product in products}, {"P1001", "P1003"})

    def test_search_history_registration_is_delegated_to_opinador(self):
        from agents import agent_cercador

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            agn = Namespace("http://www.agentes.org#")
            cercador = Agent("CercadorAgent", agn.Cercador, "http://cercador.test/comm", "http://cercador.test/Stop")
            opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
            delegated = []

            agent_cercador.configure_runtime({"agent": cercador, "directory_agent": None, "data_dir": data_dir})

            def fake_sender(message, address):
                delegated.append(parse_peticio_registre_cerca(message))
                return build_confirmacio_registre_cerca(
                    "USER-1",
                    sender=opinador.uri,
                    receiver=cercador.uri,
                    msgcnt=2,
                )

            agent_cercador.MESSAGE_SENDER = fake_sender
            agent_cercador.resolve_opinador_agent = lambda: opinador

            agent_cercador.pla_registrar_cerca_a_opinador(
                {"text": "", "category": "periferics", "brand": "KeyCo", "min_price": None, "max_price": None},
                [{"product_id": "P1002", "name": "Ratoli", "category": "periferics", "brand": "KeyCo", "price": 20.0, "weight": 0.2}],
                user_id="USER-1",
            )

            self.assertEqual(delegated[0]["user_id"], "USER-1")
            self.assertEqual(delegated[0]["criteria"]["brand"], "KeyCo")
            self.assertEqual(delegated[0]["products"][0]["product_id"], "P1002")


if __name__ == "__main__":
    unittest.main()
