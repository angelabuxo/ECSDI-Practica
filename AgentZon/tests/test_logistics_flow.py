"""Flow tests for logistics-center and transport-negotiation behaviour."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace


class LogisticsFlowTests(unittest.TestCase):
    def test_centre_logistic_queries_two_transport_agents_and_picks_the_cheapest_offer(self):
        from AgentZon.AgentUtil.Agent import Agent
        from AgentZon.agents import agent_centre_logistic
        from AgentZon.protocols.centre_logistic import (
            build_productes_localitzats,
            build_resposta_oferta_transport,
            extract_shipping_details,
        )

        agn = Namespace("http://www.agentes.org#")

        logistics_agent = Agent(
            "CentreLogisticAgent",
            agn.CentreLogistic,
            "http://centre.test/comm",
            "http://centre.test/stop",
        )
        fast_transport = Agent(
            "TransportFast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/stop",
        )
        economy_transport = Agent(
            "TransportEconomy",
            agn.TransportEconomy,
            "http://transport-economy.test/comm",
            "http://transport-economy.test/stop",
        )

        def fake_send_message(message, address):
            if address == fast_transport.address:
                return build_resposta_oferta_transport(
                    {
                        "lot_id": "LOT-1",
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

            request_graph, content = build_productes_localitzats(
                order_id="ORDER-1",
                user_id="USER-1",
                city="Barcelona",
                priority="urgent",
                products=[
                    {
                        "product_id": "P1001",
                        "name": "Wireless Headphones",
                        "weight": 1.5,
                    }
                ],
            )

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


if __name__ == "__main__":
    unittest.main()
