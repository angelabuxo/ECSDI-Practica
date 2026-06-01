"""Browser-style tests for deferred purchase confirmation and later shipping updates."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF

from tests.support import LocalMessageRouter, load_catalog_products


class PurchaseFlowTests(unittest.TestCase):
    def test_choose_logistics_centre_prefers_exact_match_then_centre_id_tiebreak(self):
        from services.logistics_routing_service import choose_logistics_centre_for_product

        selected = choose_logistics_centre_for_product(
            "Barcelna",
            [
                {
                    "name": "CentreLogisticAgent-CL-Z",
                    "uri": "http://www.agentes.org#CentreLogisticCLZ",
                    "address": "http://centre-z.test/comm",
                    "centre_id": "CL-Z",
                    "centre_city": "Barcelona",
                },
                {
                    "name": "CentreLogisticAgent-CL-A",
                    "uri": "http://www.agentes.org#CentreLogisticCLA",
                    "address": "http://centre-a.test/comm",
                    "centre_id": "CL-A",
                    "centre_city": "Barcelona",
                },
                {
                    "name": "CentreLogisticAgent-CL-GI",
                    "uri": "http://centre-gi.test/comm",
                    "address": "http://centre-gi.test/comm",
                    "centre_id": "CL-GI",
                    "centre_city": "Girona",
                },
            ],
        )

        self.assertEqual(selected["centre_id"], "CL-A")
        self.assertEqual(selected["centre_city"], "Barcelona")

    def test_single_product_purchase_produces_exactly_one_logistics_request(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_compra, agent_directory, agent_opinador
        from protocols.centre_logistic import build_confirmacio_localitzacio, parse_productes_localitzats
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        centre_bcn = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre-bcn.test/comm",
            "http://centre-bcn.test/Stop",
        )

        router = LocalMessageRouter()
        centre_requests = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            product = load_catalog_products(data_dir / "productes.ttl")[0]

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def fake_send_message(message, address):
                if address == centre_bcn.address:
                    centre_requests.append(address)
                    content = message.value(predicate=RDF.type, object=AZON.ProducteLocalitzat)
                    request_data = parse_productes_localitzats(message, content)
                    self.assertEqual(len(request_data["products"]), 1)
                    self.assertEqual(request_data["products"][0]["product_id"], product["product_id"])
                    return build_confirmacio_localitzacio(
                        request_data,
                        {
                            "lot_id": "LOT-CL-BCN-1",
                            "order_id": request_data["order_id"],
                            "city": request_data["city"],
                            "delivery_date": request_data["delivery_date"],
                            "status": "OBERT",
                            "products": request_data["products"],
                            "centre_id": "CL-BCN",
                            "centre_city": "Barcelona",
                        },
                        sender=centre_bcn.uri,
                        receiver=compra.uri,
                        request_content=content,
                        msgcnt=40,
                    )
                if address in {directory.address, opinador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=fake_send_message,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, centre_bcn, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: "CL-BCN", AZON.Ciutat: "Barcelona"}),
                (2, opinador, DSO.OpinadorAgent, None),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt, metadata=metadata)
                router.send_message(register_graph, directory.address)

            purchase_message = build_peticio_compra(
                "purchase-request-single",
                user_id="USER-1",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "7 dies",
                },
                product_ids=[product["product_id"]],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=20,
            )
            response = router.send_message(purchase_message, compra.address)
            parsed = extract_resultat_compra(response)

            self.assertEqual(centre_requests, [centre_bcn.address])
            self.assertEqual(parsed["status"], "OBERT")
            self.assertEqual(len(parsed["lots"]), 1)
            self.assertEqual(parsed["lots"][0]["centre_id"], "CL-BCN")

    def test_acl_purchase_flow_returns_immediate_result_and_later_order_status_page(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI
        from agents import agent_centre_logistic, agent_compra, agent_directory, agent_opinador
        from protocols.centre_logistic import build_resposta_oferta_transport
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        centre = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        transport_fast = Agent("TransportFast", agn.TransportFast, "http://transport-fast.test/comm", "http://transport-fast.test/Stop")
        transport_economy = Agent("TransportEconomy", agn.TransportEconomy, "http://transport-economy.test/comm", "http://transport-economy.test/Stop")

        router = LocalMessageRouter()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            sample_product = load_catalog_products(data_dir / "productes.ttl")[0]

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def centre_sender(message, address):
                if address == directory.address:
                    return router.send_message(message, address)
                if address == compra.address:
                    return router.send_message(message, address)
                if address == transport_fast.address:
                    return build_resposta_oferta_transport(
                        {
                            "lot_id": "LOT-TEST",
                            "order_id": "ORDER-TEST",
                            "transport_id": "fast",
                            "transport_name": transport_fast.name,
                            "city": "Barcelona",
                            "delivery_date": "2026-06-02",
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
                            "delivery_date": "2026-06-04",
                            "price": 6.0,
                        },
                        sender=transport_economy.uri,
                        receiver=centre.uri,
                        msgcnt=11,
                    )
                raise AssertionError(f"Unexpected address {address}")

            agent_centre_logistic.configure_runtime(
                {
                    "agent": centre,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                    "transport_agents": [transport_fast, transport_economy],
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
                message_sender=centre_sender,
            )
            router.register_app(centre.address, agent_centre_logistic.app)

            def compra_sender(message, address):
                if address in {directory.address, opinador.address, centre.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=compra_sender,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, compra, DSO.CompraAgent, None),
                (2, centre, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: "CL-BCN", AZON.Ciutat: "Barcelona"}),
                (3, opinador, DSO.OpinadorAgent, None),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt, metadata=metadata)
                router.send_message(register_graph, directory.address)

            purchase_message = build_peticio_compra(
                "purchase-request-1",
                user_id="USER-1",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Carrer de Mallorca 401",
                    "city": "Barcelona",
                    "priority": "24h",
                },
                product_ids=[sample_product["product_id"]],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=21,
            )
            confirmation = router.send_message(purchase_message, compra.address)
            confirmation_props = get_message_properties(confirmation)
            self.assertEqual(confirmation_props["performative"], ACL.inform)

            parsed = extract_resultat_compra(confirmation)
            self.assertEqual(parsed["status"], "OBERT")
            self.assertEqual(len(parsed["lots"]), 1)
            order_id = parsed["order_id"]

            cron_response = agent_centre_logistic.app.test_client().get("/cron/negotiate-ready-lots")
            self.assertEqual(cron_response.status_code, 200)

            order_page = agent_compra.app.test_client().get(f"/orders/{order_id}")
            self.assertEqual(order_page.status_code, 200)
            self.assertIn("economy", order_page.get_data(as_text=True))
            self.assertIn("ENVIAT", order_page.get_data(as_text=True))

    def test_purchase_flow_routes_products_per_centre_and_returns_multiple_lot_reservations(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON, bind_namespaces
        from agents import agent_compra, agent_directory, agent_opinador
        from protocols.centre_logistic import build_confirmacio_localitzacio, parse_productes_localitzats
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import save_graph

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        centre_bcn = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre-bcn.test/comm",
            "http://centre-bcn.test/Stop",
        )
        centre_gi = Agent(
            "CentreLogisticAgent-CL-GI",
            agn.CentreLogisticCLGI,
            "http://centre-gi.test/comm",
            "http://centre-gi.test/Stop",
        )

        router = LocalMessageRouter()
        centre_requests = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            products = load_catalog_products(data_dir / "productes.ttl")[:2]

            locations = Graph()
            bind_namespaces(locations)
            centre_nodes = {"CL-BCN": AZON["centre-BCN"], "CL-GI": AZON["centre-GI"]}
            for centre_id, city in [("CL-BCN", "Barcelona"), ("CL-GI", "Girona")]:
                centre_node = centre_nodes[centre_id]
                locations.add((centre_node, RDF.type, AZON.CentreLogistic))
                locations.add((centre_node, AZON.IdCentreLogistic, Literal(centre_id)))
                locations.add((centre_node, AZON.Ciutat, Literal(city)))
            locations.add((AZON[f"product-{products[0]['product_id']}"], AZON.UbicatACentre, centre_nodes["CL-BCN"]))
            locations.add((AZON[f"product-{products[0]['product_id']}"], AZON.UbicatACentre, centre_nodes["CL-GI"]))
            locations.add((AZON[f"product-{products[1]['product_id']}"], AZON.UbicatACentre, centre_nodes["CL-GI"]))
            save_graph(data_dir / "ubicacions_productes.ttl", locations)

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def fake_send_message(message, address):
                if address in {centre_bcn.address, centre_gi.address}:
                    centre_requests.append(address)
                    content = message.value(predicate=RDF.type, object=AZON.ProducteLocalitzat)
                    request_data = parse_productes_localitzats(message, content)
                    centre = {"centre_id": "CL-BCN", "centre_city": "Barcelona"} if address == centre_bcn.address else {"centre_id": "CL-GI", "centre_city": "Girona"}
                    return build_confirmacio_localitzacio(
                        request_data,
                        {
                            "lot_id": f"LOT-{centre['centre_id']}",
                            "order_id": request_data["order_id"],
                            "city": request_data["city"],
                            "delivery_date": request_data["delivery_date"],
                            "status": "OBERT",
                            "products": request_data["products"],
                            **centre,
                        },
                        sender=centre_gi.uri if address == centre_gi.address else centre_bcn.uri,
                        receiver=compra.uri,
                        request_content=content,
                        msgcnt=60,
                    )
                if address in {directory.address, opinador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=fake_send_message,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, (agent, centre_id, centre_city) in enumerate(
                [(centre_bcn, "CL-BCN", "Barcelona"), (centre_gi, "CL-GI", "Girona")],
                start=1,
            ):
                register_graph = build_register_message(
                    agent,
                    DSO.CentreLogisticAgent,
                    directory,
                    msgcnt=msgcnt,
                    metadata={AZON.IdCentreLogistic: centre_id, AZON.Ciutat: centre_city},
                )
                router.send_message(register_graph, directory.address)

            register_graph = build_register_message(opinador, DSO.OpinadorAgent, directory, msgcnt=50)
            router.send_message(register_graph, directory.address)

            purchase_message = build_peticio_compra(
                "purchase-request-2",
                user_id="USER-2",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "7 dies",
                },
                product_ids=[products[0]["product_id"], products[1]["product_id"]],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=20,
            )
            confirmation = router.send_message(purchase_message, compra.address)
            parsed = extract_resultat_compra(confirmation)

            self.assertEqual(centre_requests.count(centre_bcn.address), 1)
            self.assertEqual(centre_requests.count(centre_gi.address), 1)
            self.assertEqual(len(parsed["lots"]), 2)
            self.assertEqual(
                sorted((lot["centre_id"], lot["lot_id"]) for lot in parsed["lots"]),
                [("CL-BCN", "LOT-CL-BCN"), ("CL-GI", "LOT-CL-GI")],
            )

    def test_two_products_in_same_centre_use_one_grouped_routing_request(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON, bind_namespaces
        from agents import agent_compra, agent_directory, agent_opinador
        from protocols.centre_logistic import build_confirmacio_localitzacio, parse_productes_localitzats
        from protocols.compra import build_peticio_compra, extract_resultat_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import save_graph

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        compra = Agent("CompraAgent", agn.Compra, "http://compra.test/comm", "http://compra.test/Stop")
        opinador = Agent("OpinadorAgent", agn.Opinador, "http://opinador.test/comm", "http://opinador.test/Stop")
        centre_bcn = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre-bcn.test/comm",
            "http://centre-bcn.test/Stop",
        )

        router = LocalMessageRouter()
        centre_requests = []

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            bootstrap_phase2_data(data_dir, product_count=10, seed=21)
            products = load_catalog_products(data_dir / "productes.ttl")[:2]

            locations = Graph()
            bind_namespaces(locations)
            centre_node = AZON["centre-BCN"]
            locations.add((centre_node, RDF.type, AZON.CentreLogistic))
            locations.add((centre_node, AZON.IdCentreLogistic, Literal("CL-BCN")))
            locations.add((centre_node, AZON.Ciutat, Literal("Barcelona")))
            for product in products:
                locations.add((AZON[f"product-{product['product_id']}"], AZON.UbicatACentre, centre_node))
            save_graph(data_dir / "ubicacions_productes.ttl", locations)

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def fake_send_message(message, address):
                if address == centre_bcn.address:
                    content = message.value(predicate=RDF.type, object=AZON.ProducteLocalitzat)
                    request_data = parse_productes_localitzats(message, content)
                    centre_requests.append(request_data)
                    return build_confirmacio_localitzacio(
                        request_data,
                        {
                            "lot_id": "LOT-SHARED",
                            "order_id": request_data["order_id"],
                            "city": request_data["city"],
                            "delivery_date": request_data["delivery_date"],
                            "status": "OBERT",
                            "products": request_data["products"],
                            "centre_id": "CL-BCN",
                            "centre_city": "Barcelona",
                        },
                        sender=centre_bcn.uri,
                        receiver=compra.uri,
                        request_content=content,
                        msgcnt=60,
                    )
                if address in {directory.address, opinador.address}:
                    return router.send_message(message, address)
                raise AssertionError(f"Unexpected address {address}")

            agent_compra.configure_runtime(
                {"agent": compra, "directory_agent": directory, "data_dir": data_dir},
                message_sender=fake_send_message,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, centre_bcn, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: "CL-BCN", AZON.Ciutat: "Barcelona"}),
                (2, opinador, DSO.OpinadorAgent, None),
            ]:
                register_graph = build_register_message(agent, agent_type, directory, msgcnt=msgcnt, metadata=metadata)
                router.send_message(register_graph, directory.address)

            purchase_message = build_peticio_compra(
                "purchase-request-same-centre",
                user_id="USER-3",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "7 dies",
                },
                product_ids=[product["product_id"] for product in products],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=22,
            )
            confirmation = router.send_message(purchase_message, compra.address)
            parsed = extract_resultat_compra(confirmation)

            self.assertEqual(len(centre_requests), 1)
            self.assertEqual(
                sorted(product["product_id"] for product in centre_requests[0]["products"]),
                sorted(product["product_id"] for product in products),
            )
            self.assertEqual(len(parsed["lots"]), 1)
            self.assertEqual(parsed["lots"][0]["lot_id"], "LOT-SHARED")
            self.assertEqual(parsed["lots"][0]["centre_id"], "CL-BCN")


if __name__ == "__main__":
    unittest.main()
