"""Flow tests for lot lifecycle and deferred transport negotiation."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from rdflib import Graph, Namespace, RDF


class LogisticsFlowTests(unittest.TestCase):
    @staticmethod
    def _localized_request(order, product=None):
        product = product or order["products"][0]
        return {
            "localized_product_id": f"ploc-{product['product_id'].lower()}",
            "user_id": order["user_id"],
            "city": order["shipping_data"]["city"],
            "delivery_date": order["delivery_date"],
            "product": product,
        }

    def test_create_lot_persists_producte_localitzat_items_not_reservations(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.logistics_service import create_lot
        from services.rdf_store import load_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            lot = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-9a13e6",
                    "user_id": "127.0.0.1",
                    "city": "Girona",
                    "delivery_date": "2026-06-06",
                    "product": {"product_id": "P1011", "name": "X", "weight": 1.5},
                    "centre_id": "CL-GI",
                    "centre_city": "Girona",
                },
            )
            graph = load_graph(lots_path)
            self.assertEqual(0, len(list(graph.subjects(RDF.type, AZON.ConfirmacioLocalitzacio))))
            items = list(graph.subjects(RDF.type, AZON.ProducteLocalitzat))
            self.assertEqual(1, len(items))
            self.assertEqual(AZON["lot-" + lot["lot_id"]], graph.value(items[0], AZON.SobreLot))

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
                "localized_product_id": "ploc-test-1",
                "user_id": "USER-1",
                "city": "Barcelona",
                "delivery_date": "2026-06-02",
                "product": {"product_id": "P1", "name": "A", "weight": 1.0},
                "centre_id": "CL-BCN",
                "centre_city": "Barcelona",
            }

            with self.assertLogs("log", level="INFO") as captured:
                lot = agent_centre_logistic.pla_assignar_producte_a_lot(request_data)

            joined_logs = "\n".join(captured.output)
            self.assertNotIn("Assignant comanda ORDER-1", joined_logs)
            self.assertIn("Processant producte P1 al centre CL-BCN", joined_logs)
            self.assertIn(f"Assignat producte P1 al lot {lot['lot_id']}", joined_logs)

    def test_build_internal_shipment_preserves_lot_id_and_product_id(self):
        from services.logistics_service import build_internal_shipment

        shipment = build_internal_shipment(
            {
                "localized_product_id": "ploc-9a13e6",
                "lot_id": "LOT-1",
                "user_id": "USER-1",
                "city": "Barcelona",
                "product": {"product_id": "P1", "name": "A", "weight": 1.5},
            },
            {
                "delivery_date": "2026-06-02",
                "price": 9.0,
            },
            total_lot_weight=3.0,
        )

        self.assertEqual(shipment["lot_id"], "LOT-1")
        self.assertEqual(shipment["product"]["product_id"], "P1")
        self.assertEqual(shipment["localized_product_id"], "ploc-9a13e6")
        self.assertEqual(shipment["transport_cost"], 4.5)

    def test_charge_request_roundtrips_user_and_price_scope(self):
        from AgentUtil.Agent import Agent
        from AgentUtil.OntoNamespaces import AZON
        from protocols.pagament import build_peticio_cobrament, parse_peticio_cobrament

        agn = Namespace("http://www.agentes.org#")
        centre = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        cobrador = Agent("CobradorAgent", agn.Cobrador, "http://cobrador.test/comm", "http://cobrador.test/Stop")

        message = build_peticio_cobrament(
            {
                "user_id": "USER-1",
                "preu_producte": 50.0,
                "cost_transport": 4.5,
            },
            sender=centre.uri,
            receiver=cobrador.uri,
            msgcnt=7,
        )
        content = next(message.subjects(RDF.type, AZON.PeticioCobrament))

        parsed = parse_peticio_cobrament(message, content)

        self.assertEqual(parsed["user_id"], "USER-1")
        self.assertEqual(parsed["preu_producte"], 50.0)
        self.assertEqual(parsed["cost_transport"], 4.5)

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

    def test_premium_counter_and_cap_are_based_on_low_offer(self):
        from services.logistics_service import (
            build_premium_counter_price,
            build_premium_price_cap,
            split_low_and_high_offers,
        )

        offers = [
            {"transport_id": "fast", "price": 40.0, "delivery_date": "2026-05-06"},
            {"transport_id": "economy", "price": 20.0, "delivery_date": "2026-05-08"},
        ]
        low_offer, high_offer = split_low_and_high_offers(offers)

        self.assertEqual(low_offer["transport_id"], "economy")
        self.assertEqual(high_offer["transport_id"], "fast")
        self.assertEqual(build_premium_counter_price(low_offer), 22.0)
        self.assertEqual(build_premium_price_cap(low_offer), 23.0)

    def test_select_offer_after_premium_negotiation(self):
        from AgentUtil.ACL import ACL
        from services.logistics_service import select_offer_after_premium_negotiation

        low_offer = {
            "transport_id": "economy",
            "transport_name": "Transportista-economy",
            "price": 20.0,
            "delivery_date": "2026-05-08",
        }
        high_offer = {
            "transport_id": "fast",
            "transport_name": "Transportista-fast",
            "price": 40.0,
            "delivery_date": "2026-05-06",
        }

        agreed = select_offer_after_premium_negotiation(
            low_offer,
            high_offer,
            counter_price=22.0,
            cap_price=23.0,
            premium_performative=ACL.agree,
        )
        self.assertEqual(agreed["transport_id"], "fast")
        self.assertEqual(agreed["price"], 22.0)

        proposed_ok = select_offer_after_premium_negotiation(
            low_offer,
            high_offer,
            counter_price=22.0,
            cap_price=23.0,
            premium_performative=ACL.propose,
            premium_negotiated_offer={**high_offer, "price": 23.0},
        )
        self.assertEqual(proposed_ok["transport_id"], "fast")
        self.assertEqual(proposed_ok["price"], 23.0)

        fallback = select_offer_after_premium_negotiation(
            low_offer,
            high_offer,
            counter_price=22.0,
            cap_price=23.0,
            premium_performative=ACL.propose,
            premium_negotiated_offer={**high_offer, "price": 30.0},
        )
        self.assertEqual(fallback["transport_id"], "economy")
        self.assertEqual(fallback["price"], 20.0)

    def test_create_lot_merges_products_for_same_city_and_delivery_date(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.logistics_service import create_lot
        from services.rdf_store import load_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"

            first_lot = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p1",
                    "user_id": "USER-1",
                    "city": "Barcelona",
                    "delivery_date": "2026-05-10",
                    "product": {"product_id": "P1", "weight": 1.5},
                    "centre_id": "CL-BCN",
                },
            )
            second_lot = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p2",
                    "user_id": "USER-2",
                    "city": "Barcelona",
                    "delivery_date": "2026-05-10",
                    "product": {"product_id": "P2", "weight": 2.0},
                    "centre_id": "CL-BCN",
                },
            )
            self.assertTrue(first_lot["created_new_lot"])
            self.assertFalse(second_lot["created_new_lot"])

            graph = load_graph(lots_path)
            lots = list(graph.subjects(RDF.type, AZON.Lot))
            self.assertEqual(len(lots), 1)
            self.assertEqual(first_lot["lot_id"], second_lot["lot_id"])

            lot = lots[0]
            self.assertEqual(float(graph.value(lot, AZON.PesTotal)), 3.5)
            items = list(graph.subjects(RDF.type, AZON.ProducteLocalitzat))
            self.assertEqual(len(items), 2)
            self.assertEqual(
                {str(graph.value(item, AZON.SobreLot)) for item in items},
                {str(lot)},
            )

    def test_create_lot_marks_lot_ready_when_adding_product_exceeds_weight_cap(self):
        from AgentUtil.OntoNamespaces import AZON
        from services.logistics_service import create_lot
        from services.rdf_store import load_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            first = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p1",
                    "user_id": "USER-1",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-02",
                    "product": {"product_id": "P1", "name": "A", "weight": 4.6},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )
            second = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p2",
                    "user_id": "USER-2",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-02",
                    "product": {"product_id": "P2", "name": "B", "weight": 1.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )

            graph = load_graph(lots_path)
            lot_node = AZON[f"lot-{first['lot_id']}"]

            self.assertEqual(first["lot_id"], second["lot_id"])
            self.assertEqual(second["status"], "PREPARAT")
            self.assertTrue(second["ready_for_negotiation"])
            self.assertEqual(float(graph.value(lot_node, AZON.PesTotal)), 5.6)
            self.assertEqual(str(graph.value(lot_node, AZON.Estat)), "PREPARAT")
            self.assertEqual(len(list(graph.subjects(RDF.type, AZON.Lot))), 1)

            third = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p3",
                    "user_id": "USER-3",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-02",
                    "product": {"product_id": "P3", "name": "C", "weight": 1.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )
            self.assertNotEqual(third["lot_id"], first["lot_id"])
            self.assertTrue(third["created_new_lot"])
            self.assertEqual(third["status"], "OBERT")

            graph = load_graph(lots_path)
            self.assertEqual(len(list(graph.subjects(RDF.type, AZON.Lot))), 2)

    def test_create_lot_marks_lot_ready_when_weight_cap_is_reached(self):
        from services.logistics_service import create_lot

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            lot = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-heavy",
                    "user_id": "USER-1",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-02",
                    "product": {"product_id": "P1", "name": "A", "weight": 5.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )

            self.assertEqual(lot["status"], "PREPARAT")
            self.assertTrue(lot["ready_for_negotiation"])

    def test_load_lot_by_id_returns_items_for_a_shared_lot(self):
        from services.logistics_service import create_lot, load_lot_by_id

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            first = create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p1",
                    "user_id": "USER-1",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-02",
                    "product": {"product_id": "P1", "name": "A", "weight": 1.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )
            create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-p2",
                    "user_id": "USER-2",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-02",
                    "product": {"product_id": "P2", "name": "B", "weight": 1.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )

            loaded = load_lot_by_id(lots_path, first["lot_id"])

            self.assertEqual(len(loaded["items"]), 2)
            self.assertEqual(
                sorted((item["product"]["product_id"], item["user_id"]) for item in loaded["items"]),
                [("P1", "USER-1"), ("P2", "USER-2")],
            )

    def test_list_ready_lots_promotes_due_soon_open_lots_once_per_daily_scan(self):
        from services.logistics_service import create_lot, list_ready_lots_for_negotiation

        with tempfile.TemporaryDirectory() as tmpdir:
            lots_path = Path(tmpdir) / "lots.ttl"
            create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-due",
                    "user_id": "USER-1",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-01",
                    "product": {"product_id": "P1", "name": "A", "weight": 1.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )
            create_lot(
                lots_path,
                {
                    "localized_product_id": "ploc-later",
                    "user_id": "USER-2",
                    "city": "Barcelona",
                    "delivery_date": "2026-06-05",
                    "product": {"product_id": "P2", "name": "B", "weight": 1.0},
                    "centre_id": "CL-BCN",
                    "centre_city": "Barcelona",
                },
            )

            ready = list_ready_lots_for_negotiation(
                lots_path,
                today=date(2026, 5, 31),
                delivery_window_days=1,
            )

            self.assertEqual(len(ready), 1)
            self.assertEqual(ready[0]["status"], "PREPARAT")

    def test_centre_logistic_assigns_premium_offer_when_negotiation_succeeds(self):
        from rdflib import Graph

        from AgentUtil.ACL import ACL
        from AgentUtil.ACLMessages import build_message, get_message_properties
        from AgentUtil.Agent import Agent
        from AgentUtil.OntoNamespaces import AZON
        from agents import agent_centre_logistic
        from protocols.centre_logistic import build_productes_localitzats, build_resposta_oferta_transport, parse_confirmacio_localitzacio

        agn = Namespace("http://www.agentes.org#")
        logistics_agent = Agent("CentreLogisticAgent", agn.CentreLogistic, "http://centre.test/comm", "http://centre.test/Stop")
        fast_transport = Agent("TransportFast", agn.TransportFast, "http://transport-fast.test/comm", "http://transport-fast.test/Stop")
        economy_transport = Agent("TransportEconomy", agn.TransportEconomy, "http://transport-economy.test/comm", "http://transport-economy.test/Stop")

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
                        msgcnt=2,
                    )
                if performative == ACL["reject-proposal"]:
                    return build_message(Graph(), ACL.inform, sender=economy_transport.uri, receiver=logistics_agent.uri, msgcnt=4)
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
            request_graph, _ = build_productes_localitzats(self._localized_request(order))

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
            self.assertEqual(final_lot["transport_id"], "fast")
            self.assertEqual(final_lot["price"], 6.6)
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
            request_graph, _ = build_productes_localitzats(self._localized_request(order))

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
            self.assertNotIn((economy_transport.address, ACL.propose), sent_performatives)
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
            request_graph, _ = build_productes_localitzats(self._localized_request(order))
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
            self.assertIn(f"Contraoferta oferta alta per al lot {lot_id}", joined_logs)
            self.assertIn("6.60 EUR", joined_logs)
            self.assertIn(f"Resposta a la contraoferta del lot {lot_id} per fast: acceptada", joined_logs)
            self.assertNotIn(f"Resposta a la contraoferta del lot {lot_id} per economy", joined_logs)
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
            request_graph, _ = build_productes_localitzats(self._localized_request(order))
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
