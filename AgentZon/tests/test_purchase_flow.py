"""Browser-style flow tests for search, purchase, and shipping coordination."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Namespace, RDF

from tests.support import LocalMessageRouter, load_catalog_products


class PurchaseFlowTests(unittest.TestCase):
    def test_acl_search_and_purchase_flow_uses_comm_endpoints_and_returns_embedded_order(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import ONTOLOGY_URI, AZON
        from agents import (
            agent_centre_logistic,
            agent_cercador,
            agent_compra,
            agent_directory,
            agent_opinador,
        )
        from protocols.centre_logistic import build_resposta_oferta_transport, extract_shipping_details
        from protocols.cerca import build_peticio_cerca, extract_result_products
        from protocols.compra import build_peticio_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data
        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        centre = Agent(
            "CentreLogisticAgent",
            agn.CentreLogistic,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )
        transport_fast = Agent(
            "TransportFast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        transport_economy = Agent(
            "TransportEconomy",
            agn.TransportEconomy,
            "http://transport-economy.test/comm",
            "http://transport-economy.test/Stop",
        )

        router = LocalMessageRouter()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            sample_product = load_catalog_products(data_dir / "productes.ttl")[0]
            search_token = sample_product["name"].split()[0]

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def transport_offer_sender(message, address):
                if address == transport_fast.address:
                    return build_resposta_oferta_transport(
                        {
                            "lot_id": "LOT-TEST",
                            "order_id": "ORDER-TEST",
                            "transport_id": "fast",
                            "transport_name": transport_fast.name,
                            "city": "Barcelona",
                            "delivery_date": "2026-05-06",
                            "price": 12.0,
                        },
                        sender=transport_fast.uri,
                        receiver=centre.uri,
                        msgcnt=10,
                    )
                if address == transport_economy.address:
                    return build_resposta_oferta_transport(
                        {
                            "lot_id": "LOT-TEST",
                            "order_id": "ORDER-TEST",
                            "transport_id": "economy",
                            "transport_name": transport_economy.name,
                            "city": "Barcelona",
                            "delivery_date": "2026-05-08",
                            "price": 6.0,
                        },
                        sender=transport_economy.uri,
                        receiver=centre.uri,
                        msgcnt=11,
                    )
                raise AssertionError(f"Unexpected transport address {address}")

            agent_centre_logistic.configure_runtime(
                {
                    "agent": centre,
                    "data_dir": data_dir,
                    "transport_agents": [transport_fast, transport_economy],
                },
                message_sender=transport_offer_sender,
            )
            router.register_app(cercador.address, agent_cercador.app)
            router.register_app(compra.address, agent_compra.app)
            router.register_app(centre.address, agent_centre_logistic.app)

            def fake_send_message(message, address):
                if address in {directory.address, opinador.address, centre.address}:
                    return router.send_message(message, address)
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

            search_graph, search_content = build_peticio_cerca(
                "search-request-1",
                text=search_token,
                category=sample_product["category"],
                brand=sample_product["brand"],
                min_price=sample_product["price"] - 0.01,
                max_price=sample_product["price"] + 0.01,
            )
            search_message = build_message(
                search_graph,
                perf=ACL.request,
                sender=cercador.uri,
                receiver=cercador.uri,
                content=search_content,
                ontology=ONTOLOGY_URI,
                msgcnt=20,
            )
            search_reply = router.send_message(search_message, cercador.address)
            search_props = get_message_properties(search_reply)
            self.assertEqual(search_props["performative"], ACL.inform)
            found_products = extract_result_products(search_reply, search_props["content"])
            self.assertIn(
                sample_product["product_id"],
                {product["product_id"] for product in found_products},
            )

            purchase_message = build_peticio_compra(
                "purchase-request-1",
                user_id="USER-1",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Carrer de Mallorca 401",
                    "city": "Barcelona",
                    "priority": "48h",
                },
                product_ids=[sample_product["product_id"]],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=21,
            )
            confirmation = router.send_message(purchase_message, compra.address)
            confirmation_props = get_message_properties(confirmation)
            self.assertEqual(confirmation_props["performative"], ACL.inform)
            shipping_details = extract_shipping_details(confirmation)
            self.assertEqual(shipping_details["transport_id"], "economy")
            self.assertTrue(shipping_details["order_id"].startswith("ORDER-"))

            confirmation_content = confirmation_props["content"]
            embedded_order = confirmation.value(confirmation_content, AZON.SobreComanda)
            self.assertIsNotNone(embedded_order)
            self.assertIn((embedded_order, RDF.type, AZON.Comanda), confirmation)
            self.assertEqual(
                {str(value).rsplit("product-", 1)[-1] for value in confirmation.objects(embedded_order, AZON.TeProducte)},
                {sample_product["product_id"]},
            )

            history_text = (data_dir / "historial_compres.ttl").read_text(encoding="utf-8")
            self.assertIn("USER-1", history_text)
            self.assertIn(sample_product["product_id"], history_text)

            search_history_text = (data_dir / "historial_cerques.ttl").read_text(encoding="utf-8")
            self.assertIn("TextConsulta", search_history_text)
            self.assertIn("CategoriaConsulta", search_history_text)
            self.assertIn("MarcaConsulta", search_history_text)
            self.assertIn("MostraProducte", search_history_text)
            self.assertNotIn("teText", search_history_text)
            self.assertNotIn("teCategoria", search_history_text)
            self.assertNotIn("teMarca", search_history_text)

            orders_text = (data_dir / "comandes.ttl").read_text(encoding="utf-8")
            lots_text = (data_dir / "lots.ttl").read_text(encoding="utf-8")

            self.assertIn("MetodePagament", orders_text)
            self.assertIn("SobreComanda", history_text)
            self.assertIn("TeProducte", lots_text)
            self.assertIn("PesTotal", lots_text)
            self.assertIn("TeProducte", orders_text)
            self.assertNotIn("idComanda", history_text)

    def test_browser_iface_flow_wraps_search_and_purchase_without_business_routes(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from agents import (
            agent_centre_logistic,
            agent_cercador,
            agent_compra,
            agent_directory,
            agent_opinador,
        )
        from protocols.centre_logistic import build_resposta_oferta_transport
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data
        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        cercador = Agent(
            "CercadorAgent",
            agn.Cercador,
            "http://cercador.test/comm",
            "http://cercador.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        centre = Agent(
            "CentreLogisticAgent",
            agn.CentreLogistic,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )
        transport_fast = Agent(
            "TransportFast",
            agn.TransportFast,
            "http://transport-fast.test/comm",
            "http://transport-fast.test/Stop",
        )
        transport_economy = Agent(
            "TransportEconomy",
            agn.TransportEconomy,
            "http://transport-economy.test/comm",
            "http://transport-economy.test/Stop",
        )

        router = LocalMessageRouter()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            sample_product = load_catalog_products(data_dir / "productes.ttl")[0]
            search_token = sample_product["name"].split()[0]

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def transport_offer_sender(message, address):
                if address == transport_fast.address:
                    return build_resposta_oferta_transport(
                        {
                            "lot_id": "LOT-TEST",
                            "order_id": "ORDER-TEST",
                            "transport_id": "fast",
                            "transport_name": transport_fast.name,
                            "city": "Barcelona",
                            "delivery_date": "2026-05-06",
                            "price": 12.0,
                        },
                        sender=transport_fast.uri,
                        receiver=centre.uri,
                        msgcnt=10,
                    )
                if address == transport_economy.address:
                    return build_resposta_oferta_transport(
                        {
                            "lot_id": "LOT-TEST",
                            "order_id": "ORDER-TEST",
                            "transport_id": "economy",
                            "transport_name": transport_economy.name,
                            "city": "Barcelona",
                            "delivery_date": "2026-05-08",
                            "price": 6.0,
                        },
                        sender=transport_economy.uri,
                        receiver=centre.uri,
                        msgcnt=11,
                    )
                raise AssertionError(f"Unexpected transport address {address}")

            agent_centre_logistic.configure_runtime(
                {
                    "agent": centre,
                    "data_dir": data_dir,
                    "transport_agents": [transport_fast, transport_economy],
                },
                message_sender=transport_offer_sender,
            )
            router.register_app(centre.address, agent_centre_logistic.app)

            def fake_send_message(message, address):
                if address in {directory.address, opinador.address, centre.address}:
                    return router.send_message(message, address)
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
            blank_page = search_client.get("/iface")
            self.assertEqual(blank_page.status_code, 200)

            search_response = search_client.post(
                "/iface",
                data={
                    "text": search_token,
                    "category": sample_product["category"],
                    "brand": sample_product["brand"],
                    "min_price": f"{sample_product['price'] - 0.01:.2f}",
                    "max_price": f"{sample_product['price'] + 0.01:.2f}",
                },
            )
            search_html = search_response.get_data(as_text=True)
            self.assertIn(sample_product["name"], search_html)
            self.assertIn("/iface", search_html)

            compra_client = agent_compra.app.test_client()
            purchase_page = compra_client.post(
                "/iface",
                data={"selected_product_ids": [sample_product["product_id"]]},
            )
            self.assertIn("Confirm purchase", purchase_page.get_data(as_text=True))

            confirmation = compra_client.post(
                "/iface",
                data={
                    "selected_product_ids": [sample_product["product_id"]],
                    "user_id": "USER-1",
                    "user_name": "Pol",
                    "street_address": "Carrer de Mallorca 401",
                    "city": "Barcelona",
                    "priority": "48h",
                    "payment_method": "placeholder-visa",
                },
            )
            confirmation_html = confirmation.get_data(as_text=True)
            self.assertIn("economy", confirmation_html)
            self.assertIn("ORDER-", confirmation_html)
            self.assertIn(sample_product["name"], confirmation_html)


if __name__ == "__main__":
    unittest.main()
