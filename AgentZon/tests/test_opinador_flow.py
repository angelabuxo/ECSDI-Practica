"""Flow tests for the Opinador agent."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, RDF

from AgentUtil.Agent import Agent
from AgentUtil.OntoNamespaces import AZON
from protocols.compra import build_peticio_registre_compra
from protocols.opinador import build_peticio_devolucio, parse_resolucio_devolucio
from services.bootstrap import bootstrap_phase2_data
from services.history_service import load_feedback_records, load_purchase_records
from services.opinador_service import generate_recommendations


class OpinadorFlowTests(unittest.TestCase):
    def test_generate_recommendations_excludes_already_purchased_products(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"

            all_recommendations = generate_recommendations(
                catalog_path,
                data_dir / "historial_cerques.ttl",
                data_dir / "historial_compres.ttl",
                limit=8,
            )
            self.assertTrue(all_recommendations)

            first_product = all_recommendations[0]
            from services.history_service import record_purchase

            record_purchase(
                data_dir / "historial_compres.ttl",
                {
                    "order_id": "ORDER-1",
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "products": [{"product_id": first_product["product_id"]}],
                    "shipping_data": {
                        "user_id": "USER-1",
                        "user_name": "Pol",
                        "street_address": "Gran Via 1",
                        "city": "Barcelona",
                        "priority": "48h",
                        "payment_method": "visa",
                    },
                },
            )

            filtered_recommendations = generate_recommendations(
                catalog_path,
                data_dir / "historial_cerques.ttl",
                data_dir / "historial_compres.ttl",
                user_id="USER-1",
                limit=8,
            )
            self.assertNotIn(first_product["product_id"], {product["product_id"] for product in filtered_recommendations})

    def test_opinador_registers_purchase_feedback_and_return_resolution(self):
        from agents import agent_opinador

        agn = Namespace("http://www.agentes.org#")
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=8, seed=21)
            catalog_path = data_dir / "productes.ttl"
            products = generate_recommendations(catalog_path, data_dir / "historial_cerques.ttl", data_dir / "historial_compres.ttl", limit=8)
            purchased_product = products[0]

            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            client = agent_opinador.app.test_client()

            purchase_order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "user_name": "Pol",
                "products": [
                    {"product_id": purchased_product["product_id"], "name": purchased_product["name"], "price": purchased_product["price"]},
                ],
                "shipping_data": {
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "street_address": "Gran Via 1",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "visa",
                },
            }

            purchase_message = build_peticio_registre_compra(
                purchase_order,
                sender=opinador.uri,
                receiver=opinador.uri,
                msgcnt=1,
            )
            purchase_response = client.get("/comm", query_string={"content": purchase_message.serialize(format="xml")})
            parsed_response = Graph()
            parsed_response.parse(data=purchase_response.get_data(as_text=True), format="xml")
            self.assertIsNotNone(parsed_response.value(predicate=RDF.type, object=AZON.ConfirmacioRegistreCompra))

            purchases = load_purchase_records(data_dir / "historial_compres.ttl")
            self.assertEqual(len(purchases), 1)
            self.assertEqual(purchases[0]["order_id"], "ORDER-1")

            feedback_response = client.post(
                "/iface",
                data={
                    "action": "feedback",
                    "feedback_id": "FB-1",
                    "user_id": "USER-1",
                    "order_id": "ORDER-1",
                    "rating": "5",
                    "product_ids": purchased_product["product_id"],
                    "comment": "Bon servei",
                },
            )
            html = feedback_response.get_data(as_text=True)
            self.assertIn("Feedback FB-1 registrat correctament", html)

            feedback_records = load_feedback_records(data_dir / "feedback.ttl")
            self.assertEqual(len(feedback_records), 1)
            self.assertEqual(feedback_records[0]["rating"], 5)

            return_message = build_peticio_devolucio(
                {
                    "return_id": "RET-1",
                    "order_id": "ORDER-1",
                    "user_id": "USER-1",
                    "amount": purchased_product["price"],
                    "reason": "No satisfà",
                    "products": [{"product_id": purchased_product["product_id"]}],
                },
                sender=opinador.uri,
                receiver=opinador.uri,
                msgcnt=2,
            )
            return_response = client.get("/comm", query_string={"content": return_message.serialize(format="xml")})
            return_graph = Graph()
            return_graph.parse(data=return_response.get_data(as_text=True), format="xml")
            decision = parse_resolucio_devolucio(return_graph)
            self.assertTrue(decision["accepted"])
            self.assertEqual(decision["return_id"], "RET-1")


if __name__ == "__main__":
    unittest.main()