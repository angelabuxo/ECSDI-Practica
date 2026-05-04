import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

from rdflib import RDF


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.agent_centre_logistic import AgentCentreLogistic, LOG, create_app
from AgentZon.agents.agent_directory import AgentDirectory
from AgentZon.agents.agent_transportista import AgentTransportista, create_app as create_transportista_app
from AgentZon.config import AGENTZON
from AgentZon.protocols.centre_logistic import (
    build_producte_localitzat_action,
    read_lot_assignat_response,
)
from AgentZon.protocols.fipa_acl import build_message, get_message_properties, parse_message


class AgentCentreLogisticTest(unittest.TestCase):
    def _producte(self, **overrides):
        payload = {
            "id_producte": "p001",
            "id_comanda": "c001",
            "userid": "u001",
            "adreca": "Carrer Test 1, Barcelona",
            "ciutat": "Barcelona",
            "prioritat": 1,
            "data_limit": "2026-05-03",
            "pes": 2.0,
            "import_producte": 99.95,
        }
        payload.update(overrides)
        return payload

    def test_loads_ontology_with_logistic_center_class(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")

        self.assertIn((AGENTZON.CentreLogistic, RDF.type, None), agent.graph)

    def test_declares_prometheus_capabilities_and_plans(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")

        self.assertEqual(
            {
                "Gestionar magatzem": ["pla_assignar_producte_a_lot"],
                "Negociar transport": ["pla_cerca_transportista", "pla_transportista_escollit"],
                "Gestionar post-enviament": ["pla_producte_sha_enviat"],
            },
            {capacitat: [pla.__name__ for pla in plans] for capacitat, plans in agent.capacitats.items()},
        )

    def test_assigns_products_to_compatible_lot_by_shipping_day(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot_1 = agent.pla_assignar_producte_a_lot(self._producte(id_producte="p001", pes=2.5))
        lot_2 = agent.pla_assignar_producte_a_lot(
            self._producte(
                id_producte="p002",
                id_comanda="c002",
                userid="u002",
                adreca="Carrer Diferent 8, Girona",
                pes=1.0,
            )
        )

        lot_node = AGENTZON[f"lot_{lot_1['id']}"]
        self.assertEqual(lot_1["id"], lot_2["id"])
        self.assertEqual(lot_1["id"], "bcn-0001")
        self.assertIn((lot_node, RDF.type, AGENTZON.Lot), agent.graph)
        self.assertIn((lot_node, AGENTZON.TeProducte, AGENTZON["p001"]), agent.graph)
        self.assertIn((lot_node, AGENTZON.TeProducte, AGENTZON["p002"]), agent.graph)
        self.assertEqual(sorted(producte["id_producte"] for producte in lot_2["productes"]), ["p001", "p002"])
        self.assertEqual(lot_2["pes_total"], 3.5)
        self.assertEqual(lot_2["data_enviament"], "2026-05-03")

    def test_creates_sequential_lot_ids_with_centre_suffix_prefix(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot_1 = agent.pla_assignar_producte_a_lot(self._producte(id_producte="p001", data_limit="2026-05-03"))
        lot_2 = agent.pla_assignar_producte_a_lot(
            self._producte(
                id_producte="p002",
                id_comanda="c002",
                userid="u002",
                ciutat="Girona",
                data_limit="2026-05-04",
                pes=1.0,
                import_producte=49.95,
            )
        )

        self.assertEqual(lot_1["id"], "bcn-0001")
        self.assertEqual(lot_2["id"], "bcn-0002")

    def test_emits_debug_logs_for_lot_assignment_and_transport_selection(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")

        with self.assertLogs("AgentZon.agents.agent_centre_logistic", level="DEBUG") as logs:
            lot = agent.pla_assignar_producte_a_lot(self._producte())
            agent.pla_cerca_transportista(lot["id"])
            agent.registrar_oferta_transport(
                {
                    "id_lot": lot["id"],
                    "transportista_id": "transport-1",
                    "cost": 9.0,
                    "data_enviament": "2026-05-03",
                }
            )
            agent.pla_transportista_escollit(lot["id"])

        log_text = "\n".join(logs.output)
        self.assertIn("assignant producte", log_text)
        self.assertIn(lot["id"], log_text)
        self.assertIn("peticio transport", log_text)
        self.assertIn("oferta transport rebuda", log_text)
        self.assertIn("transportista escollit", log_text)

    def test_comm_assigns_producte_localitzat_to_lot(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        app = create_app(agent)
        message = build_message(
            "request",
            AGENTZON.agent_compra,
            AGENTZON.agent_centre_logistic_bcn,
            build_producte_localitzat_action(self._producte(pes=2.5)),
            msgcnt=1,
        )

        response = app.test_client().get("/comm", query_string={"content": message.serialize(format="xml")})
        response_graph = parse_message(response.data.decode("utf-8"))
        props = get_message_properties(response_graph)
        lot_response = read_lot_assignat_response(response_graph, props["content"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(props["performative"], "confirm")
        self.assertEqual(lot_response["id_producte"], "p001")
        lot_node = AGENTZON[f"lot_{lot_response['id_lot']}"]
        self.assertIn((lot_node, RDF.type, AGENTZON.Lot), agent.graph)
        self.assertIn((lot_node, AGENTZON.TeProducte, AGENTZON["p001"]), agent.graph)

    def test_prepares_transport_request_for_pending_lot(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot = agent.pla_assignar_producte_a_lot(self._producte(data_limit="2026-05-04"))

        peticio = agent.pla_cerca_transportista(lot["id"])
        lot_node = AGENTZON[f"lot_{lot['id']}"]

        self.assertEqual(peticio["ciutat_desti"], "Barcelona")
        self.assertEqual(peticio["pes"], 2.0)
        self.assertEqual(peticio["data_enviament"], "2026-05-04")
        self.assertEqual(str(agent.graph.value(lot_node, LOG.estat)), "NEGOCIANT_TRANSPORT")

    def test_selects_cheapest_transport_offer_before_lot_deadline(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot = agent.pla_assignar_producte_a_lot(self._producte())
        agent.pla_cerca_transportista(lot["id"])
        agent.registrar_oferta_transport(
            {
                "id_lot": lot["id"],
                "transportista_id": "transport-1",
                "cost": 9.0,
                "data_enviament": "2026-05-03",
            }
        )
        agent.registrar_oferta_transport(
            {
                "id_lot": lot["id"],
                "transportista_id": "transport-2",
                "cost": 6.5,
                "data_enviament": "2026-05-04",
            }
        )

        eleccio, missatges = agent.pla_transportista_escollit(lot["id"])
        lot_node = AGENTZON[f"lot_{lot['id']}"]

        self.assertEqual(len(missatges), 1)
        self.assertEqual(eleccio["id_lot"], lot["id"])
        self.assertEqual(eleccio["transportista_id"], "transport-1")
        self.assertEqual(eleccio["cost"], 9.0)
        self.assertEqual(str(agent.graph.value(lot_node, LOG.estat)), "TRANSPORTISTA_ESCOLLIT")

    def test_transport_selection_creates_delivery_messages_for_compra(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot = agent.pla_assignar_producte_a_lot(self._producte(id_producte="p001", id_comanda="c001"))
        agent.pla_assignar_producte_a_lot(
            self._producte(
                id_producte="p002",
                id_comanda="c002",
                userid="u002",
                pes=1.0,
                import_producte=49.95,
            )
        )
        agent.pla_cerca_transportista(lot["id"])
        agent.registrar_oferta_transport(
            {
                "id_lot": lot["id"],
                "transportista_id": "transport-1",
                "cost": 9.0,
                "data_enviament": "2026-05-03",
            }
        )

        eleccio, missatges = agent.pla_transportista_escollit(lot["id"])

        self.assertEqual(eleccio["transportista_id"], "transport-1")
        self.assertEqual(len(missatges), 2)
        self.assertEqual(sorted(missatge["id_producte"] for missatge in missatges), ["p001", "p002"])
        self.assertEqual({missatge["transportista_id"] for missatge in missatges}, {"transport-1"})
        self.assertEqual({missatge["data_entrega_definitiva"] for missatge in missatges}, {"2026-05-03"})

    def test_discovers_transport_agents_and_selects_best_offer(self):
        directory = AgentDirectory()
        directory.register_agent(
            name="transport-a",
            uri=AGENTZON.agent_transportista_a,
            address="memory://transport-a/comm",
            agent_type="AgentTransportista",
        )
        directory.register_agent(
            name="transport-b",
            uri=AGENTZON.agent_transportista_b,
            address="memory://transport-b/comm",
            agent_type="AgentTransportista",
        )
        transport_a = create_transportista_app(
            AgentTransportista("transport-a", cost_base=8.0, dies_extra=0, address="memory://transport-a/comm")
        )
        transport_b = create_transportista_app(
            AgentTransportista("transport-b", cost_base=5.0, dies_extra=0, address="memory://transport-b/comm")
        )
        transport_apps = {
            "memory://transport-a/comm": transport_a,
            "memory://transport-b/comm": transport_b,
        }

        def send_in_memory(address, graph):
            if address == "memory://directory/Register":
                return directory.process_message(graph)
            response = transport_apps[address].test_client().get(
                "/comm",
                query_string={"content": graph.serialize(format="xml")},
            )
            return parse_message(response.data.decode("utf-8"))

        agent = AgentCentreLogistic(
            centre_logistic_id="magatzem-bcn",
            ubicacio="Barcelona",
            directory_address="memory://directory/Register",
            message_sender=send_in_memory,
        )
        lot = agent.pla_assignar_producte_a_lot(self._producte())

        eleccio, missatges = agent.negociar_transport_amb_transportistes(lot["id"])

        self.assertEqual(eleccio["transportista_id"], "transport-b")
        self.assertEqual(eleccio["cost"], 7.0)
        self.assertEqual(len(agent._read_ofertes(lot["id"])), 2)
        self.assertEqual(missatges[0]["transportista_id"], "transport-b")

    def test_rejects_transport_selection_when_no_offer_meets_deadline(self):
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot = agent.pla_assignar_producte_a_lot(self._producte())
        agent.pla_cerca_transportista(lot["id"])
        agent.registrar_oferta_transport(
            {
                "id_lot": lot["id"],
                "transportista_id": "transport-1",
                "cost": 6.5,
                "data_enviament": "2026-05-04",
            }
        )

        with self.assertRaisesRegex(ValueError, "dins del termini"):
            agent.pla_transportista_escollit(lot["id"])

    def test_shipping_today_creates_charging_requests_for_sent_products(self):
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        agent = AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona")
        lot_avui = agent.pla_assignar_producte_a_lot(self._producte(data_limit=today))
        agent.pla_assignar_producte_a_lot(
            self._producte(
                id_producte="p002",
                id_comanda="c002",
                userid="u002",
                data_limit=tomorrow,
                pes=1.0,
                import_producte=49.95,
            )
        )

        peticions = agent.pla_producte_sha_enviat(today=today)
        lot_node = AGENTZON[f"lot_{lot_avui['id']}"]

        self.assertEqual(len(peticions), 1)
        self.assertEqual(peticions[0]["userid"], "u001")
        self.assertEqual(peticions[0]["id_comanda"], "c001")
        self.assertEqual(peticions[0]["id_producte"], "p001")
        self.assertEqual(peticions[0]["import_cobrament"], 99.95)
        self.assertEqual(str(agent.graph.value(lot_node, LOG.estat)), "ENVIAT")

    def test_info_endpoint_returns_turtle_runtime_graph(self):
        app = create_app(AgentCentreLogistic(centre_logistic_id="magatzem-bcn", ubicacio="Barcelona"))

        response = app.test_client().get("/Info")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"@prefix az:", response.data)


if __name__ == "__main__":
    unittest.main()
