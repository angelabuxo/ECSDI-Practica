"""Flow tests for logistics-center and transport-negotiation behaviour."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace


class LogisticsFlowTests(unittest.TestCase):
    def test_centre_runtime_uses_a_centre_specific_lots_file(self):
        from AgentUtil.Agent import Agent
        from agents import agent_centre_logistic

        agn = Namespace("http://www.agentes.org#")
        logistics_agent = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre-bcn.test/comm",
            "http://centre-bcn.test/Stop",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            agent_centre_logistic.configure_runtime(
                {
                    "agent": logistics_agent,
                    "data_dir": Path(tmpdir),
                    "transport_agents": [],
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                }
            )
            self.assertEqual(agent_centre_logistic.LOTS_PATH.name, "lots-CL-BCN.ttl")

    def test_create_lot_merges_products_for_same_city_and_delivery_date(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.logistics_service import create_lot
        from services.rdf_store import load_graph
        from rdflib import RDF

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"

            first_lot = create_lot(
                lots_path,
                order_id="ORDER-1",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[
                    {"product_id": "P1", "weight": 1.5},
                ],
                centre_id="CL-BCN",
            )
            second_lot = create_lot(
                lots_path,
                order_id="ORDER-2",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[
                    {"product_id": "P2", "weight": 2.0},
                ],
                centre_id="CL-BCN",
            )
            self.assertTrue(first_lot["created_new_lot"])
            self.assertFalse(second_lot["created_new_lot"])

            graph = load_graph(lots_path)
            lots = list(graph.subjects(RDF.type, AZON.Lot))
            self.assertEqual(len(lots), 1)
            self.assertEqual(first_lot["lot_id"], second_lot["lot_id"])

            lot = lots[0]
            self.assertEqual(float(graph.value(lot, AZON.PesTotal)), 3.5)
            self.assertEqual(
                {str(value) for value in graph.objects(lot, AZON.TeProducte)},
                {str(AZON["product-P1"]), str(AZON["product-P2"])},
            )
            self.assertEqual(
                {str(value) for value in graph.objects(lot, AZON.SobreComanda)},
                {str(AZON["order-ORDER-1"]), str(AZON["order-ORDER-2"])},
            )

    def test_create_lot_does_not_merge_different_centres_for_same_city_and_date(self):
        from services.logistics_service import create_lot

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"

            bcn_lot = create_lot(
                lots_path,
                order_id="ORDER-1",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[{"product_id": "P1", "weight": 1.0}],
                centre_id="CL-BCN",
            )
            gi_lot = create_lot(
                lots_path,
                order_id="ORDER-1",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[{"product_id": "P2", "weight": 1.0}],
                centre_id="CL-GI",
            )

            self.assertTrue(bcn_lot["created_new_lot"])
            self.assertTrue(gi_lot["created_new_lot"])
            self.assertNotEqual(bcn_lot["lot_id"], gi_lot["lot_id"])

    def test_create_lot_creates_new_lot_for_different_city_or_delivery_date(self):
        from services.logistics_service import create_lot

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"

            first_lot = create_lot(
                lots_path,
                order_id="ORDER-1",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[{"product_id": "P1", "weight": 1.0}],
            )
            second_lot = create_lot(
                lots_path,
                order_id="ORDER-2",
                city="Barcelona",
                delivery_date="2026-05-11",
                products=[{"product_id": "P2", "weight": 1.0}],
            )
            third_lot = create_lot(
                lots_path,
                order_id="ORDER-3",
                city="Girona",
                delivery_date="2026-05-10",
                products=[{"product_id": "P3", "weight": 1.0}],
            )
            self.assertTrue(first_lot["created_new_lot"])
            self.assertTrue(second_lot["created_new_lot"])
            self.assertTrue(third_lot["created_new_lot"])

            self.assertNotEqual(first_lot["lot_id"], second_lot["lot_id"])
            self.assertNotEqual(first_lot["lot_id"], third_lot["lot_id"])
            self.assertNotEqual(second_lot["lot_id"], third_lot["lot_id"])

    def test_centre_logistic_queries_two_transport_agents_and_picks_the_cheapest_offer(self):
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.Agent import Agent
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_centre_logistic
        from protocols.centre_logistic import (
            build_productes_localitzats,
            build_resposta_oferta_transport,
            extract_shipping_details,
        )

        agn = Namespace("http://www.agentes.org#")

        logistics_agent = Agent(
            "CentreLogisticAgent",
            agn.CentreLogistic,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )
        fast_transport = Agent(
            "TransportFast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        economy_transport = Agent(
            "TransportEconomy",
            agn.TransportEconomy,
            "http://transport-economy.test/comm",
            "http://transport-economy.test/Stop",
        )

        def fake_send_message(message, address):
            if address == fast_transport.address:
                return build_resposta_oferta_transport(
                    {
                        "lot_id": "LOT-1",
                        "order_id": "ORDER-1",
                        "transport_id": "fast",
                        "transport_name": fast_transport.name,
                        "city": "Barcelona",
                        "delivery_date": "2026-05-06",
                        "price": 11.25,
                    },
                    sender=fast_transport.uri,
                    receiver=logistics_agent.uri,
                    msgcnt=1,
                )
            if address == economy_transport.address:
                return build_resposta_oferta_transport(
                    {
                        "lot_id": "LOT-1",
                        "order_id": "ORDER-1",
                        "transport_id": "economy",
                        "transport_name": economy_transport.name,
                        "city": "Barcelona",
                        "delivery_date": "2026-05-08",
                        "price": 6.0,
                    },
                    sender=economy_transport.uri,
                    receiver=logistics_agent.uri,
                    msgcnt=2,
                )
            raise AssertionError(f"Unexpected address {address}")

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            agent_centre_logistic.configure_runtime(
                {
                    "agent": logistics_agent,
                    "data_dir": data_dir,
                    "transport_agents": [fast_transport, economy_transport],
                },
                message_sender=fake_send_message,
            )

            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "shipping_data": {"city": "Barcelona", "priority": "24h"},
                "delivery_date": "2026-05-10",
                "products": [
                    {
                        "product_id": "P1001",
                        "name": "Wireless Headphones",
                        "weight": 1.5,
                    }
                ],
            }
            request_graph, _ = build_productes_localitzats(order)

            client = agent_centre_logistic.app.test_client()
            response = client.get(
                "/comm",
                query_string={"content": request_graph.serialize(format="xml")},
            )
            self.assertEqual(response.status_code, 200)
            graph = response.get_data(as_text=True)
            from rdflib import Graph

            parsed_graph = Graph()
            parsed_graph.parse(data=graph, format="xml")
            details = extract_shipping_details(parsed_graph)

            self.assertEqual(details["transport_id"], "economy")
            self.assertEqual(details["order_id"], "ORDER-1")
            self.assertEqual(details["city"], "Barcelona")
            self.assertGreater(details["price"], 0.0)

            content = get_message_properties(parsed_graph)["content"]
            self.assertIsNotNone(parsed_graph.value(content, AZON.SobreLot))
            self.assertIsNotNone(parsed_graph.value(content, AZON.AssignatATransportista))
            self.assertIsNotNone(parsed_graph.value(content, AZON.EsRespostaA))


if __name__ == "__main__":
    unittest.main()
