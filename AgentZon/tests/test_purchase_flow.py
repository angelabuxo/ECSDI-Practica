import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace


class PurchaseFlowTests(unittest.TestCase):
    def test_browser_search_and_simple_order_flow_records_history_and_returns_shipping_summary(self):
        from AgentZon.AgentUtil.Agent import Agent
        from AgentZon.AgentUtil.DSO import DSO
        from AgentZon.agents.agent_centre_logistic import create_app as create_logistics_app
        from AgentZon.agents.agent_cercador import create_app as create_cercador_app
        from AgentZon.agents.agent_compra import create_app as create_compra_app
        from AgentZon.agents.agent_directory import create_app as create_directory_app
        from AgentZon.agents.agent_opinador import create_app as create_opinador_app
        from AgentZon.agents.agent_transportista import create_app as create_transport_app
        from AgentZon.protocols.directory import build_register_message
        from AgentZon.services.bootstrap import bootstrap_phase2_data
        from AgentZon.tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/stop",
        )
        centre = Agent(
            "CentreLogisticAgent",
            agn.CentreLogistic,
            "http://centre.test/comm",
            "http://centre.test/stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/stop",
        )
        transport_fast = Agent(
            "TransportFast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/stop",
        )
        transport_economy = Agent(
            "TransportEconomy",
            agn.TransportEconomy,
            "http://transport-economy.test/comm",
            "http://transport-economy.test/stop",
        )

        router = LocalMessageRouter()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir)

            directory_app = create_directory_app({"agent": directory})
            opinador_app = create_opinador_app({"agent": opinador, "data_dir": data_dir})
            centre_app = create_logistics_app(
                {
                    "agent": centre,
                    "data_dir": data_dir,
                    "transport_agents": [transport_fast, transport_economy],
                },
                message_sender=router.send_message,
            )
            transport_fast_app = create_transport_app(
                {
                    "agent": transport_fast,
                    "transport_id": "fast",
                    "price_per_kg": 8.0,
                    "delivery_days": 1,
                }
            )
            transport_economy_app = create_transport_app(
                {
                    "agent": transport_economy,
                    "transport_id": "economy",
                    "price_per_kg": 4.0,
                    "delivery_days": 3,
                }
            )
            compra_app = create_compra_app(
                {
                    "agent": compra,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                },
                message_sender=router.send_message,
            )
            cercador_app = create_cercador_app(
                {
                    "agent": cercador,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                },
                message_sender=router.send_message,
            )

            router.register_app(directory.address, directory_app)
            router.register_app(opinador.address, opinador_app)
            router.register_app(centre.address, centre_app)
            router.register_app(transport_fast.address, transport_fast_app)
            router.register_app(transport_economy.address, transport_economy_app)
            router.register_app(compra.address, compra_app)
            router.register_app(cercador.address, cercador_app)

            for agent, agent_type in [
                (cercador, DSO.CercadorAgent),
                (compra, DSO.CompraAgent),
                (centre, DSO.CentreLogisticAgent),
                (opinador, DSO.OpinadorAgent),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=1)
                router.send_message(register_graph, directory.address)

            search_client = cercador_app.test_client()
            search_response = search_client.post(
                "/search",
                data={
                    "text": "wireless",
                    "category": "audio",
                    "brand": "AuralMax",
                    "min_price": "20",
                    "max_price": "150",
                },
            )
            search_html = search_response.get_data(as_text=True)
            self.assertIn("Wireless Headphones", search_html)

            compra_client = compra_app.test_client()
            purchase_page = compra_client.post(
                "/purchase",
                data={"selected_product_ids": ["P1001"]},
            )
            self.assertIn("Confirm purchase", purchase_page.get_data(as_text=True))

            confirmation = compra_client.post(
                "/confirm-purchase",
                data={
                    "selected_product_ids": ["P1001"],
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "street_address": "Carrer de Mallorca 401",
                    "city": "Barcelona",
                    "priority": "standard",
                    "payment_method": "placeholder-visa",
                },
            )
            confirmation_html = confirmation.get_data(as_text=True)
            self.assertIn("economy", confirmation_html)
            self.assertIn("ORDER-", confirmation_html)
            self.assertIn("Wireless Headphones", confirmation_html)

            history_text = (data_dir / "historial_compres.ttl").read_text(encoding="utf-8")
            self.assertIn("USER-1", history_text)
            self.assertIn("P1001", history_text)


if __name__ == "__main__":
    unittest.main()
