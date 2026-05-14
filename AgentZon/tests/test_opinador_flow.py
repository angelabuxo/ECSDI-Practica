"""Flow tests for the Opinador agent capabilities."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace


class OpinadorFlowTests(unittest.TestCase):
    def test_opinador_records_purchase_feedback_and_validates_returns(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_opinador
        from protocols.compra import build_peticio_registre_compra
        from protocols.opinador import build_peticio_consulta_devolucio
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import load_graph
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})

            router = LocalMessageRouter()
            router.register_app(opinador.address, agent_opinador.app)

            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "products": [{"product_id": "P1001"}],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "street_address": "Carrer Major 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
                "delivery_date": "2026-05-10",
            }
            purchase_request = build_peticio_registre_compra(order, sender=compra.uri, receiver=opinador.uri, msgcnt=1)
            purchase_response = router.send_message(purchase_request, opinador.address)
            purchase_props = get_message_properties(purchase_response)
            self.assertIn("content", purchase_props)

            purchase_history_text = (data_dir / "historial_compres.ttl").read_text(encoding="utf-8")
            self.assertIn("DataCompra", purchase_history_text)
            self.assertIn("DataEntregaDefinitiva", purchase_history_text)

            feedback_client = agent_opinador.app.test_client()
            feedback_response = feedback_client.post(
                "/feedback",
                json={
                    "feedback_id": "FB-1",
                    "order_id": "ORDER-1",
                    "user_id": "USER-1",
                    "score": 5,
                    "comment": "Perfecte",
                    "products": ["P1001"],
                },
            )
            self.assertEqual(feedback_response.status_code, 200)

            feedback_text = (data_dir / "feedback.ttl").read_text(encoding="utf-8")
            self.assertIn("Perfecte", feedback_text)
            self.assertIn("Puntuacio", feedback_text)

            return_request = build_peticio_consulta_devolucio(
                "RET-1",
                "ORDER-1",
                "USER-1",
                ["P1001"],
                "producte defectuós",
                sender=compra.uri,
                receiver=opinador.uri,
                msgcnt=2,
            )
            return_response = router.send_message(return_request, opinador.address)
            return_props = get_message_properties(return_response)
            return_content = return_props["content"]
            return_graph = return_response
            self.assertTrue(bool(return_graph.value(return_content, AZON.Acceptada)))
            self.assertEqual(str(return_graph.value(return_content, AZON.Estat)), "acceptada")

    def test_opinador_generates_recommendations_from_histories(self):
        from AgentUtil.Agent import Agent
        from agents import agent_opinador
        from services.bootstrap import bootstrap_phase2_data
        from services.history_service import record_search

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})

            record_search(
                data_dir / "historial_cerques.ttl",
                {"text": "wireless", "category": "audio", "brand": "AuralMax", "min_price": None, "max_price": None},
                [{"product_id": "P1001", "name": "Wireless Headphones", "description": "Wireless over-ear headphones with noise isolation", "category": "audio", "brand": "AuralMax", "price": 89.99, "weight": 1.5}],
            )

            client = agent_opinador.app.test_client()
            response = client.get("/recommendations", query_string={"limit": "1"})
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["product_id"], "P1001")


if __name__ == "__main__":
    unittest.main()