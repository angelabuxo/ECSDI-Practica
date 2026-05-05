import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace


class LogisticsFlowTests(unittest.TestCase):
    def test_centre_logistic_queries_two_transport_agents_and_picks_the_cheapest_offer(self):
        from AgentZon.AgentUtil.Agent import Agent
        from AgentZon.agents.agent_centre_logistic import create_app as create_logistics_app
        from AgentZon.agents.agent_transportista import create_app as create_transport_app
        from AgentZon.protocols.centre_logistic import (
            build_productes_localitzats,
            extract_shipping_details,
        )
        from AgentZon.tests.support import LocalMessageRouter

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

        router = LocalMessageRouter()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            transport_apps = [
                create_transport_app(
                    {
                        "agent": fast_transport,
                        "transport_id": "fast",
                        "price_per_kg": 7.5,
                        "delivery_days": 1,
                    }
                ),
                create_transport_app(
                    {
                        "agent": economy_transport,
                        "transport_id": "economy",
                        "price_per_kg": 4.0,
                        "delivery_days": 3,
                    }
                ),
            ]
            logistics_app = create_logistics_app(
                {
                    "agent": logistics_agent,
                    "data_dir": data_dir,
                    "transport_agents": [fast_transport, economy_transport],
                },
                message_sender=router.send_message,
            )

            router.register_app(fast_transport.address, transport_apps[0])
            router.register_app(economy_transport.address, transport_apps[1])
            router.register_app(logistics_agent.address, logistics_app)

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

            response_graph = router.send_message(request_graph, logistics_agent.address)
            details = extract_shipping_details(response_graph)

            self.assertEqual(details["transport_id"], "economy")
            self.assertEqual(details["order_id"], "ORDER-1")
            self.assertEqual(details["city"], "Barcelona")
            self.assertGreater(details["price"], 0.0)


if __name__ == "__main__":
    unittest.main()
