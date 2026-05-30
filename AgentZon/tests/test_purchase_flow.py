"""Browser-style flow tests for search, purchase, and shipping coordination."""

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
                    "uri": "http://www.agentes.org#CentreLogisticCLGI",
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
        from protocols.centre_logistic import build_shipping_details_response, parse_productes_localitzats
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
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )
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
                    return build_shipping_details_response(
                        request_data,
                        {
                            "lot_id": "LOT-CL-BCN-1",
                            "order_id": request_data["order_id"],
                            "transport_id": "economy",
                            "transport_name": "TransportEconomy",
                            "city": request_data["city"],
                            "delivery_date": "2026-06-01",
                            "price": 4.0,
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
                {
                    "agent": compra,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                },
                message_sender=fake_send_message,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, centre_bcn, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: "CL-BCN", AZON.Ciutat: "Barcelona"}),
                (2, opinador, DSO.OpinadorAgent, None),
            ]:
                register_graph = build_register_message(
                    agent,
                    agent_type,
                    directory,
                    msgcnt=msgcnt,
                    metadata=metadata,
                )
                router.send_message(register_graph, directory.address)

            purchase_message = build_peticio_compra(
                "purchase-request-single",
                user_id="USER-1",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "48h",
                },
                product_ids=[product["product_id"]],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=20,
            )
            router.send_message(purchase_message, compra.address)

            self.assertEqual(centre_requests, [centre_bcn.address])

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

    def test_purchase_flow_routes_products_per_centre_and_returns_multiple_shipments(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON, ONTOLOGY_URI, bind_namespaces
        from agents import (
            agent_compra,
            agent_directory,
            agent_opinador,
        )
        from protocols.centre_logistic import (
            build_shipping_details_response,
            extract_shipping_details_list,
            parse_productes_localitzats,
        )
        from protocols.compra import build_peticio_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import save_graph

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )
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
            centre_nodes = {
                "CL-BCN": AZON["centre-BCN"],
                "CL-GI": AZON["centre-GI"],
            }
            for centre_id, city in [("CL-BCN", "Barcelona"), ("CL-GI", "Girona")]:
                centre_node = centre_nodes[centre_id]
                locations.add((centre_node, RDF.type, AZON.CentreLogistic))
                locations.add((centre_node, AZON.IdCentreLogistic, Literal(centre_id)))
                locations.add((centre_node, AZON.Ciutat, Literal(city)))

            product_one = AZON[f"product-{products[0]['product_id']}"]
            product_two = AZON[f"product-{products[1]['product_id']}"]
            locations.add((product_one, AZON.UbicatACentre, centre_nodes["CL-BCN"]))
            locations.add((product_one, AZON.UbicatACentre, centre_nodes["CL-GI"]))
            locations.add((product_two, AZON.UbicatACentre, centre_nodes["CL-GI"]))
            save_graph(data_dir / "ubicacions_productes.ttl", locations)

            agent_directory.configure_runtime({"agent": directory})
            router.register_app(directory.address, agent_directory.app)
            agent_opinador.configure_runtime({"agent": opinador, "data_dir": data_dir})
            router.register_app(opinador.address, agent_opinador.app)

            def fake_send_message(message, address):
                if address in {centre_bcn.address, centre_gi.address}:
                    centre_requests.append(address)
                    content = get_message_properties(message)["content"]
                    request_data = parse_productes_localitzats(message, content)
                    centre = (
                        {"centre_id": "CL-BCN", "centre_city": "Barcelona"}
                        if address == centre_bcn.address
                        else {"centre_id": "CL-GI", "centre_city": "Girona"}
                    )
                    offer = {
                        "lot_id": f"LOT-{centre['centre_id']}",
                        "order_id": request_data["order_id"],
                        "transport_id": "economy",
                        "transport_name": "TransportEconomy",
                        "city": request_data["city"],
                        "delivery_date": "2026-06-03" if centre["centre_id"] == "CL-GI" else "2026-06-01",
                        "price": 4.0,
                    }
                    return build_shipping_details_response(
                        request_data,
                        offer,
                        sender=centre_gi.uri if address == centre_gi.address else centre_bcn.uri,
                        receiver=compra.uri,
                        request_content=content,
                        msgcnt=60,
                    )
                if address in {directory.address, opinador.address}:
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
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, (agent, centre_id, centre_city) in enumerate(
                [
                    (centre_bcn, "CL-BCN", "Barcelona"),
                    (centre_gi, "CL-GI", "Girona"),
                ],
                start=1,
            ):
                register_graph = build_register_message(
                    agent,
                    DSO.CentreLogisticAgent,
                    directory,
                    msgcnt=msgcnt,
                    metadata={
                        AZON.IdCentreLogistic: centre_id,
                        AZON.Ciutat: centre_city,
                    },
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
                    "priority": "48h",
                },
                product_ids=[products[0]["product_id"], products[1]["product_id"]],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=20,
            )
            confirmation = router.send_message(purchase_message, compra.address)

            self.assertEqual(centre_requests.count(centre_bcn.address), 1)
            self.assertEqual(centre_requests.count(centre_gi.address), 1)

            shipments = extract_shipping_details_list(confirmation)
            self.assertEqual(len(shipments), 2)
            self.assertEqual(
                sorted((shipment["product_id"], shipment["centre_id"]) for shipment in shipments),
                sorted(
                    [
                        (products[0]["product_id"], "CL-BCN"),
                        (products[1]["product_id"], "CL-GI"),
                    ]
                ),
            )

            confirmation_props = get_message_properties(confirmation)
            self.assertEqual(confirmation_props["performative"], ACL.inform)
            confirmation_content = confirmation_props["content"]
            self.assertEqual(
                str(confirmation.value(confirmation_content, AZON.DataEntregaDefinitiva)),
                "2026-06-03",
            )

    def test_two_products_in_same_centre_use_one_grouped_routing_request(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON, bind_namespaces
        from agents import agent_compra, agent_directory, agent_opinador
        from protocols.centre_logistic import build_shipping_details_response, extract_shipping_details_list, parse_productes_localitzats
        from protocols.compra import build_peticio_compra
        from protocols.directory import build_register_message
        from services.bootstrap import bootstrap_phase2_data
        from services.rdf_store import save_graph

        agn = Namespace("http://www.agentes.org#")
        directory = Agent(
            "DirectoryAgent",
            agn.Directory,
            "http://directory.test/Register",
            "http://directory.test/Stop",
        )
        compra = Agent(
            "CompraAgent",
            agn.Compra,
            "http://compra.test/comm",
            "http://compra.test/Stop",
        )
        opinador = Agent(
            "OpinadorAgent",
            agn.Opinador,
            "http://opinador.test/comm",
            "http://opinador.test/Stop",
        )
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
                    return build_shipping_details_response(
                        request_data,
                        {
                            "lot_id": "LOT-SHARED",
                            "order_id": request_data["order_id"],
                            "transport_id": "economy",
                            "transport_name": "TransportEconomy",
                            "city": request_data["city"],
                            "delivery_date": "2026-06-01",
                            "price": 4.0,
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
                {
                    "agent": compra,
                    "directory_agent": directory,
                    "data_dir": data_dir,
                },
                message_sender=fake_send_message,
            )
            router.register_app(compra.address, agent_compra.app)

            for msgcnt, agent, agent_type, metadata in [
                (1, centre_bcn, DSO.CentreLogisticAgent, {AZON.IdCentreLogistic: "CL-BCN", AZON.Ciutat: "Barcelona"}),
                (2, opinador, DSO.OpinadorAgent, None),
            ]:
                register_graph = build_register_message(
                    agent,
                    agent_type,
                    directory,
                    msgcnt=msgcnt,
                    metadata=metadata,
                )
                router.send_message(register_graph, directory.address)

            purchase_message = build_peticio_compra(
                "purchase-request-same-centre",
                user_id="USER-3",
                payment_method="placeholder-visa",
                shipping_data={
                    "user_name": "Pol",
                    "street_address": "Gran Via 100",
                    "city": "Barcelona",
                    "priority": "48h",
                },
                product_ids=[product["product_id"] for product in products],
                sender=compra.uri,
                receiver=compra.uri,
                msgcnt=22,
            )
            confirmation = router.send_message(purchase_message, compra.address)

            self.assertEqual(len(centre_requests), 1)
            self.assertEqual(
                sorted(product["product_id"] for product in centre_requests[0]["products"]),
                sorted(product["product_id"] for product in products),
            )

            shipments = extract_shipping_details_list(confirmation)
            self.assertEqual(len(shipments), 2)
            self.assertEqual({shipment["centre_id"] for shipment in shipments}, {"CL-BCN"})
            self.assertEqual({shipment["lot_id"] for shipment in shipments}, {"LOT-SHARED"})
            self.assertEqual({shipment["transport_id"] for shipment in shipments}, {"economy"})

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
