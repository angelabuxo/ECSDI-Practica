"""Flow tests for lot lifecycle and deferred transport negotiation."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from rdflib import Graph, Namespace, RDF


class LogisticsFlowTests(unittest.TestCase):
    def test_centre_logistic_logs_product_level_lot_assignment(self):
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
                    "auto_trigger_ready_lots": False,
                }
            )

            request_data = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "city": "Barcelona",
                "delivery_date": "2026-06-02",
                "products": [
                    {"product_id": "P1", "name": "A", "weight": 1.0},
                    {"product_id": "P2", "name": "B", "weight": 2.0},
                ],
                "centre_id": "CL-BCN",
                "centre_city": "Barcelona",
            }

            with self.assertLogs("log", level="INFO") as captured:
                lot = agent_centre_logistic.pla_assignar_producte_a_lot(request_data)

            joined_logs = "\n".join(captured.output)
            self.assertNotIn("Assignant comanda ORDER-1", joined_logs)
            self.assertIn("Processant 2 productes al centre CL-BCN", joined_logs)
            self.assertIn(f"Assignat producte P1 al lot {lot['lot_id']}", joined_logs)
            self.assertIn(f"Assignat producte P2 al lot {lot['lot_id']}", joined_logs)

    def test_build_internal_shipment_preserves_lot_id_and_exact_product_ids(self):
        from services.logistics_service import build_internal_shipment

        shipment = build_internal_shipment(
            {
                "lot_id": "LOT-1",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "city": "Barcelona",
                "reservation_weight": 1.5,
                "products": [
                    {"product_id": "P1", "name": "A", "weight": 1.0},
                    {"product_id": "P2", "name": "B", "weight": 0.5},
                ],
            },
            {
                "delivery_date": "2026-06-02",
                "price": 9.0,
            },
            total_lot_weight=3.0,
        )

        self.assertEqual(shipment["lot_id"], "LOT-1")
        self.assertEqual(shipment["product_ids"], ["P1", "P2"])
        self.assertEqual(shipment["transport_cost"], 4.5)

    def test_internal_charge_request_roundtrips_lot_and_product_scope(self):
        from AgentUtil.Agent import Agent
        from protocols.pagament import build_peticio_cobrament_intern, parse_peticio_cobrament_intern

        agn = Namespace("http://www.agentes.org#")
        centre = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")

        message = build_peticio_cobrament_intern(
            {
                "lot_id": "LOT-1",
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "city": "Barcelona",
                "delivery_date": "2026-06-02",
                "transport_cost": 4.5,
                "product_ids": ["P1", "P2"],
            },
            sender=centre.uri,
            receiver=cobrador.uri,
            msgcnt=7,
        )
        content = next(message.subjects(RDF.type, Namespace("http://www.semanticweb.org/agentzon#").ConfirmacioEnviament))

        parsed = parse_peticio_cobrament_intern(message, content)

        self.assertEqual(parsed["lot_id"], "LOT-1")
        self.assertEqual(parsed["product_ids"], ["P1", "P2"])

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

    def test_choose_winning_offer_prefers_negotiated_pool(self):
        from services.logistics_service import choose_winning_offer

        initial_offers = [
            {
                "transport_id": "fast",
                "transport_name": "Transportista-fast",
                "price": 10.0,
                "delivery_date": "2026-05-06",
            },
            {
                "transport_id": "economy",
                "transport_name": "Transportista-economy",
                "price": 8.0,
                "delivery_date": "2026-05-08",
            },
        ]
        negotiated_offers = [
            {
                "transport_id": "fast",
                "transport_name": "Transportista-fast",
                "price": 7.5,
                "delivery_date": "2026-05-06",
            }
        ]

        selected = choose_winning_offer(initial_offers, negotiated_offers, chooser=lambda offers: offers[0])
        self.assertEqual(selected["transport_id"], "fast")

    def test_build_counter_offer_price_undercuts_cheapest_initial_offer(self):
        from services.logistics_service import build_counter_offer_price

        offers = [
            {"transport_id": "fast", "price": 10.0, "delivery_date": "2026-05-06"},
            {"transport_id": "economy", "price": 8.0, "delivery_date": "2026-05-08"},
        ]

        self.assertEqual(build_counter_offer_price(offers), 7.99)

    def test_create_lot_merges_products_for_same_city_and_delivery_date(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.logistics_service import create_lot
        from services.rdf_store import load_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"

            first_lot = create_lot(
                lots_path,
                order_id="ORDER-1",
                user_id="USER-1",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[{"product_id": "P1", "weight": 1.5}],
                centre_id="CL-BCN",
            )
            second_lot = create_lot(
                lots_path,
                order_id="ORDER-2",
                user_id="USER-2",
                city="Barcelona",
                delivery_date="2026-05-10",
                products=[{"product_id": "P2", "weight": 2.0}],
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

    def test_create_lot_closes_previous_open_lot_when_new_batch_would_overflow_capacity(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.logistics_service import create_lot
        from services.rdf_store import load_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            first = create_lot(
                lots_path,
                order_id="ORDER-1",
                user_id="USER-1",
                city="Barcelona",
                delivery_date="2026-06-02",
                products=[{"product_id": "P1", "name": "A", "weight": 4.6}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )
            second = create_lot(
                lots_path,
                order_id="ORDER-2",
                user_id="USER-2",
                city="Barcelona",
                delivery_date="2026-06-02",
                products=[{"product_id": "P2", "name": "B", "weight": 1.0}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )

            graph = load_graph(lots_path)
            first_node = AZON[f"lot-{first['lot_id']}"]
            second_node = AZON[f"lot-{second['lot_id']}"]

            self.assertNotEqual(first["lot_id"], second["lot_id"])
            self.assertEqual(str(graph.value(first_node, AZON.Estat)), "PREPARAT")
            self.assertEqual(str(graph.value(second_node, AZON.Estat)), "OBERT")

    def test_create_lot_marks_lot_ready_when_weight_cap_is_reached(self):
        from services.logistics_service import create_lot

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            lot = create_lot(
                lots_path,
                order_id="ORDER-1",
                user_id="USER-1",
                city="Barcelona",
                delivery_date="2026-06-02",
                products=[{"product_id": "P1", "name": "A", "weight": 5.0}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )

            self.assertEqual(lot["status"], "PREPARAT")
            self.assertTrue(lot["ready_for_negotiation"])

    def test_load_lot_by_id_returns_order_reservations_for_a_shared_lot(self):
        from services.logistics_service import create_lot, load_lot_by_id

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            first = create_lot(
                lots_path,
                order_id="ORDER-1",
                user_id="USER-1",
                city="Barcelona",
                delivery_date="2026-06-02",
                products=[{"product_id": "P1", "name": "A", "weight": 1.0}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )
            create_lot(
                lots_path,
                order_id="ORDER-2",
                user_id="USER-2",
                city="Barcelona",
                delivery_date="2026-06-02",
                products=[{"product_id": "P2", "name": "B", "weight": 1.0}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )

            loaded = load_lot_by_id(lots_path, first["lot_id"])

            self.assertEqual(loaded["order_ids"], ["ORDER-1", "ORDER-2"])
            self.assertEqual(
                sorted((reservation["order_id"], reservation["products"][0]["product_id"]) for reservation in loaded["reservations"]),
                [("ORDER-1", "P1"), ("ORDER-2", "P2")],
            )

    def test_list_ready_lots_promotes_due_soon_open_lots_once_per_daily_scan(self):
        from services.logistics_service import create_lot, list_ready_lots_for_negotiation

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            create_lot(
                lots_path,
                order_id="ORDER-1",
                user_id="USER-1",
                city="Barcelona",
                delivery_date="2026-06-01",
                products=[{"product_id": "P1", "name": "A", "weight": 1.0}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )
            create_lot(
                lots_path,
                order_id="ORDER-2",
                user_id="USER-2",
                city="Barcelona",
                delivery_date="2026-06-05",
                products=[{"product_id": "P2", "name": "B", "weight": 1.0}],
                centre_id="CL-BCN",
                centre_city="Barcelona",
            )

            ready = list_ready_lots_for_negotiation(
                lots_path,
                today=date(2026, 5, 31),
                delivery_window_days=1,
            )

            self.assertEqual(len(ready), 1)
            self.assertEqual(ready[0]["order_ids"], ["ORDER-1"])
            self.assertEqual(ready[0]["status"], "PREPARAT")

    def test_centre_logistic_queries_two_transport_agents_and_picks_the_cheapest_offer(self):
        from AgentUtil.ACLMessages import get_message_properties
        from AgentUtil.Agent import Agent
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_centre_logistic
        from protocols.centre_logistic import build_productes_localitzats, build_resposta_oferta_transport, parse_confirmacio_localitzacio

        agn = Namespace("http://www.agentes.org#")
        logistics_agent = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        fast_transport = Agent("TransportFast", agn.TransportFast, "http://transport-fast.test/comm", "http://transport-fast.test/Stop")
        economy_transport = Agent("TransportEconomy", agn.TransportEconomy, "http://transport-economy.test/comm", "http://transport-economy.test/Stop")

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
            agent_centre_logistic.configure_runtime(
                {
                    "agent": logistics_agent,
                    "data_dir": Path(tmpdir),
                    "transport_agents": [fast_transport, economy_transport],
                    "auto_trigger_ready_lots": False,
                },
                message_sender=fake_send_message,
            )

            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "shipping_data": {"city": "Barcelona", "priority": "24h"},
                "delivery_date": "2026-05-10",
                "products": [{"product_id": "P1001", "name": "Wireless Headphones", "weight": 5.0}],
            }
            request_graph, _ = build_productes_localitzats(order)

            response = agent_centre_logistic.app.test_client().get(
                "/comm",
                query_string={"content": request_graph.serialize(format="xml")},
            )
            parsed_graph = Graph()
            parsed_graph.parse(data=response.get_data(as_text=True), format="xml")
            properties = get_message_properties(parsed_graph)
            confirmation = parse_confirmacio_localitzacio(parsed_graph)

            self.assertEqual(str(properties["performative"]), "http://www.nuin.org/ontology/fipa/acl#inform")
            self.assertEqual(confirmation["status"], "PREPARAT")

            final_lot = agent_centre_logistic.process_ready_lot(confirmation["lot_id"])
            self.assertEqual(final_lot["transport_id"], "economy")
            self.assertEqual(final_lot["status"], "ENVIAT")

    def test_centre_logistic_negotiates_counter_offers_and_notifies_winner_and_loser(self):
        from rdflib import Graph

        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentUtil.Agent import Agent
        from agents import agent_centre_logistic
        from protocols.centre_logistic import build_productes_localitzats, build_resposta_oferta_transport, parse_confirmacio_localitzacio

        agn = Namespace("http://www.agentes.org#")
        logistics_agent = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        fast_transport = Agent("Transportista-fast", agn.TransportFast, "http://transport-fast.test/comm", "http://transport-fast.test/Stop")
        economy_transport = Agent("Transportista-economy", agn.TransportEconomy, "http://transport-economy.test/comm", "http://transport-economy.test/Stop")

        sent_performatives = []

        def fake_send_message(message, address):
            performative = get_message_properties(message)["performative"]
            sent_performatives.append((address, performative))
            if address == fast_transport.address:
                if performative == ACL.cfp:
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
                if performative == ACL.propose:
                    return build_message(Graph(), ACL.agree, sender=fast_transport.uri, receiver=logistics_agent.uri, msgcnt=2)
                if performative == ACL["accept-proposal"]:
                    return build_message(Graph(), ACL.inform, sender=fast_transport.uri, receiver=logistics_agent.uri, msgcnt=3)
                raise AssertionError(f"Unexpected fast transport performative {performative}")
            if address == economy_transport.address:
                if performative == ACL.cfp:
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
                        msgcnt=4,
                    )
                if performative == ACL.propose:
                    return build_message(Graph(), ACL.refuse, sender=economy_transport.uri, receiver=logistics_agent.uri, msgcnt=5)
                if performative == ACL["reject-proposal"]:
                    return build_message(Graph(), ACL.inform, sender=economy_transport.uri, receiver=logistics_agent.uri, msgcnt=6)
                raise AssertionError(f"Unexpected economy transport performative {performative}")
            raise AssertionError(f"Unexpected address {address}")

        with tempfile.TemporaryDirectory() as tmpdir:
            agent_centre_logistic.configure_runtime(
                {
                    "agent": logistics_agent,
                    "data_dir": Path(tmpdir),
                    "transport_agents": [fast_transport, economy_transport],
                    "auto_trigger_ready_lots": False,
                },
                message_sender=fake_send_message,
            )

            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "shipping_data": {"city": "Barcelona", "priority": "24h"},
                "delivery_date": "2026-05-10",
                "products": [{"product_id": "P1001", "name": "Wireless Headphones", "weight": 5.0}],
            }
            request_graph, _ = build_productes_localitzats(order)

            response = agent_centre_logistic.app.test_client().get(
                "/comm",
                query_string={"content": request_graph.serialize(format="xml")},
            )
            parsed_graph = Graph()
            parsed_graph.parse(data=response.get_data(as_text=True), format="xml")
            confirmation = parse_confirmacio_localitzacio(parsed_graph)

            agent_centre_logistic.process_ready_lot(confirmation["lot_id"])

            self.assertIn((fast_transport.address, ACL.cfp), sent_performatives)
            self.assertIn((economy_transport.address, ACL.cfp), sent_performatives)
            self.assertIn((fast_transport.address, ACL.propose), sent_performatives)
            self.assertIn((economy_transport.address, ACL.propose), sent_performatives)
            self.assertIn((fast_transport.address, ACL["accept-proposal"]), sent_performatives)
            self.assertIn((economy_transport.address, ACL["reject-proposal"]), sent_performatives)

    def test_centre_logistic_logs_negotiation_steps(self):
        from rdflib import Graph

        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentUtil.Agent import Agent
        from agents import agent_centre_logistic
        from protocols.centre_logistic import build_productes_localitzats, build_resposta_oferta_transport, parse_confirmacio_localitzacio

        agn = Namespace("http://www.agentes.org#")
        logistics_agent = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        fast_transport = Agent("Transportista-fast", agn.TransportFast, "http://transport-fast.test/comm", "http://transport-fast.test/Stop")
        economy_transport = Agent("Transportista-economy", agn.TransportEconomy, "http://transport-economy.test/comm", "http://transport-economy.test/Stop")

        def fake_send_message(message, address):
            performative = get_message_properties(message)["performative"]
            if address == fast_transport.address:
                if performative == ACL.cfp:
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
                if performative == ACL.propose:
                    return build_message(Graph(), ACL.agree, sender=fast_transport.uri, receiver=logistics_agent.uri, msgcnt=2)
                if performative == ACL["accept-proposal"]:
                    return build_message(Graph(), ACL.inform, sender=fast_transport.uri, receiver=logistics_agent.uri, msgcnt=3)
            if address == economy_transport.address:
                if performative == ACL.cfp:
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
                        msgcnt=4,
                    )
                if performative == ACL.propose:
                    return build_message(Graph(), ACL.refuse, sender=economy_transport.uri, receiver=logistics_agent.uri, msgcnt=5)
                if performative == ACL["reject-proposal"]:
                    return build_message(Graph(), ACL.inform, sender=economy_transport.uri, receiver=logistics_agent.uri, msgcnt=6)
            raise AssertionError(f"Unexpected address {address}")

        with tempfile.TemporaryDirectory() as tmpdir:
            agent_centre_logistic.configure_runtime(
                {
                    "agent": logistics_agent,
                    "data_dir": Path(tmpdir),
                    "transport_agents": [fast_transport, economy_transport],
                    "auto_trigger_ready_lots": False,
                },
                message_sender=fake_send_message,
            )

            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "shipping_data": {"city": "Barcelona", "priority": "24h"},
                "delivery_date": "2026-05-10",
                "products": [{"product_id": "P1001", "name": "Wireless Headphones", "weight": 5.0}],
            }
            request_graph, _ = build_productes_localitzats(order)
            response = agent_centre_logistic.app.test_client().get(
                "/comm",
                query_string={"content": request_graph.serialize(format="xml")},
            )

            parsed_graph = Graph()
            parsed_graph.parse(data=response.get_data(as_text=True), format="xml")
            confirmation = parse_confirmacio_localitzacio(parsed_graph)
            lot_id = confirmation["lot_id"]

            with self.assertLogs("log", level="INFO") as captured:
                agent_centre_logistic.process_ready_lot(lot_id)

            joined_logs = "\n".join(captured.output)
            self.assertIn(f"Iniciant negociacio del lot {lot_id}", joined_logs)
            self.assertIn(f"Oferta inicial rebuda per al lot {lot_id}: fast", joined_logs)
            self.assertIn(f"Oferta inicial rebuda per al lot {lot_id}: economy", joined_logs)
            self.assertIn(f"Contraoferta comuna per al lot {lot_id}: 5.99 EUR", joined_logs)
            self.assertIn(f"Resposta a la contraoferta del lot {lot_id} per fast: acceptada", joined_logs)
            self.assertIn(f"Resposta a la contraoferta del lot {lot_id} per economy: rebutjada", joined_logs)
            self.assertIn(f"Transportista seleccionat per al lot {lot_id}: fast", joined_logs)

    def test_centre_logistic_discovers_transport_agents_from_directory(self):
        from rdflib import Graph

        from AgentUtil.Agent import Agent
        from AgentUtil.DSO import DSO
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_centre_logistic, agent_directory
        from protocols.centre_logistic import build_productes_localitzats, build_resposta_oferta_transport, parse_confirmacio_localitzacio
        from protocols.directory import build_register_message
        from tests.support import LocalMessageRouter

        agn = Namespace("http://www.agentes.org#")
        directory = Agent("DirectoryAgent", agn.Directory, "http://directory.test/Register", "http://directory.test/Stop")
        logistics_agent = Agent(
            "CentreLogisticAgent-CL-BCN",
            agn.CentreLogisticCLBCN,
            "http://centre.test/comm",
            "http://centre.test/Stop",
        )
        fast_transport = Agent("Transportista-fast", agn.TransportFast, "http://transport-fast.test/comm", "http://transport-fast.test/Stop")
        economy_transport = Agent("Transportista-economy", agn.TransportEconomy, "http://transport-economy.test/comm", "http://transport-economy.test/Stop")

        agent_directory.configure_runtime({"agent": directory})
        router = LocalMessageRouter()
        router.register_app(directory.address, agent_directory.app)

        for msgcnt, (agent, transport_id) in enumerate([(fast_transport, "fast"), (economy_transport, "economy")], start=1):
            register_graph = build_register_message(
                agent,
                DSO.TransportistaAgent,
                directory,
                msgcnt=msgcnt,
                metadata={AZON.IdTransportista: transport_id},
            )
            router.send_message(register_graph, directory.address)

        def fake_send_message(message, address):
            if address == directory.address:
                return router.send_message(message, address)
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
            agent_centre_logistic.configure_runtime(
                {
                    "agent": logistics_agent,
                    "directory_agent": directory,
                    "data_dir": Path(tmpdir),
                    "transport_agents": [],
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                    "auto_trigger_ready_lots": False,
                },
                message_sender=fake_send_message,
            )

            order = {
                "order_id": "ORDER-1",
                "user_id": "USER-1",
                "shipping_data": {"city": "Barcelona", "priority": "24h"},
                "delivery_date": "2026-05-10",
                "products": [{"product_id": "P1001", "name": "Wireless Headphones", "weight": 5.0}],
            }
            request_graph, _ = build_productes_localitzats(order)
            response = agent_centre_logistic.app.test_client().get(
                "/comm",
                query_string={"content": request_graph.serialize(format="xml")},
            )

            parsed_graph = Graph()
            parsed_graph.parse(data=response.get_data(as_text=True), format="xml")
            confirmation = parse_confirmacio_localitzacio(parsed_graph)

            final_lot = agent_centre_logistic.process_ready_lot(confirmation["lot_id"])
            self.assertEqual(final_lot["transport_id"], "economy")


if __name__ == "__main__":
    unittest.main()
