"""Browser-style flow tests for search, purchase, and shipping coordination."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace


class PurchaseFlowTests(unittest.TestCase):
    def test_browser_search_and_simple_order_flow_records_history_and_returns_shipping_summary(self):
        from AgentZon.AgentUtil.Agent import Agent
        from AgentZon.AgentUtil.DSO import DSO
        from AgentZon.AgentUtil.ACLMessages import get_message_properties
        from AgentZon.agents import agent_cercador, agent_compra, agent_directory, agent_opinador
        from AgentZon.protocols.centre_logistic import (
            build_shipping_details_response,
            parse_productes_localitzats,
        )
        from AgentZon.protocols.compra import build_confirmacio_registre_compra
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

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def fake_send_message(message, address):
                if address == directory.address:
                    return router.send_message(message, address)
                if address == opinador.address:
                    return router.send_message(message, address)
                if address == centre.address:
                    props = get_message_properties(message)
                    localized = parse_productes_localitzats(message, props["content"])
                    return build_shipping_details_response(
                        localized["order_id"],
                        localized["city"],
                        {
                            "lot_id": "LOT-TEST",
                            "transport_id": "economy",
                            "transport_name": "TransportEconomy",
                            "city": localized["city"],
                            "delivery_date": "2026-05-08",
                            "price": 6.0,
                        },
                        sender=centre.uri,
                        receiver=compra.uri,
                        msgcnt=2,
                    )
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {
                    "agent": compra,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                },
                message_sender=fake_send_message,
            )
            agent_cercador.configure_runtime(
                {
                    "agent": cercador,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                },
                message_sender=fake_send_message,
            )

            for agent, agent_type in [
                (cercador, DSO.CercadorAgent),
                (compra, DSO.CompraAgent),
                (centre, DSO.CentreLogisticAgent),
                (opinador, DSO.OpinadorAgent),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=1)
                router.send_message(register_graph, directory.address)

            search_client = agent_cercador.app.test_client()
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

            compra_client = agent_compra.app.test_client()
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
